"""
Apple Music Integration Routes

Premium Apple Music MusicKit integration for VitaFlow.
Supports: MusicKit JS token generation, library access, and playback control.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import jwt
import os

from ..dependencies import get_current_user
from ..models.user import User

router = APIRouter(prefix="/apple-music", tags=["Apple Music Integration"])

# ============================================================================
# Configuration
# ============================================================================

# Apple Music API credentials (set via environment variables)
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID", "")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY", "")  # PEM format

APPLE_MUSIC_API_BASE = "https://api.music.apple.com/v1"

# ============================================================================
# Pydantic Schemas
# ============================================================================

class MusicKitToken(BaseModel):
    """MusicKit developer token for frontend initialization."""
    token: str
    expires_at: datetime

class AppleMusicTrack(BaseModel):
    """Simplified Apple Music track info."""
    id: str
    name: str
    artist: str
    album: str
    artwork_url: Optional[str]
    duration_ms: int
    preview_url: Optional[str]

class AppleMusicPlaylist(BaseModel):
    """Simplified Apple Music playlist info."""
    id: str
    name: str
    description: Optional[str]
    artwork_url: Optional[str]
    track_count: int
    is_public: bool

class AppleMusicSearchResult(BaseModel):
    """Apple Music catalog search result."""
    songs: List[AppleMusicTrack]
    playlists: List[AppleMusicPlaylist]

# ============================================================================
# Token Generation
# ============================================================================

def generate_musickit_token() -> tuple[str, datetime]:
    """
    Generate a MusicKit developer token (JWT).
    
    This token is signed with your Apple Music private key and authorizes
    the frontend to use the MusicKit JS library.
    
    Token is valid for 6 months (Apple's maximum).
    """
    if not all([APPLE_TEAM_ID, APPLE_KEY_ID, APPLE_PRIVATE_KEY]):
        raise HTTPException(
            status_code=503,
            detail="Apple Music integration not configured. Please set APPLE_TEAM_ID, APPLE_KEY_ID, and APPLE_PRIVATE_KEY."
        )
    
    # Token expires in 6 months (maximum allowed by Apple)
    expires_at = datetime.now(timezone.utc) + timedelta(days=180)
    
    headers = {
        "alg": "ES256",
        "kid": APPLE_KEY_ID,
    }
    
    payload = {
        "iss": APPLE_TEAM_ID,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    
    token = jwt.encode(
        payload,
        APPLE_PRIVATE_KEY,
        algorithm="ES256",
        headers=headers,
    )
    
    return token, expires_at

# ============================================================================
# Routes
# ============================================================================

@router.get("/auth/token", response_model=MusicKitToken)
async def get_musickit_token(
    current_user: User = Depends(get_current_user),
):
    """
    Get a MusicKit developer token for frontend initialization.
    
    The frontend uses this token to configure MusicKit JS before
    requesting user authorization.
    """
    token, expires_at = generate_musickit_token()
    
    return MusicKitToken(
        token=token,
        expires_at=expires_at,
    )


@router.get("/catalog/search", response_model=AppleMusicSearchResult)
async def search_catalog(
    query: str = Query(..., min_length=1),
    types: str = Query("songs,playlists"),
    storefront: str = Query("us"),  # ISO country code
    limit: int = Query(25, ge=1, le=25),
    current_user: User = Depends(get_current_user),
):
    """
    Search the Apple Music catalog.
    
    Note: This endpoint requires a valid developer token but NOT user authorization.
    For user library access, use the MusicKit JS library on the frontend.
    """
    import httpx
    
    token, _ = generate_musickit_token()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{APPLE_MUSIC_API_BASE}/catalog/{storefront}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "term": query,
                "types": types,
                "limit": limit,
            },
        )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to search Apple Music catalog",
        )
    
    data = response.json()
    results = data.get("results", {})
    
    songs = []
    for song in results.get("songs", {}).get("data", []):
        attrs = song.get("attributes", {})
        artwork = attrs.get("artwork", {})
        artwork_url = None
        if artwork.get("url"):
            # Replace {w}x{h} with actual dimensions
            artwork_url = artwork["url"].replace("{w}", "300").replace("{h}", "300")
        
        songs.append(AppleMusicTrack(
            id=song["id"],
            name=attrs.get("name", ""),
            artist=attrs.get("artistName", ""),
            album=attrs.get("albumName", ""),
            artwork_url=artwork_url,
            duration_ms=attrs.get("durationInMillis", 0),
            preview_url=attrs.get("previews", [{}])[0].get("url"),
        ))
    
    playlists = []
    for playlist in results.get("playlists", {}).get("data", []):
        attrs = playlist.get("attributes", {})
        artwork = attrs.get("artwork", {})
        artwork_url = None
        if artwork.get("url"):
            artwork_url = artwork["url"].replace("{w}", "300").replace("{h}", "300")
        
        playlists.append(AppleMusicPlaylist(
            id=playlist["id"],
            name=attrs.get("name", ""),
            description=attrs.get("description", {}).get("standard"),
            artwork_url=artwork_url,
            track_count=0,  # Not available in search results
            is_public=True,
        ))
    
    return AppleMusicSearchResult(songs=songs, playlists=playlists)


@router.get("/catalog/playlists/{playlist_id}")
async def get_catalog_playlist(
    playlist_id: str,
    storefront: str = Query("us"),
    current_user: User = Depends(get_current_user),
):
    """
    Get details of a specific catalog playlist.
    """
    import httpx
    
    token, _ = generate_musickit_token()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{APPLE_MUSIC_API_BASE}/catalog/{storefront}/playlists/{playlist_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"include": "tracks"},
        )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to fetch playlist",
        )
    
    data = response.json()
    playlist_data = data.get("data", [{}])[0]
    attrs = playlist_data.get("attributes", {})
    
    # Extract tracks
    tracks = []
    for track in playlist_data.get("relationships", {}).get("tracks", {}).get("data", []):
        track_attrs = track.get("attributes", {})
        artwork = track_attrs.get("artwork", {})
        artwork_url = None
        if artwork.get("url"):
            artwork_url = artwork["url"].replace("{w}", "300").replace("{h}", "300")
        
        tracks.append({
            "id": track["id"],
            "name": track_attrs.get("name", ""),
            "artist": track_attrs.get("artistName", ""),
            "album": track_attrs.get("albumName", ""),
            "artwork_url": artwork_url,
            "duration_ms": track_attrs.get("durationInMillis", 0),
        })
    
    artwork = attrs.get("artwork", {})
    playlist_artwork = None
    if artwork.get("url"):
        playlist_artwork = artwork["url"].replace("{w}", "600").replace("{h}", "600")
    
    return {
        "id": playlist_data["id"],
        "name": attrs.get("name", ""),
        "description": attrs.get("description", {}).get("standard"),
        "artwork_url": playlist_artwork,
        "track_count": len(tracks),
        "tracks": tracks,
        "curator_name": attrs.get("curatorName"),
    }


@router.get("/catalog/workout-playlists")
async def get_workout_playlists(
    storefront: str = Query("us"),
    current_user: User = Depends(get_current_user),
):
    """
    Get curated workout playlists from Apple Music's fitness category.
    """
    # Search for fitness/workout playlists
    result = await search_catalog(
        query="workout fitness",
        types="playlists",
        storefront=storefront,
        limit=25,
        current_user=current_user,
    )
    
    return {
        "playlists": result.playlists,
        "note": "Use MusicKit JS on the frontend to play these playlists",
    }
