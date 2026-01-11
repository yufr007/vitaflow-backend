# app/services/azure_speech.py
"""
VitaFlow - Azure Speech Service Integration.

Provides real-time voice coaching during workouts (Elite tier only).
Features:
- Text-to-speech for coaching cues
- Speech-to-text for voice commands
- Personalized voice feedback
"""

import os
import logging
from typing import Optional, Dict, Any, BinaryIO
from io import BytesIO

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    AZURE_SPEECH_AVAILABLE = False
    speechsdk = None

logger = logging.getLogger(__name__)


class AzureSpeechService:
    """
    Azure Speech Service for voice coaching.
    
    Usage:
        service = AzureSpeechService()
        await service.initialize()
        audio_data = await service.synthesize_coaching_cue("Lock your core, maintain neutral spine")
    """
    
    _instance: Optional['AzureSpeechService'] = None
    _initialized: bool = False
    
    def __init__(self):
        """Initialize Azure Speech configuration."""
        self.speech_config: Optional[speechsdk.SpeechConfig] = None
        self.speech_key: Optional[str] = None
        self.speech_region: Optional[str] = None
        
    @classmethod
    def get_instance(cls) -> 'AzureSpeechService':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self) -> bool:
        """
        Initialize Azure Speech Service connection.
        
        Returns:
            bool: True if initialization successful.
        """
        if self._initialized:
            return True
        
        if not AZURE_SPEECH_AVAILABLE:
            logger.warning("Azure Speech SDK not installed - pip install azure-cognitiveservices-speech")
            return False
        
        try:
            self.speech_key = os.getenv("AZURE_SPEECH_KEY")
            self.speech_region = os.getenv("AZURE_SPEECH_REGION", "australiaeast")
            
            if not self.speech_key:
                logger.warning("Azure Speech not configured - using fallback mode")
                return False
            
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region
            )
            
            # Configure voice settings (neural voice for natural sound)
            self.speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
            
            logger.info(f"Azure Speech initialized: {self.speech_region}")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Speech: {e}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if Azure Speech is available."""
        return self._initialized and self.speech_config is not None
    
    # =========================================================================
    # Text-to-Speech for Coaching Cues
    # =========================================================================
    
    async def synthesize_coaching_cue(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0
    ) -> Optional[bytes]:
        """
        Convert coaching text to speech audio.
        
        Args:
            text: Coaching cue text (e.g., "Lock your core")
            voice_name: Optional voice (default: en-US-JennyNeural)
            speaking_rate: Speed multiplier (0.5 = slow, 2.0 = fast)
            pitch: Pitch adjustment in Hz
        
        Returns:
            Audio bytes (WAV format) or None if failed
        """
        if not self.is_available:
            logger.warning("Azure Speech not available - cannot synthesize audio")
            return None
        
        try:
            # Configure voice if specified
            if voice_name:
                self.speech_config.speech_synthesis_voice_name = voice_name
            
            # Create synthesizer with in-memory output
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Build SSML for advanced control
            ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
                <voice name="{self.speech_config.speech_synthesis_voice_name}">
                    <prosody rate="{speaking_rate}" pitch="{pitch:+.1f}Hz">
                        {text}
                    </prosody>
                </voice>
            </speak>
            """
            
            # Synthesize
            result = synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"Synthesized coaching cue: {text[:50]}...")
                return result.audio_data
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(f"Speech synthesis canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation.error_details}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            return None
    
    async def synthesize_personalized_cue(
        self,
        user_name: str,
        exercise: str,
        feedback: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """
        Generate personalized coaching cue with user's name and context.
        
        Args:
            user_name: User's first name
            exercise: Current exercise (e.g., "squat")
            feedback: Specific feedback (e.g., "lock your core")
            user_context: AgentEvolver context for personalization
        
        Returns:
            Audio bytes or None
        """
        # Build personalized message
        if user_context and user_context.get("past_cues"):
            # Reference past coaching
            text = f"{user_name}, {feedback}. Remember last time you nailed this."
        else:
            text = f"{user_name}, {feedback}"
        
        # Adjust speaking rate based on exercise intensity
        high_intensity_exercises = ["sprint", "burpee", "jump", "hiit"]
        speaking_rate = 1.2 if any(ex in exercise.lower() for ex in high_intensity_exercises) else 1.0
        
        return await self.synthesize_coaching_cue(text, speaking_rate=speaking_rate)
    
    # =========================================================================
    # Speech-to-Text for Voice Commands
    # =========================================================================
    
    async def recognize_voice_command(
        self,
        audio_data: bytes,
        language: str = "en-US"
    ) -> Optional[Dict[str, Any]]:
        """
        Convert voice audio to text (for hands-free commands).
        
        Args:
            audio_data: Audio bytes (WAV format)
            language: Language code (en-US, en-AU, etc.)
        
        Returns:
            {
                "text": "next exercise",
                "confidence": 0.95,
                "recognized": true
            }
        """
        if not self.is_available:
            logger.warning("Azure Speech not available - cannot recognize audio")
            return None
        
        try:
            # Configure recognition language
            self.speech_config.speech_recognition_language = language
            
            # Create recognizer from audio data
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_stream.write(audio_data)
            audio_stream.close()
            
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Recognize
            result = recognizer.recognize_once_async().get()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return {
                    "text": result.text,
                    "confidence": 0.95,  # Azure doesn't expose confidence directly
                    "recognized": True
                }
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No speech recognized")
                return {"text": "", "confidence": 0.0, "recognized": False}
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(f"Speech recognition canceled: {cancellation.reason}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to recognize speech: {e}")
            return None
    
    # =========================================================================
    # Voice Profiles (Future: Multi-voice support)
    # =========================================================================
    
    def get_available_voices(self) -> Dict[str, str]:
        """
        Get available neural voices for different coaching styles.
        
        Returns:
            {
                "motivator": "en-US-GuyNeural",
                "therapist": "en-US-JennyNeural",
                "drill_sergeant": "en-US-DavisNeural"
            }
        """
        return {
            "motivator": "en-US-GuyNeural",  # Energetic male
            "therapist": "en-US-JennyNeural",  # Calm female
            "drill_sergeant": "en-US-DavisNeural",  # Authoritative male
            "scientist": "en-US-AriaNeural",  # Professional female
            "specialist": "en-US-BrandonNeural",  # Confident male
        }


# Singleton instance
azure_speech = AzureSpeechService.get_instance()
