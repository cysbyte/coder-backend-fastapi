from fastapi import APIRouter, Response, Header
from typing import Optional
from pydantic import BaseModel
from controllers.role_controller import RoleController

router = APIRouter(
    prefix="/role",
    tags=["role"]
)

# Initialize controller
role_controller = RoleController()

# Request models
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
    """Add a new role to the roles table"""
    return await role_controller.add_role(request, authorization, response)

@router.get("/get/{user_id}")
async def get_roles_by_user(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Fetch the 10 most recent roles for a specific user"""
    return await role_controller.get_roles_by_user(user_id, authorization, response)

@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Delete a role by its ID"""
    return await role_controller.delete_role(role_id, authorization, response) 