from fastapi import APIRouter, HTTPException, Response, Header
from typing import Optional
from pydantic import BaseModel
from services.database_service import get_user_credits
from utils.auth import validate_access_token
from utils.supabase_client import supabase
import jwt
import os
from dotenv import load_dotenv

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
                "tasks_deleted": len(tasks_result.data) if tasks_result.data else 0
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
