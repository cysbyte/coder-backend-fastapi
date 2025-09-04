from typing import Optional, Tuple
from fastapi import Header, HTTPException, Response
from utils.supabase_client import supabase
import asyncio
import hashlib
from datetime import datetime, timedelta

# In-memory storage for refresh locks and cached tokens
_refresh_locks = {}
_cached_tokens = {}
_lock_cleanup_interval = 300  # 5 minutes

def _get_refresh_token_hash(refresh_token: str) -> str:
    """Create a hash of the refresh token for use as a lock key"""
    return hashlib.sha256(refresh_token.encode()).hexdigest()

async def _cleanup_expired_locks():
    """Clean up expired locks and cached tokens"""
    current_time = datetime.now()
    expired_keys = []
    
    for key, (lock, timestamp) in _refresh_locks.items():
        if current_time - timestamp > timedelta(seconds=_lock_cleanup_interval):
            expired_keys.append(key)
    
    for key in expired_keys:
        del _refresh_locks[key]
        if key in _cached_tokens:
            del _cached_tokens[key]

async def silent_refresh_token(refresh_token: str) -> Tuple[dict, dict]:
    """
    Attempt to refresh tokens silently without raising HTTP exceptions.
    Uses in-memory locking to prevent concurrent refresh attempts for the same token.
    Returns (user_dict, session_dict) or (None, None) if refresh fails.
    """
    token_hash = _get_refresh_token_hash(refresh_token)
    
    # Clean up expired locks periodically
    await _cleanup_expired_locks()
    
    # Check if we have a cached result for this token
    if token_hash in _cached_tokens:
        cached_result, cached_time = _cached_tokens[token_hash]
        # Cache is valid for 30 seconds
        if datetime.now() - cached_time < timedelta(seconds=30):
            print(f"[DEBUG] Using cached token refresh result for token: {refresh_token[:20]}...")
            return cached_result
    
    # Get or create lock for this refresh token
    if token_hash not in _refresh_locks:
        _refresh_locks[token_hash] = (asyncio.Lock(), datetime.now())
    
    lock, _ = _refresh_locks[token_hash]
    
    # Acquire lock to prevent concurrent refresh attempts
    async with lock:
        print(f"[DEBUG] silent_refresh_token: Starting token refresh with refresh_token: {refresh_token[:20]}...")
        
        try:
            print("[DEBUG] silent_refresh_token: Calling supabase.auth.refresh_session")
            refresh_response = supabase.auth.refresh_session(refresh_token)
            print(f"[DEBUG] silent_refresh_token: Refresh response received: {refresh_response is not None}")
            
            if not refresh_response or not getattr(refresh_response, "user", None):
                print("[DEBUG] silent_refresh_token: No refresh response or user data")
                return None, None
            
            print(f"[DEBUG] silent_refresh_token: User data present: {refresh_response.user.id if refresh_response.user else 'None'}")
            
            session = getattr(refresh_response, "session", None)
            if not session:
                print("[DEBUG] silent_refresh_token: No session data in refresh response")
                return None, None
            
            print("[DEBUG] silent_refresh_token: Session data present, extracting tokens")
            
            access_token = getattr(session, "access_token", None)
            new_refresh_token = getattr(session, "refresh_token", None)
            expires_at = getattr(session, "expires_at", None)
            
            print(f"[DEBUG] silent_refresh_token: Access token extracted: {access_token[:20] if access_token else 'None'}...")
            print(f"[DEBUG] silent_refresh_token: New refresh token extracted: {new_refresh_token[:20] if new_refresh_token else 'None'}...")
            print(f"[DEBUG] silent_refresh_token: Expires at: {expires_at}")
            
            session_data = {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "expires_at": expires_at
            }
            
            # Cache the successful result
            result = (refresh_response.user, session_data)
            _cached_tokens[token_hash] = (result, datetime.now())
            
            print("[DEBUG] silent_refresh_token: Token refresh successful")
            return result
            
        except Exception as e:
            print(f"[DEBUG] silent_refresh_token: Exception occurred: {str(e)}")
            print(f"[DEBUG] silent_refresh_token: Exception type: {type(e).__name__}")
            
            # If it's a refresh_token_already_used error, check if we have a cached result
            if "refresh_token_already_used" in str(e).lower() and token_hash in _cached_tokens:
                cached_result, cached_time = _cached_tokens[token_hash]
                # Use cached result if it's recent (within 30 seconds)
                if datetime.now() - cached_time < timedelta(seconds=30):
                    print(f"[DEBUG] Using cached result due to refresh_token_already_used for token: {refresh_token[:20]}...")
                    return cached_result
            
            return None, None

