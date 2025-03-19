from typing import Optional
from fastapi import Header, HTTPException
from utils.supabase_client import supabase

async def validate_access_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        # Check if the header starts with "Bearer "
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        # Extract the token
        token = authorization.replace("Bearer ", "")
        
        try:
            # First try to validate the token
            user = supabase.auth.get_user(token)
            return user.user
        except Exception as token_error:
            # If token validation fails, try to refresh it
            try:
                # Get refresh token from the Authorization header
                # Format should be: "Bearer access_token,refresh_token"
                tokens = token.split(',')
                if len(tokens) != 2:
                    raise HTTPException(status_code=401, detail="Invalid token format")
                
                access_token = tokens[0]
                refresh_token = tokens[1]

                # Try to refresh the session
                refresh_response = supabase.auth.refresh_session(refresh_token)
                
                if not refresh_response or not refresh_response.user:
                    raise HTTPException(status_code=401, detail="Failed to refresh token")
                
                # Return both the new token and user info
                return {
                    "user": refresh_response.user,
                    "new_access_token": refresh_response.session.access_token,
                    "new_refresh_token": refresh_response.session.refresh_token,
                    "token_refreshed": True
                }
                
            except Exception as refresh_error:
                raise HTTPException(status_code=401, detail="Token expired and refresh failed")
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))