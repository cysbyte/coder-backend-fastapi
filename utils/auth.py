from typing import Optional, Tuple
from fastapi import Header, HTTPException, Response
from utils.supabase_client import supabase

async def validate_access_token(
    authorization: Optional[str] = Header(None),
    response: Response = None,
) -> Tuple[dict, bool]:
    """Validate access token and refresh if needed.

    Expects Authorization header as: "Bearer <access_token>,<refresh_token>".

    Returns (user_dict, token_refreshed_bool).
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")

        # Split tokens "access,refresh" and trim whitespace
        raw_tokens = authorization.replace("Bearer ", "", 1)
        tokens = [t.strip() for t in raw_tokens.split(',') if t is not None]
        if len(tokens) != 2:
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
                refresh_response = supabase.auth.refresh_session(refresh_token)

                if not refresh_response or not getattr(refresh_response, "user", None):
                    raise HTTPException(status_code=401, detail="Failed to refresh token")

                # Surface new tokens to the client
                if response and getattr(refresh_response, "session", None):
                    if getattr(refresh_response.session, "access_token", None):
                        response.headers["New-Access-Token"] = refresh_response.session.access_token
                    if getattr(refresh_response.session, "refresh_token", None):
                        response.headers["New-Refresh-Token"] = refresh_response.session.refresh_token

                return refresh_response.user, True
            except HTTPException:
                # Bubble up structured HTTPException
                raise
            except Exception as refresh_error:
                # Likely refresh token expired/invalid → require re-authentication
                raise HTTPException(
                    status_code=401,
                    detail="Refresh token expired or invalid. Please sign in again.",
                ) from refresh_error

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))