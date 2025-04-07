from fastapi import APIRouter, HTTPException, Response, Header
from typing import Optional
from pydantic import BaseModel
from utils.supabase_client import supabase
from utils.auth import validate_access_token

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
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Prepare role data
        role_data = {
            "user_id": request.user_id,
            "company_name": request.company_name,
            "role": request.role,
            "description": request.description
        }
        
        # Insert the role data into the 'roles' table
        result = supabase.table('roles').insert(role_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to add role"
            )
            
        return {
            "success": True,
            "data": result.data[0],
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/get/{user_id}")
async def get_roles_by_user(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Fetch the 3 most recent roles for a specific user
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Query roles table for the user's 3 most recent roles
        result = supabase.table('roles')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(3)\
            .execute()
        
        if not result.data:
            return {
                "success": True,
                "data": [],
                "token_refreshed": token_refreshed
            }
            
        return {
            "success": True,
            "data": result.data,
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 