def get_token_expiration_info():
    """
    Get information about current token expiration settings for debugging
    """
    import os
    return {
        "jwt_expiry": os.getenv("JWT_EXPIRY", "Not set"),
        "environment": os.getenv("ENV", "development"),
        "note": "Token expiration is controlled by Supabase JWT settings in the dashboard"
    }

def get_refresh_lock_debug_info():
    """
    Get debug information about the refresh lock system
    """
    current_time = datetime.now()
    active_locks = {}
    
    for token_hash, (lock, timestamp) in _refresh_locks.items():
        age_seconds = (current_time - timestamp).total_seconds()
        active_locks[token_hash[:8]] = {
            "age_seconds": age_seconds,
            "will_expire_in": _lock_cleanup_interval - age_seconds
        }
    
    cached_tokens_info = {}
    for token_hash, (result, timestamp) in _cached_tokens.items():
        age_seconds = (current_time - timestamp).total_seconds()
        cached_tokens_info[token_hash[:8]] = {
            "age_seconds": age_seconds,
            "is_valid": age_seconds < 30
        }
    
    return {
        "active_locks_count": len(_refresh_locks),
        "cached_tokens_count": len(_cached_tokens),
        "active_locks": active_locks,
        "cached_tokens": cached_tokens_info,
        "cleanup_interval_seconds": _lock_cleanup_interval
    }

async def validate_access_token(
    authorization: Optional[str] = Header(None),
    response: Response = None,
) -> Tuple[dict, bool]:
    """Validate access token and refresh if needed.

    Expects Authorization header as: "Bearer <access_token>,<refresh_token>".

    Returns (user_dict, token_refreshed_bool).
    """
    if not authorization:
        print("401err - Authorization header is missing")
        raise HTTPException(status_code=500, detail="Authorization header is missing")

    try:
        if not authorization.startswith("Bearer "):
            print("401err - Invalid authorization header format not start with Bearer")
            raise HTTPException(status_code=500, detail="Invalid authorization header format")

        # Split tokens "access,refresh" and trim whitespace
        raw_tokens = authorization.replace("Bearer ", "", 1)
        tokens = [t.strip() for t in raw_tokens.split(',') if t is not None]
        if len(tokens) != 2:
            print("401err - Invalid token format not 2 tokens")
            raise HTTPException(status_code=500, detail="Invalid token format")

        access_token = tokens[0]
        refresh_token = tokens[1]

        # 1) Try to validate the access token
        try:
            user_response = supabase.auth.get_user(access_token)
            return user_response.user, False
        except Exception:
            # 2) Access token invalid/expired → try to refresh using refresh token
            try:
                user, session_data = await silent_refresh_token(refresh_token)
                
                if not user or not session_data:
                    print("401err - Failed to silent refresh token")
                    raise HTTPException(status_code=401, detail="Failed to refresh token")

                # Surface new tokens to the client
                if response and session_data:
                    print(f"DEBUG: Response object type: {type(response)}")
                    print(f"DEBUG: Session data keys: {list(session_data.keys())}")
                    
                    if session_data.get("access_token"):
                        response.headers["New-Access-Token"] = session_data["access_token"]
                        print(f"DEBUG: Set New-Access-Token header: {session_data['access_token'][:20]}...")
                        print(f"DEBUG: Header set successfully: {response.headers.get('New-Access-Token', 'NOT_SET')[:20]}...")
                    if session_data.get("refresh_token"):
                        response.headers["New-Refresh-Token"] = session_data["refresh_token"]
                        print(f"DEBUG: Set New-Refresh-Token header: {session_data['refresh_token'][:20]}...")
                        print(f"DEBUG: Header set successfully: {response.headers.get('New-Refresh-Token', 'NOT_SET')[:20]}...")
                else:
                    print(f"DEBUG: Response object is None: {response is None}")
                    print(f"DEBUG: Session data is None: {session_data is None}")
                print("401success - Token refreshed")

                return user, True
            except HTTPException:
                # Bubble up structured HTTPException
                raise
            except Exception as refresh_error:
                # Likely refresh token expired/invalid → return specific error for token refresh
                print("401err - TOKEN_REFRESH_REQUIRED: Refresh token expired or invalid. Please refresh your session.")
                raise HTTPException(
                    status_code=401,
                    detail="TOKEN_REFRESH_REQUIRED: Refresh token expired or invalid. Please refresh your session.",
                ) from refresh_error

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))