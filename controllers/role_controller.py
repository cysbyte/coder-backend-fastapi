"""
Role controller for handling role-related operations
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Response
from pydantic import BaseModel
from utils.supabase_client import insert_with_retry, select_with_retry, delete_with_retry
from .base_controller import BaseController
import logging

logger = logging.getLogger(__name__)


class RoleController(BaseController):
    """Controller for role operations"""
    
    @staticmethod
    async def add_role(
        request: BaseModel,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Add a new role to the roles table
        
        Args:
            request: RoleRequest with user_id, company_name, role, and description
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Created role data
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Prepare role data
            role_data = {
                "user_id": request.user_id,
                "company_name": request.company_name,
                "role": request.role,
                "description": request.description
            }
            
            # Insert the role data into the 'roles' table with retry logic
            result = await insert_with_retry('roles', role_data)
            
            if not result.data:
                logger.error("Failed to add role: No data returned from database")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to add role: Database operation returned no data"
                )
                
            logger.info(f"Successfully added role for user {request.user_id}")
            return BaseController.format_success_response(
                result.data[0],
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error adding role: {str(e)}")
            raise BaseController.handle_database_error(e)
    
    @staticmethod
    async def get_roles_by_user(
        user_id: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Fetch the 10 most recent roles for a specific user
        
        Args:
            user_id: User ID
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            List of user roles (max 10)
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Query roles table for the user's roles with retry logic
            result = await select_with_retry('roles', user_id=user_id)
            
            # Apply ordering and limit (since select_with_retry doesn't support complex queries yet)
            if result.data:
                # Sort by created_at descending and limit to 10
                sorted_data = sorted(
                    result.data,
                    key=lambda x: x.get('created_at', ''),
                    reverse=True
                )[:10]
            else:
                sorted_data = []
                
            logger.info(f"Successfully retrieved {len(sorted_data)} roles for user {user_id}")
            return BaseController.format_success_response(
                sorted_data,
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error getting roles for user {user_id}: {str(e)}")
            raise BaseController.handle_database_error(e)
    
    @staticmethod
    async def delete_role(
        role_id: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Delete a role by its ID
        
        Args:
            role_id: Role ID
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Deleted role data
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # First check if the role exists with retry logic
            role_result = await select_with_retry('roles', id=role_id)
            
            if not role_result.data or len(role_result.data) == 0:
                logger.warning(f"Role not found for deletion: {role_id}")
                raise HTTPException(
                    status_code=404,
                    detail="Role not found"
                )
                
            # Delete the role with retry logic
            result = await delete_with_retry('roles', id=role_id)
            
            if not result.data:
                logger.error(f"Failed to delete role {role_id}: No data returned from database")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to delete role: Database operation returned no data"
                )
                
            logger.info(f"Successfully deleted role {role_id}")
            return BaseController.format_success_response(
                result.data[0],
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error deleting role {role_id}: {str(e)}")
            raise BaseController.handle_database_error(e)

