from fastapi import APIRouter, HTTPException, Response, Header
from typing import Optional
from pydantic import BaseModel
from utils.supabase_client import supabase, insert_with_retry, select_with_retry, delete_with_retry
from utils.auth import validate_access_token
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/role",
    tags=["role"]
)

class RoleRequest(BaseModel):
    user_id: str
    company_name: str
    role: str
    description: str

@router.post("/add")
async def add_role(
    request: RoleRequest,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Add a new role to the roles table
    """
    try:
        # Validate the access token
        # user, token_refreshed = await validate_access_token(authorization, response)
        
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
        return {
            "success": True,
            "data": result.data[0],
            "token_refreshed": None
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error adding role: {str(e)}")
        
        # Provide more specific error messages based on the error type
        if 'timeout' in error_msg or 'connection' in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database connection timeout. Please try again."
            )
        elif 'duplicate' in error_msg or 'unique' in error_msg:
            raise HTTPException(
                status_code=409,
                detail="Role already exists for this user and company."
            )
        elif 'permission' in error_msg or 'unauthorized' in error_msg:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to add role."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

@router.get("/get/{user_id}")
async def get_roles_by_user(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Fetch the 10 most recent roles for a specific user
    """
    try:
        # Validate the access token
        # user, token_refreshed = await validate_access_token(authorization, response)
        
        # Query roles table for the user's 10 most recent roles with retry logic
        result = await select_with_retry('roles', user_id=user_id)
        
        # Apply ordering and limit (since select_with_retry doesn't support complex queries yet)
        if result.data:
            # Sort by created_at descending and limit to 10
            sorted_data = sorted(result.data, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
        else:
            sorted_data = []
            
        logger.info(f"Successfully retrieved {len(sorted_data)} roles for user {user_id}")
        return {
            "success": True,
            "data": sorted_data,
            "token_refreshed": None
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error getting roles for user {user_id}: {str(e)}")
        
        if 'timeout' in error_msg or 'connection' in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database connection timeout. Please try again."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Delete a role by its ID
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
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
        return {
            "success": True,
            "data": result.data[0],
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error deleting role {role_id}: {str(e)}")
        
        if 'timeout' in error_msg or 'connection' in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database connection timeout. Please try again."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            ) 