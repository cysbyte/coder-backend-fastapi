"""
Authentication controller for handling auth-related operations
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Response
from pydantic import BaseModel
from gotrue.errors import AuthApiError
from utils.supabase_client import supabase
from utils.auth import get_token_expiration_info
from .base_controller import BaseController
import logging

logger = logging.getLogger(__name__)


class AuthController(BaseController):
    """Controller for authentication operations"""
    
    @staticmethod
    async def signup(request: BaseModel) -> Dict[str, Any]:
        """
        Handle user signup
        
        Args:
            request: SignUpRequest with email and password
            
        Returns:
            Auth response from Supabase
        """
        try:
            auth_response = supabase.auth.sign_up({
                "email": request.email,
                "password": request.password
            })
            return auth_response
        except AuthApiError as e:
            logger.error(f"Signup error: {e.message}")
            return {"error": e.message}
        except Exception as e:
            logger.error(f"Unexpected signup error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Signup failed: {str(e)}"
            )
    
    @staticmethod
    async def signin(request: BaseModel) -> Dict[str, Any]:
        """
        Handle user signin
        
        Args:
            request: SignInRequest with email and password
            
        Returns:
            Auth response with user data
        """
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
        except AuthApiError as e:
            logger.error(f"Signin error: {e.message}")
            raise HTTPException(
                status_code=401,
                detail=f"Signin failed: {e.message}"
            )
        except Exception as e:
            logger.error(f"Unexpected signin error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Signin failed: {str(e)}"
            )
    
    @staticmethod
    async def signout() -> Dict[str, Any]:
        """
        Handle user signout
        
        Returns:
            Success message
        """
        try:
            supabase.auth.signout()
            return {"message": "Signed out successfully"}
        except Exception as e:
            logger.error(f"Signout error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Signout failed: {str(e)}"
            )
    
    @staticmethod
    async def get_user() -> Dict[str, Any]:
        """
        Get current authenticated user
        
        Returns:
            User data from Supabase
        """
        try:
            user = supabase.auth.get_user()
            return user
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail=f"Failed to get user: {str(e)}"
            )
    
    @staticmethod
    async def send_validation_code(request: BaseModel) -> Dict[str, Any]:
        """
        Send validation code to user's email
        
        Args:
            request: ValidationCodeRequest with email
            
        Returns:
            Success response with message
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
        except AuthApiError as e:
            logger.error(f"Send code error: {e.message}")
            return {
                "success": False,
                "error": e.message
            }
        except Exception as e:
            logger.error(f"Unexpected send code error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def verify_validation_code(request: BaseModel) -> Dict[str, Any]:
        """
        Verify the validation code sent to user's email
        
        Args:
            request: VerifyCodeRequest with email and code
            
        Returns:
            Auth response with user data
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
        except AuthApiError as e:
            logger.error(f"Verify code error: {e.message}")
            return {
                "success": False,
                "error": e.message
            }
        except Exception as e:
            logger.error(f"Unexpected verify code error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def refresh_token(request: BaseModel) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            request: RefreshTokenRequest with refresh_token
            
        Returns:
            New tokens and user data
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
            logger.error(f"Refresh token error: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail=f"Token refresh failed: {str(e)}"
            )
    
    @staticmethod
    async def test_login_short_token(request: BaseModel) -> Dict[str, Any]:
        """
        Test endpoint that creates a session with very short token expiration
        
        Args:
            request: TestTokenRequest with email and password
            
        Returns:
            Auth response with user and session data
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
            
        except AuthApiError as e:
            logger.error(f"Test login error: {e.message}")
            raise HTTPException(status_code=401, detail=e.message)
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Unexpected test login error: {str(e)}")
            raise HTTPException(status_code=401, detail=str(e))
    
    @staticmethod
    async def get_token_info() -> Dict[str, Any]:
        """
        Get information about current token expiration settings (for debugging)
        
        Returns:
            Token expiration information
        """
        return {
            "success": True,
            "data": get_token_expiration_info()
        }
    
    @staticmethod
    async def test_headers(response: Response) -> Dict[str, Any]:
        """
        Test endpoint to verify custom headers are working
        
        Args:
            response: FastAPI Response object
            
        Returns:
            Success message
        """
        response.headers["New-Access-Token"] = "test-access-token-123"
        response.headers["New-Refresh-Token"] = "test-refresh-token-456"
        return {
            "success": True,
            "message": "Test headers set. Check response headers for New-Access-Token and New-Refresh-Token"
        }

