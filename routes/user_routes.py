from fastapi import APIRouter, HTTPException, Response, Header, WebSocket, WebSocketDisconnect
from typing import Optional
from pydantic import BaseModel
from services.database_service import get_user_credits
from utils.auth import validate_access_token
from utils.supabase_client import supabase
from services.websocket_service import manager
import jwt
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
# Load environment variables
load_dotenv()

# Verify JWT secret key is loaded
jwt_secret = os.getenv("JWT_SECRET")
if not jwt_secret:
    print("WARNING: JWT_SECRET not found in environment variables")
else:
    print(f"JWT_SECRET loaded: {jwt_secret[:4]}...")  # Only print first 4 chars for security

router = APIRouter(
    prefix="/user",
    tags=["user"]
)

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
    """
    WebSocket endpoint for user-specific real-time updates
    """
    try:
        await manager.connect(websocket, user_id)
        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            print(f"Received message from user {user_id}: {data}")
            
            # Here you can add specific message handling logic for user updates
            # For example, sending credit updates, role changes, etc.
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        print(f"User {user_id} disconnected")

@router.post("/create")
async def create_user(
    request: CreateUserRequest,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Create a new user record in the users table
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Check if user already exists
        existing_user = supabase.table('users').select("*").eq('id', request.user_id).execute()
        
        if existing_user.data and len(existing_user.data) > 0:
            return {
                "success": True,
                "data": existing_user.data[0],
                "token_refreshed": token_refreshed
            }
        
        # Insert new user record
        result = supabase.table('users').insert({
            'id': request.user_id,
            'email': request.email,
            'os': request.os,
        }).execute()

        print('request.os', request.os)
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create user"
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

@router.post("/payment_successful/{user_id}")
async def payment_successful(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Handle successful payment and notify frontend
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Send notification through WebSocket
        await manager.send_message(user_id, {
            "type": "payment_successful",
            "message": "Payment processed successfully"
        })
        
        return {
            "success": True,
            "message": "Payment notification sent successfully",
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/cancel_subscription/{user_id}")
async def cancel_subscription(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Handle subscription cancellation and notify frontend
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Send notification through WebSocket
        await manager.send_message(user_id, {
            "type": "subscription_cancelled",
            "message": "Your subscription has been cancelled successfully"
        })
        
        return {
            "success": True,
            "message": "Subscription cancellation notification sent successfully",
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/credits/{user_id}")
async def get_credits(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Get user's free credits
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Get user credits
        credits_result = await get_user_credits(user_id)
        
        if not credits_result["success"]:
            raise HTTPException(
                status_code=404,
                detail=credits_result.get("error", "Failed to get user credits")
            )
            
        return {
            "success": True,
            "data": credits_result["data"],
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/update-name/{user_id}")
async def update_user_name(
    user_id: str,
    request: UpdateUserNameRequest,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Update user's first and last name
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Update user data
        result = supabase.table('users').update({
            'first_name': request.first_name,
            'last_name': request.last_name
        }).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to update user name"
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

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Delete a user record from the users table and all associated roles
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # First delete all associated roles
        roles_result = supabase.table('roles').delete().eq('user_id', user_id).execute()
        tasks_result = supabase.table('tasks').delete().eq('user_id', user_id).execute()
        subscriptions_result = supabase.table('subscriptions').delete().eq('user_id', user_id).execute()
        payments_result = supabase.table('payments').delete().eq('user_id', user_id).execute()
        credits_transactions_result = supabase.table('credits_transactions').delete().eq('user_id', user_id).execute()
        
        # Then delete the user record
        user_result = supabase.table('users').delete().eq('id', user_id).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=404,
                detail="User not found or already deleted"
            )
            
        return {
            "success": True,
            "message": "User and associated roles deleted successfully",
            "data": {
                "user": user_result.data[0],
                "roles_deleted": len(roles_result.data) if roles_result.data else 0,
                "tasks_deleted": len(tasks_result.data) if tasks_result.data else 0,
                "subscriptions_deleted": len(subscriptions_result.data) if subscriptions_result.data else 0,
                "payments_deleted": len(payments_result.data) if payments_result.data else 0,
                "credits_transactions_deleted": len(credits_transactions_result.data) if credits_transactions_result.data else 0
            },
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/verify-pricing-token")
async def verify_pricing_token(
    request: PricingTokenRequest,

    response: Response = None
):
    """
    Verify pricing token and decode user information
    """
    try:
        
        # Get secret key from environment variables
        secret_key = os.getenv("JWT_SECRET") 
        print(f"Using secret key: {secret_key}")
            
        try:
            print(f"Received token: {request.token}")
            
            try:
                # Decode the token
                decoded_data = jwt.decode(request.token, secret_key, algorithms=["HS256"])
                print(f"Decoded data: {decoded_data}")
            except jwt.InvalidSignatureError as e:
                print(f"Invalid signature error: {str(e)}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token signature"
                )
            except jwt.InvalidTokenError as e:
                print(f"Invalid token error: {str(e)}")
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid token: {str(e)}"
                )
            
            # Extract user information
            email = decoded_data.get("email")
            avatar = decoded_data.get("avatar")
            access_token = decoded_data.get("accessToken")
            refresh_token = decoded_data.get("refreshToken")
            
            if not email:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid token: email not found"
                )
                
            return {
                "success": True,
                "data": {
                    "email": email,
                    "avatar": avatar,
                    "accessToken": access_token,
                    "refreshToken": refresh_token
                },
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/subscription-days/{user_id}")
async def get_subscription_days(
    user_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None
):
    """
    Get remaining days of user's current subscription
    """
    try:
        # Validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Get user's subscription
        subscription_result = supabase.table('subscriptions').select("*").eq('user_id', user_id).eq('status', 'active').execute()
        
        if not subscription_result.data or len(subscription_result.data) == 0:
            return {
                "success": True,
                "data": {
                    "remaining_days": 0,
                    "current_period_end": datetime.now(timezone.utc).isoformat()
                },
                "token_refreshed": token_refreshed
            }
            
        subscription = subscription_result.data[0]
        current_period_end = subscription.get('current_period_end')
        
        if not current_period_end:
            raise HTTPException(
                status_code=400,
                detail="Invalid subscription data: missing period end date"
            )
            
        # Calculate remaining days
        current_time = datetime.now(timezone.utc)
        end_date = datetime.fromisoformat(current_period_end.replace('Z', '+00:00'))
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        remaining_days = (end_date - current_time).days
        
        return {
            "success": True,
            "data": {
                "remaining_days": max(0, remaining_days),
                "current_period_end": current_period_end
            },
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
