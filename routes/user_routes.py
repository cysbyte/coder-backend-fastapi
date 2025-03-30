from fastapi import APIRouter, HTTPException, Response, Header
from typing import Optional
from pydantic import BaseModel
from services.database_service import get_user_credits
from utils.auth import validate_access_token
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

@router.get("/free_credits/{user_id}")
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
