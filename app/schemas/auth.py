"""
VitaFlow API - Authentication Schemas.

Pydantic schemas for authentication requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    """
    Schema for user registration request.
    
    Attributes:
        email: User's email address.
        password: User's password (min 8 characters).
        name: User's display name.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "name": "John Doe"
            }
        }
    )
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (minimum 8 characters)"
    )
    name: str = Field(..., min_length=1, description="User's display name")


class LoginRequest(BaseModel):
    """
    Schema for user login request.
    
    Attributes:
        email: User's email address.
        password: User's password.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    )
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class TokenResponse(BaseModel):
    """
    Schema for authentication token response.

    Attributes:
        access_token: JWT access token.
        token_type: Token type (always "bearer").
        user_id: Authenticated user's ID.
        refresh_token: Optional JWT refresh token for token rotation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="Authenticated user's ID")
    refresh_token: str | None = Field(None, description="JWT refresh token for token rotation")


class RefreshRequest(BaseModel):
    """
    Schema for token refresh request.
    
    Attributes:
        refresh_token: The refresh token to exchange.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )
    
    refresh_token: str = Field(..., description="Refresh token")


class RegisterResponse(BaseModel):
    """
    Schema for registration response (before OTP verification).
    
    Attributes:
        user_id: Created user's ID (needed for OTP verification).
        email: User's email (for display/confirmation).
        message: Success message.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "message": "Verification code sent to email"
            }
        }
    )
    
    user_id: str = Field(..., description="Created user's ID")
    email: str = Field(..., description="User's email address")
    message: str = Field(default="Verification code sent to email")


class VerifyOTPRequest(BaseModel):
    """
    Schema for OTP verification request.
    
    Attributes:
        user_id: User's ID from registration response.
        otp_code: 6-digit OTP code from email.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "otp_code": "123456"
            }
        }
    )
    
    user_id: str = Field(..., description="User's ID")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class ResendOTPRequest(BaseModel):
    """
    Schema for resend OTP request.
    
    Attributes:
        user_id: User's ID from registration response.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )
    
    user_id: str = Field(..., description="User's ID")


class ResendOTPResponse(BaseModel):
    """Schema for resend OTP response."""
    
    success: bool = Field(..., description="Whether OTP was resent")
    message: str = Field(..., description="Status message")


class GoogleOAuthRequest(BaseModel):
    """
    Schema for Google OAuth token exchange.
    
    Attributes:
        token: Google ID token from frontend.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )
    
    token: str = Field(..., description="Google ID token")
