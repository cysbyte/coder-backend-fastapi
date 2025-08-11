from typing import Optional, Tuple
from fastapi import Header, HTTPException, Response
from utils.supabase_client import supabase

async def silent_refresh_token(refresh_token: str) -> Tuple[dict, dict]:
    """
    Attempt to refresh tokens silently without raising HTTP exceptions.
    Returns (user_dict, session_dict) or (None, None) if refresh fails.
    """
    try:
        refresh_response = supabase.auth.refresh_session(refresh_token)
        
        if not refresh_response or not getattr(refresh_response, "user", None):
            return None, None
        
        session = getattr(refresh_response, "session", None)
        if not session:
            return None, None
            
        return refresh_response.user, {
            "access_token": getattr(session, "access_token", None),
            "refresh_token": getattr(session, "refresh_token", None),
            "expires_at": getattr(session, "expires_at", None)
        }
        
    except Exception:
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

async def validate_access_token(
    authorization: Optional[str] = Header(None),
    response: Response = None,
) -> Tuple[dict, bool]:
    """Validate access token and refresh if needed.

    Expects Authorization header as: "Bearer <access_token>,<refresh_token>".

    Returns (user_dict, token_refreshed_bool).
    """
    if not authorization:
        print("401: Authorization header is missing")
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    try:
        if not authorization.startswith("Bearer "):
            print("401: Invalid authorization header format not start with Bearer")
            raise HTTPException(status_code=401, detail="Invalid authorization header format")

        # Split tokens "access,refresh" and trim whitespace
        raw_tokens = authorization.replace("Bearer ", "", 1)
        tokens = [t.strip() for t in raw_tokens.split(',') if t is not None]
        if len(tokens) != 2:
            print("401: Invalid token format not 2 tokens")
            raise HTTPException(status_code=401, detail="Invalid token format")

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
                    print("401: Failed to silent refresh token")
                    raise HTTPException(status_code=401, detail="Failed to refresh token")

                # Surface new tokens to the client
                if response and session_data:
                    if session_data.get("access_token"):
                        response.headers["New-Access-Token"] = session_data["access_token"]
                    if session_data.get("refresh_token"):
                        response.headers["New-Refresh-Token"] = session_data["refresh_token"]

                return user, True
            except HTTPException:
                # Bubble up structured HTTPException
                raise
            except Exception as refresh_error:
                # Likely refresh token expired/invalid → return specific error for token refresh
                print("401: TOKEN_REFRESH_REQUIRED: Refresh token expired or invalid. Please refresh your session.")
                raise HTTPException(
                    status_code=401,
                    detail="TOKEN_REFRESH_REQUIRED: Refresh token expired or invalid. Please refresh your session.",
                ) from refresh_error

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))