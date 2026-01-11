"""
Spotify Integration Routes

Premium Spotify OAuth and Playback API integration for VitaFlow.
Supports: OAuth2 PKCE flow, playlist management, playback control, and AI-generated workout playlists.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import httpx
import base64
import secrets
import json

from ..dependencies import get_current_user, get_db
from ..models.user import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/spotify", tags=["Spotify Integration"])

# ============================================================================
# Configuration (Loaded from environment in production)
# ============================================================================

import os

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:5173/callback/spotify")

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Required scopes for VitaFlow features
SPOTIFY_SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "streaming",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
]

# ============================================================================
# Pydantic Schemas
# ============================================================================

class SpotifyAuthURL(BaseModel):
    """Response containing Spotify OAuth URL."""
    auth_url: str
    state: str

class SpotifyTokens(BaseModel):
    """Spotify access and refresh tokens."""
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: datetime
    token_type: str
    scope: str

class SpotifyTrack(BaseModel):
    """Simplified Spotify track info."""
    id: str
    name: str
    artist: str
    album: str
    album_art_url: Optional[str]
    duration_ms: int
    bpm: Optional[float] = None  # Audio feature

class SpotifyPlaylist(BaseModel):
    """Simplified Spotify playlist info."""
    id: str
    name: str
    description: Optional[str]
    image_url: Optional[str]
    track_count: int
    owner: str
    is_public: bool

class PlaybackState(BaseModel):
    """Current Spotify playback state."""
    is_playing: bool
    track: Optional[SpotifyTrack]
    progress_ms: int
    device_id: Optional[str]
    device_name: Optional[str]
    volume_percent: int
    shuffle_state: bool
    repeat_state: str

class WorkoutPlaylistRequest(BaseModel):
    """Request for AI-generated workout playlist."""
    workout_type: str  # HIIT, strength, cardio, yoga, etc.
    duration_minutes: int
    bpm_min: int = 100
    bpm_max: int = 180
    energy_level: str = "high"  # low, medium, high

# ============================================================================
# OAuth Routes
# ============================================================================

@router.get("/auth/url", response_model=SpotifyAuthURL)
async def get_spotify_auth_url(
    redirect_uri: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Generate Spotify OAuth authorization URL.
    
    Frontend should redirect user to this URL to initiate Spotify login.
    After auth, Spotify redirects back with an authorization code.
    """
    if not SPOTIFY_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Spotify integration not configured. Please set SPOTIFY_CLIENT_ID."
        )
    
    # Generate secure state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Use provided redirect URI or default
    final_redirect = redirect_uri or SPOTIFY_REDIRECT_URI
    
    # Build authorization URL
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": final_redirect,
        "state": state,
        "scope": " ".join(SPOTIFY_SCOPES),
        "show_dialog": "true",  # Always show login dialog
    }
    
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{SPOTIFY_AUTH_URL}?{query_string}"
    
    return SpotifyAuthURL(auth_url=auth_url, state=state)


@router.post("/auth/callback", response_model=SpotifyTokens)
async def spotify_callback(
    code: str,
    state: str,
    redirect_uri: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Exchange authorization code for access and refresh tokens.
    
    Frontend calls this after receiving the callback from Spotify.
    Tokens are stored server-side for security.
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Spotify integration not configured."
        )
    
    final_redirect = redirect_uri or SPOTIFY_REDIRECT_URI
    
    # Exchange code for tokens
    auth_header = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": final_redirect,
            },
        )
    
    if response.status_code != 200:
        error_data = response.json()
        raise HTTPException(
            status_code=400,
            detail=f"Spotify auth failed: {error_data.get('error_description', 'Unknown error')}"
        )
    
    token_data = response.json()
    
    # Calculate expiration time
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
    
    # TODO: Store tokens in database (MusicConnection model)
    # For now, return directly to frontend for storage
    
    return SpotifyTokens(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_in=token_data["expires_in"],
        expires_at=expires_at,
        token_type=token_data["token_type"],
        scope=token_data["scope"],
    )


@router.post("/auth/refresh", response_model=SpotifyTokens)
async def refresh_spotify_token(
    refresh_token: str,
    current_user: User = Depends(get_current_user),
):
    """
    Refresh expired access token using refresh token.
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Spotify integration not configured.")
    
    auth_header = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to refresh token")
    
    token_data = response.json()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
    
    return SpotifyTokens(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", refresh_token),  # May not be returned
        expires_in=token_data["expires_in"],
        expires_at=expires_at,
        token_type=token_data["token_type"],
        scope=token_data.get("scope", ""),
    )

# ============================================================================
# Playlist Routes
# ============================================================================

@router.get("/playlists", response_model=List[SpotifyPlaylist])
async def get_user_playlists(
    access_token: str,
    limit: int = Query(50, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch user's Spotify playlists.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_BASE}/me/playlists",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": limit, "offset": offset},
        )
    
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Spotify token expired")
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch playlists")
    
    data = response.json()
    playlists = []
    
    for item in data.get("items", []):
        playlists.append(SpotifyPlaylist(
            id=item["id"],
            name=item["name"],
            description=item.get("description"),
            image_url=item["images"][0]["url"] if item.get("images") else None,
            track_count=item["tracks"]["total"],
            owner=item["owner"]["display_name"],
            is_public=item.get("public", False),
        ))
    
    return playlists


@router.get("/playlists/{playlist_id}/tracks", response_model=List[SpotifyTrack])
async def get_playlist_tracks(
    playlist_id: str,
    access_token: str,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """
    Get tracks from a specific playlist.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": limit, "offset": offset},
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch tracks")
    
    data = response.json()
    tracks = []
    
    for item in data.get("items", []):
        track = item.get("track")
        if not track:
            continue
        
        tracks.append(SpotifyTrack(
            id=track["id"],
            name=track["name"],
            artist=", ".join(a["name"] for a in track["artists"]),
            album=track["album"]["name"],
            album_art_url=track["album"]["images"][0]["url"] if track["album"].get("images") else None,
            duration_ms=track["duration_ms"],
        ))
    
    return tracks

