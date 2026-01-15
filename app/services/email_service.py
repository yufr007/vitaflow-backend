"""
VitaFlow Email Service.

Handles OTP email delivery using Resend API with premium glassmorphic HTML templates.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

import resend
from settings import settings


class EmailService:
    """Email service for OTP verification and transactional emails."""

    def __init__(self):
        """Initialize Resend API with API key."""
        resend.api_key = settings.RESEND_API_KEY

    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit OTP code."""
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def get_otp_expiry() -> datetime:
        """Get OTP expiration datetime (10 minutes from now)."""
        return datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    @staticmethod
    def create_otp_email_html(name: str, otp_code: str) -> str:
        """
        Create premium glassmorphic HTML template for OTP email.

        Args:
            name: User's name
            otp_code: 6-digit OTP code

        Returns:
            HTML string with premium styling
        """
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VitaFlow - Verify Your Email</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0A0E1C;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0A0E1C; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px;">
                    <!-- Header with logo -->
                    <tr>
                        <td align="center" style="padding-bottom: 40px;">
                            <h1 style="color: #00FF88; font-size: 32px; font-weight: 700; margin: 0; text-shadow: 0 0 20px rgba(0, 255, 136, 0.4);">
                                VitaFlow
                            </h1>
                        </td>
                    </tr>

                    <!-- Main content card with glassmorphism effect -->
                    <tr>
                        <td style="background: rgba(13, 19, 33, 0.6); backdrop-filter: blur(24px); border: 1px solid rgba(0, 255, 136, 0.12); border-radius: 16px; padding: 40px;">
                            <!-- Greeting -->
                            <h2 style="color: #FFFFFF; font-size: 24px; font-weight: 600; margin: 0 0 16px 0;">
                                Welcome, {name}!
                            </h2>

                            <p style="color: #94A3B8; font-size: 16px; line-height: 1.6; margin: 0 0 32px 0;">
                                Your personalized fitness intelligence system is ready to activate. Please verify your email address to continue.
                            </p>

                            <!-- OTP Code Display -->
                            <div style="background: linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(0, 212, 255, 0.1) 100%); border: 2px solid rgba(0, 255, 136, 0.3); border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 32px;">
                                <p style="color: #94A3B8; font-size: 14px; font-weight: 500; margin: 0 0 12px 0; letter-spacing: 0.05em; text-transform: uppercase;">
                                    Your Verification Code
                                </p>
                                <p style="color: #00FF88; font-size: 48px; font-weight: 700; margin: 0; letter-spacing: 0.1em; text-shadow: 0 0 20px rgba(0, 255, 136, 0.4);">
                                    {otp_code}
                                </p>
                            </div>

                            <!-- Instructions -->
                            <div style="background: rgba(15, 23, 42, 0.4); border-left: 3px solid #00D4FF; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                                <p style="color: #CBD5E1; font-size: 14px; line-height: 1.6; margin: 0;">
                                    <strong style="color: #00D4FF;">Important:</strong> This code will expire in <strong>{settings.OTP_EXPIRY_MINUTES} minutes</strong>. Enter it in the VitaFlow app to activate your account.
                                </p>
                            </div>

                            <!-- Security notice -->
                            <p style="color: #64748B; font-size: 13px; line-height: 1.5; margin: 0;">
                                If you didn't request this code, please ignore this email. Your account security is important to us.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding-top: 32px;">
                            <p style="color: #475569; font-size: 12px; line-height: 1.5; margin: 0;">
                                © 2026 VitaFlow. Personalized Fitness Intelligence.
                            </p>
                            <p style="color: #475569; font-size: 12px; line-height: 1.5; margin: 8px 0 0 0;">
                                This email was sent to verify your VitaFlow account.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """

    async def send_otp_email(
        self,
        to_email: str,
        name: str,
        otp_code: str
    ) -> bool:
        """
        Send OTP verification email using Resend.

        Args:
            to_email: Recipient email address
            name: Recipient's name
            otp_code: 6-digit OTP code

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            html_content = self.create_otp_email_html(name, otp_code)

            params = {
                "from": "VitaFlow <noreply@vitaflow.fitness>",
                "to": [to_email],
                "subject": f"VitaFlow - Your Verification Code: {otp_code}",
                "html": html_content
            }

            # Send email via Resend API
            email = resend.Emails.send(params)

            return True
        except Exception as e:
            # Log error but don't expose details to user
            print(f"Failed to send OTP email: {str(e)}")
            return False


# Singleton instance
email_service = EmailService()
