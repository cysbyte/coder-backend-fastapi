"""
User controller for handling user-related operations
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from utils.supabase_client import supabase
from services.database_service import get_user_credits
from services.websocket_service import manager
from .base_controller import BaseController
import jwt
import os
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class UserController(BaseController):
    """Controller for user operations"""
    
    @staticmethod
    async def create_user(
        request: BaseModel,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Create a new user record in the users table
        
        Args:
            request: CreateUserRequest with user_id, email, and optional os
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Created user data
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Check if user already exists
            existing_user = supabase.table('users').select("*").eq('id', request.user_id).execute()
            
            if existing_user.data and len(existing_user.data) > 0:
                # User exists, check if we need to update OS field
                if request.os is not None:
                    # Update OS field if provided
                    update_result = supabase.table('users').update({
                        'os': request.os
                    }).eq('id', request.user_id).execute()
                    
                    if update_result.data:
                        return BaseController.format_success_response(
                            update_result.data[0],
                            token_refreshed=token_refreshed
                        )
                
                # Return existing user data if no update needed
                return BaseController.format_success_response(
                    existing_user.data[0],
                    token_refreshed=token_refreshed
                )
            
            # Insert new user record
            result = supabase.table('users').insert({
                'id': request.user_id,
                'email': request.email,
                'os': request.os,
            }).execute()
            
            if not result.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create user"
                )
                
            return BaseController.format_success_response(
                result.data[0],
                token_refreshed=token_refreshed
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Create user error: {str(e)}")
            raise BaseController.handle_database_error(e)
    
    @staticmethod
    async def get_credits(
        user_id: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Get user's free credits
        
        Args:
            user_id: User ID
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            User credits data
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Get user credits
            credits_result = await get_user_credits(user_id)
            
            if not credits_result["success"]:
                raise HTTPException(
                    status_code=404,
                    detail=credits_result.get("error", "Failed to get user credits")
                )
                
            return BaseController.format_success_response(
                credits_result["data"],
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Get credits error: {str(e)}")
            raise BaseController.handle_database_error(e)
    
    @staticmethod
    async def update_user_name(
        user_id: str,
        request: BaseModel,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Update user's first and last name
        
        Args:
            user_id: User ID
            request: UpdateUserNameRequest with first_name and last_name
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Updated user data
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
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
                
            return BaseController.format_success_response(
                result.data[0],
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Update user name error: {str(e)}")
            raise BaseController.handle_database_error(e)
    
    @staticmethod
    async def delete_user(
        user_id: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Delete a user record from the users table and all associated data
        
        Args:
            user_id: User ID
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Deletion confirmation with counts
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # First delete all associated data
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
                
            return BaseController.format_success_response(
                {
                    "user": user_result.data[0],
                    "roles_deleted": len(roles_result.data) if roles_result.data else 0,
                    "tasks_deleted": len(tasks_result.data) if tasks_result.data else 0,
                    "subscriptions_deleted": len(subscriptions_result.data) if subscriptions_result.data else 0,
                    "payments_deleted": len(payments_result.data) if payments_result.data else 0,
                    "credits_transactions_deleted": len(credits_transactions_result.data) if credits_transactions_result.data else 0
                },
                message="User and associated data deleted successfully",
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Delete user error: {str(e)}")
            raise BaseController.handle_database_error(e)
    
    @staticmethod
    async def verify_pricing_token(
        request: BaseModel,
        response: Response
    ) -> Dict[str, Any]:
        """
        Verify pricing token and decode user information
        
        Args:
            request: PricingTokenRequest with token
            response: FastAPI Response object
            
        Returns:
            Decoded user information
        """
        try:
            # Get secret key from environment variables
            secret_key = os.getenv("JWT_SECRET")
            if not secret_key:
                raise HTTPException(
                    status_code=500,
                    detail="JWT_SECRET not configured"
                )
            
            try:
                # Decode the token
                decoded_data = jwt.decode(request.token, secret_key, algorithms=["HS256"])
            except jwt.InvalidSignatureError as e:
                logger.error(f"Invalid signature error: {str(e)}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token signature"
                )
            except jwt.InvalidTokenError as e:
                logger.error(f"Invalid token error: {str(e)}")
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid token: {str(e)}"
                )
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
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
                
            return BaseController.format_success_response({
                "email": email,
                "avatar": avatar,
                "accessToken": access_token,
                "refreshToken": refresh_token
            })
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Verify pricing token error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @staticmethod
    async def get_subscription_days(
        user_id: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Get remaining days of user's current subscription
        
        Args:
            user_id: User ID
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Subscription days information
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Get user's subscription
            subscription_result = supabase.table('subscriptions').select("*").eq('user_id', user_id).eq('status', 'active').execute()
            
            if not subscription_result.data or len(subscription_result.data) == 0:
                return BaseController.format_success_response(
                    {
                        "remaining_days": 0,
                        "current_period_end": datetime.now(timezone.utc).isoformat()
                    },
                    token_refreshed=None
                )
                
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
            
            return BaseController.format_success_response(
                {
                    "remaining_days": max(0, remaining_days),
                    "current_period_end": current_period_end
                },
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Get subscription days error: {str(e)}")
            raise BaseController.handle_database_error(e)
    
    @staticmethod
    async def payment_successful(
        user_id: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Handle successful payment and notify frontend via WebSocket
        
        Args:
            user_id: User ID
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Success message
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Send notification through WebSocket
            await manager.send_message(user_id, {
                "type": "payment_successful",
                "message": "Payment processed successfully"
            })
            
            return BaseController.format_success_response(
                None,
                message="Payment notification sent successfully",
                token_refreshed=token_refreshed
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Payment successful notification error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @staticmethod
    async def cancel_subscription(
        user_id: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Handle subscription cancellation and notify frontend via WebSocket
        
        Args:
            user_id: User ID
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Success message
        """
        try:
            # Validate the access token
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            
            # Send notification through WebSocket
            await manager.send_message(user_id, {
                "type": "subscription_cancelled",
                "message": "Your subscription has been cancelled successfully"
            })
            
            return BaseController.format_success_response(
                None,
                message="Subscription cancellation notification sent successfully",
                token_refreshed=token_refreshed
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Cancel subscription notification error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @staticmethod
    async def websocket_endpoint(websocket: WebSocket, user_id: str):
        """
        WebSocket endpoint for user-specific real-time updates
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
        """
        try:
            await manager.connect(websocket, user_id)
            while True:
                # Keep connection alive and wait for messages
                data = await websocket.receive_text()
                logger.info(f"Received message from user {user_id}: {data}")
                
                # Here you can add specific message handling logic for user updates
                # For example, sending credit updates, role changes, etc.
                
        except WebSocketDisconnect:
            await manager.disconnect(websocket, user_id)
            logger.info(f"User {user_id} disconnected")