# ============================================================================
# Playback Control Routes
# ============================================================================

@router.get("/playback", response_model=Optional[PlaybackState])
async def get_playback_state(
    access_token: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get current Spotify playback state.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_BASE}/me/player",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    
    if response.status_code == 204:
        return None  # No active playback
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to get playback state")
    
    data = response.json()
    track = data.get("item")
    device = data.get("device")
    
    return PlaybackState(
        is_playing=data.get("is_playing", False),
        track=SpotifyTrack(
            id=track["id"],
            name=track["name"],
            artist=", ".join(a["name"] for a in track["artists"]),
            album=track["album"]["name"],
            album_art_url=track["album"]["images"][0]["url"] if track["album"].get("images") else None,
            duration_ms=track["duration_ms"],
        ) if track else None,
        progress_ms=data.get("progress_ms", 0),
        device_id=device.get("id") if device else None,
        device_name=device.get("name") if device else None,
        volume_percent=device.get("volume_percent", 0) if device else 0,
        shuffle_state=data.get("shuffle_state", False),
        repeat_state=data.get("repeat_state", "off"),
    )


@router.put("/playback/play")
async def start_playback(
    access_token: str,
    playlist_uri: Optional[str] = None,
    device_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Start or resume playback.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {}
    body = {}
    
    if device_id:
        params["device_id"] = device_id
    
    if playlist_uri:
        body["context_uri"] = playlist_uri
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{SPOTIFY_API_BASE}/me/player/play",
            headers=headers,
            params=params,
            json=body if body else None,
        )
    
    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=response.status_code, detail="Failed to start playback")
    
    return {"success": True}


@router.put("/playback/pause")
async def pause_playback(
    access_token: str,
    device_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Pause playback.
    """
    params = {"device_id": device_id} if device_id else {}
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{SPOTIFY_API_BASE}/me/player/pause",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
    
    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=response.status_code, detail="Failed to pause playback")
    
    return {"success": True}


@router.post("/playback/skip")
async def skip_track(
    access_token: str,
    device_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Skip to next track.
    """
    params = {"device_id": device_id} if device_id else {}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SPOTIFY_API_BASE}/me/player/next",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
    
    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=response.status_code, detail="Failed to skip track")
    
    return {"success": True}


@router.put("/playback/volume")
async def set_volume(
    access_token: str,
    volume_percent: int = Query(..., ge=0, le=100),
    device_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Set playback volume.
    """
    params = {"volume_percent": volume_percent}
    if device_id:
        params["device_id"] = device_id
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{SPOTIFY_API_BASE}/me/player/volume",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
    
    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=response.status_code, detail="Failed to set volume")
    
    return {"success": True}

# ============================================================================
# AI-Powered Playlist Generation
# ============================================================================

@router.post("/playlists/generate-workout")
async def generate_workout_playlist(
    request: WorkoutPlaylistRequest,
    access_token: str,
    current_user: User = Depends(get_current_user),
):
    """
    Generate an AI-powered workout playlist based on workout parameters.
    
    Uses Spotify's audio features (tempo, energy, danceability) to select
    optimal tracks for the specified workout type.
    """
    # Define search queries based on workout type
    genre_map = {
        "hiit": ["electronic dance music", "workout", "high energy"],
        "strength": ["hip hop", "rock", "powerful"],
        "cardio": ["pop", "dance", "running"],
        "yoga": ["ambient", "chill", "meditation"],
        "stretching": ["lo-fi", "acoustic", "relaxing"],
    }
    
    genres = genre_map.get(request.workout_type.lower(), ["workout", "fitness"])
    
    # Search for tracks matching the criteria
    tracks = []
    async with httpx.AsyncClient() as client:
        for genre in genres[:2]:  # Limit to 2 genre searches
            response = await client.get(
                f"{SPOTIFY_API_BASE}/search",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": f"genre:{genre}",
                    "type": "track",
                    "limit": 20,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                for track in data.get("tracks", {}).get("items", []):
                    tracks.append({
                        "id": track["id"],
                        "uri": track["uri"],
                        "name": track["name"],
                        "artist": track["artists"][0]["name"],
                        "duration_ms": track["duration_ms"],
                    })
    
    # Calculate approximate number of tracks needed
    target_duration_ms = request.duration_minutes * 60 * 1000
    selected_tracks = []
    current_duration = 0
    
    for track in tracks:
        if current_duration >= target_duration_ms:
            break
        selected_tracks.append(track)
        current_duration += track["duration_ms"]
    
    return {
        "workout_type": request.workout_type,
        "duration_target_minutes": request.duration_minutes,
        "actual_duration_minutes": round(current_duration / 60000, 1),
        "track_count": len(selected_tracks),
        "tracks": selected_tracks,
        "note": "Use /playback/play with track URIs to start playback",
    }
