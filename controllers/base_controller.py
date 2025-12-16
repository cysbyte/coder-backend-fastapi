"""
Base controller class with common functionality
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Response
from utils.auth import validate_access_token
import logging

logger = logging.getLogger(__name__)


class BaseController:
    """Base controller with common methods for all controllers"""
    
    @staticmethod
    async def authenticate_user(
        authorization: Optional[str],
        response: Response
    ) -> tuple[Dict[str, Any], Optional[bool]]:
        """
        Authenticate user and return user data with token refresh status
        
        Args:
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Tuple of (user_data, token_refreshed)
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            user, token_refreshed = await validate_access_token(authorization, response)
            return user, token_refreshed
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
    
    @staticmethod
    def format_success_response(
        data: Any,
        message: Optional[str] = None,
        token_refreshed: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Format a successful response
        
        Args:
            data: Response data
            message: Optional success message
            token_refreshed: Whether token was refreshed
            
        Returns:
            Formatted response dictionary
        """
        response = {
            "success": True,
            "data": data
        }
        
        if message:
            response["message"] = message
            
        if token_refreshed is not None:
            response["token_refreshed"] = token_refreshed
            
        return response
    
    @staticmethod
    def format_error_response(
        error: str,
        status_code: int = 500
    ) -> HTTPException:
        """
        Format an error response
        
        Args:
            error: Error message
            status_code: HTTP status code
            
        Returns:
            HTTPException to be raised
        """
        return HTTPException(
            status_code=status_code,
            detail=error
        )
    
    @staticmethod
    def handle_database_error(error: Exception) -> HTTPException:
        """
        Handle database-related errors with appropriate status codes
        
        Args:
            error: Exception object
            
        Returns:
            HTTPException with appropriate status code
        """
        error_msg = str(error).lower()
        
        if 'timeout' in error_msg or 'connection' in error_msg:
            return HTTPException(
                status_code=503,
                detail="Database connection timeout. Please try again."
            )
        elif 'duplicate' in error_msg or 'unique' in error_msg:
            return HTTPException(
                status_code=409,
                detail="Resource already exists."
            )
        elif 'permission' in error_msg or 'unauthorized' in error_msg:
            return HTTPException(
                status_code=403,
                detail="Insufficient permissions."
            )
        elif 'not found' in error_msg:
            return HTTPException(
                status_code=404,
                detail="Resource not found."
            )
        else:
            return HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(error)}"
            )

