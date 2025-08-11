from fastapi import APIRouter, HTTPException, Response, Header
from typing import Optional
from pydantic import BaseModel
from supabase import Client
from gotrue.errors import AuthApiError
from utils.supabase_client import supabase
from utils.auth import validate_access_token, get_token_expiration_info

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

class SignInRequest(BaseModel):
    email: str
    password: str

class SignUpRequest(BaseModel):
    email: str
    password: str

class ValidationCodeRequest(BaseModel):
    email: str

class VerifyCodeRequest(BaseModel):
    email: str
    code: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TestTokenRequest(BaseModel):
    email: str
    password: str

@router.post("/signup")
def signup(request: SignUpRequest):
    try:
        auth_response = supabase.auth.sign_up({ "email": request.email, "password": request.password })
        return auth_response
    except AuthApiError as e:
        return {"error": e.message}

@router.post("/signin")
async def login(request: SignInRequest):
    try:
        user = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if user.user:
            # Check if user exists in users table
            user_query = supabase.table('users').select("*").eq('user_id', user.user.id).execute()
            
            # If user doesn't exist in the users table, create a record
            if not user_query.data:
                user_data = {
                    "user_id": user.user.id,
                    "email": request.email,
                }
                # Insert the user data into the 'users' table
                user_record = supabase.table('users').insert(user_data).execute()
                return {
                    "auth": user,
                    "user_record": user_record.data
                }
            
            return {
                "auth": user,
                "user_record": user_query.data[0]
            }
            
        return user
    except Exception as e:
        return {"error": str(e)}

@router.post("/signout")
def logout():
    supabase.auth.signout()
    return {"message": "Signed out successfully"}

@router.get("/user")
def get_user():
    user = supabase.auth.get_user()
    return user

@router.post("/send-code")
async def send_validation_code(request: ValidationCodeRequest):
    """
    Send validation code to user's email
    """
    try:
        # Send validation code using Supabase
        response = supabase.auth.sign_in_with_otp({
            "email": request.email
        })
        
        return {
            "success": True,
            "message": "Validation code sent successfully",
            "data": response
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/test-login-short-token")
async def test_login_short_token(request: TestTokenRequest):
    """
    Test endpoint that creates a session with very short token expiration
    """
    try:
        # Sign in the user
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Note: The actual token expiration is controlled by Supabase JWT settings
        # This endpoint just provides a way to test the flow
        return {
            "success": True,
            "message": "Test login successful. Tokens will expire based on Supabase JWT settings.",
            "user": auth_response.user,
            "session": auth_response.session
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/refresh-token")
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token without requiring full authentication
    """
    try:
        # Attempt to refresh the session using the provided refresh token
        refresh_response = supabase.auth.refresh_session(request.refresh_token)
        
        if not refresh_response or not getattr(refresh_response, "user", None):
            raise HTTPException(
                status_code=401,
                detail="Failed to refresh token. Please sign in again."
            )
        
        # Return the new tokens
        session = getattr(refresh_response, "session", None)
        if session:
            return {
                "success": True,
                "user": refresh_response.user,
                "access_token": getattr(session, "access_token", None),
                "refresh_token": getattr(session, "refresh_token", None),
                "expires_at": getattr(session, "expires_at", None)
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid session data received"
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.get("/token-info")
async def get_token_info():
    """
    Get information about current token expiration settings (for debugging)
    """
    return {
        "success": True,
        "data": get_token_expiration_info()
    }

@router.post("/verify-code")
async def verify_validation_code(request: VerifyCodeRequest):
    """
    Verify the validation code sent to user's email
    """
    try:
        # Verify the code using Supabase
        response = supabase.auth.verify_otp({
            "email": request.email,
            "token": request.code,
            "type": "email"
        })
        
        if response.user:
            # Check if user exists in users table
            user_query = supabase.table('users').select("*").eq('id', response.user.id).execute()
            
            # If user doesn't exist in the users table, create a record
            if not user_query.data:
                user_data = {
                    "id": response.user.id,
                    "email": request.email,
                }
                # Insert the user data into the 'users' table
                user_record = supabase.table('users').insert(user_data).execute()
                return {
                    "success": True,
                    "auth": response,
                    "user_record": user_record.data
                }
            
            return {
                "success": True,
                "auth": response,
                "user_record": user_query.data[0]
            }
            
        return {
            "success": False,
            "error": "Invalid validation code"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
