from fastapi import APIRouter, Response, Header, WebSocket
from typing import Optional
from pydantic import BaseModel
from controllers.user_controller import UserController

router = APIRouter(
    prefix="/user",
    tags=["user"]
)

# Initialize controller
user_controller = UserController()

# Request models
class PricingTokenRequest(BaseModel):
    token: str

class UpdateUserNameRequest(BaseModel):
    first_name: str
    last_name: str

class CreateUserRequest(BaseModel):
    user_id: str
    email: str
    os: Optional[str] = None

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for user-specific real-time updates"""
    await user_controller.websocket_endpoint(websocket, user_id)

@router.post("/create")
async def create_user(
    request: CreateUserRequest,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Create a new user record in the users table"""
    return await user_controller.create_user(request, authorization, response)

@router.post("/payment_successful/{user_id}")
async def payment_successful(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Handle successful payment and notify frontend"""
    return await user_controller.payment_successful(user_id, authorization, response)

@router.post("/cancel_subscription/{user_id}")
async def cancel_subscription(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Handle subscription cancellation and notify frontend"""
    return await user_controller.cancel_subscription(user_id, authorization, response)

@router.get("/credits/{user_id}")
async def get_credits(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Get user's free credits"""
    return await user_controller.get_credits(user_id, authorization, response)

@router.post("/update-name/{user_id}")
async def update_user_name(
    user_id: str,
    request: UpdateUserNameRequest,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Update user's first and last name"""
    return await user_controller.update_user_name(user_id, request, authorization, response)

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Delete a user record from the users table and all associated roles"""
    return await user_controller.delete_user(user_id, authorization, response)

@router.post("/verify-pricing-token")
async def verify_pricing_token(
    request: PricingTokenRequest,
    response: Response = None
):
    """Verify pricing token and decode user information"""
    return await user_controller.verify_pricing_token(request, response)

@router.get("/subscription-days/{user_id}")
async def get_subscription_days(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """Get remaining days of user's current subscription"""
    return await user_controller.get_subscription_days(user_id, authorization, response)
