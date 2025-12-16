"""
Coder controller for handling coder-related operations
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Response
from utils.supabase_client_coder import select_with_retry
from .base_controller import BaseController
import logging

logger = logging.getLogger(__name__)


class CoderController(BaseController):
    """Controller for coder operations"""
    
    @staticmethod
    async def get_coder_data(
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Get coder data from the coder database
        
        Args:
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Coder data
        """
        try:
            # Validate access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Query coder database
            result = await select_with_retry('coders', id=1)
            
            return BaseController.format_success_response(
                result.data,
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error getting coder data: {str(e)}")
            error_msg = str(e).lower()
            if 'timeout' in error_msg or 'connection' in error_msg:
                raise HTTPException(
                    status_code=503,
                    detail="Database connection timeout. Please try again."
                )
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

