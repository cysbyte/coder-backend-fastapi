"""
Task controller for handling task-related operations
"""
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from utils.supabase_client import supabase
from services.task_processor import process_generate, process_debug, process_generate_multimodal, process_multimodal_debug
from services.websocket_service import manager
from services.database_service import get_user_credits
from .base_controller import BaseController
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)


class TaskController(BaseController):
    """Controller for task operations"""
    
    @staticmethod
    async def validate_files(
        files: Optional[List[UploadFile]],
        max_files: int = 3,
        max_size_mb: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Validate and process uploaded files
        
        Args:
            files: List of uploaded files
            max_files: Maximum number of files allowed
            max_size_mb: Maximum file size in MB
            
        Returns:
            List of processed image data
            
        Raises:
            HTTPException: If validation fails
        """
        if files is None:
            return []
        
        # Validate number of files
        if len(files) > max_files:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {max_files} images allowed per request"
            )
        
        images = []
        max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
        
        for file in files:
            # Validate file type
            if not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type for {file.filename}. Only images are allowed."
                )
            
            # Read file content
            content = await file.read()
            
            # Validate file size
            if len(content) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum limit of {max_size_mb}MB for {file.filename}"
                )
            
            # Add image to list
            images.append({
                "content": content,
                "filename": file.filename
            })
        
        return images
    
    @staticmethod
    async def check_user_credits(user_id: str) -> Dict[str, Any]:
        """
        Check user's remaining credits
        
        Args:
            user_id: User ID
            
        Returns:
            Credits information
            
        Raises:
            HTTPException: If credits check fails or insufficient credits
        """
        credits_result = await get_user_credits(user_id)
        if not credits_result["success"]:
            raise HTTPException(
                status_code=404,
                detail=credits_result.get("error", "Failed to get user credits")
            )
            
        remaining_credits = credits_result["data"]["remaining_credits"]
        if remaining_credits <= 0:
            raise HTTPException(
                status_code=403,
                detail="Insufficient credits. Please purchase more credits to continue."
            )
        
        return credits_result["data"]
    
    @staticmethod
    async def generate(
        task_id: str,
        files: Optional[List[UploadFile]],
        user_id: str,
        user_input: str,
        programming_language: str,
        model: str,
        speech: str,
        language: str,
        screenshot_count: int,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Handle task generation request
        
        Args:
            task_id: Task ID
            files: List of uploaded image files
            user_id: User ID
            user_input: User input text
            programming_language: Programming language
            model: Model to use
            speech: Speech input
            language: Language
            screenshot_count: Number of screenshots
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Task creation response
        """
        try:
            # Handle case when screenshot_count is 0 - no images needed
            if screenshot_count == 0:
                # Validate that at least user_input or speech is provided
                if not user_input.strip() and not speech.strip():
                    raise HTTPException(
                        status_code=400,
                        detail="Either user_input or speech must be provided when no screenshots are provided"
                    )
                
                # Authenticate user
                user, token_refreshed = await BaseController.authenticate_user(
                    authorization, response
                )
                user = supabase.table('users').select("*").eq('id', user_id).execute().data[0]
                
                # Check credits
                await TaskController.check_user_credits(user_id)
                
                # Create async task with empty images list
                asyncio.create_task(process_generate(
                    task_id=task_id,
                    images=[],
                    user_id=user_id,
                    user_input=user_input,
                    programming_language=programming_language,
                    model=model,
                    speech=speech,
                    language=language
                ))
                
                return BaseController.format_success_response(
                    {
                        "task_id": task_id,
                        "message": "Processing started with no images",
                        "user": {
                            "id": user["id"],
                            "email": user["email"]
                        }
                    },
                    token_refreshed=None
                )
            
            # Validate files when screenshots are expected
            if not files:
                raise HTTPException(
                    status_code=400,
                    detail="No files provided in the request"
                )
            
            # Authenticate user
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            user = supabase.table('users').select("*").eq('id', user_id).execute().data[0]
            
            # Check credits
            await TaskController.check_user_credits(user_id)
            
            # Validate and process files
            images = await TaskController.validate_files(files, max_files=3)
            
            # Create async task
            asyncio.create_task(process_generate(
                task_id=task_id,
                images=images,
                user_id=user_id,
                user_input=user_input,
                programming_language=programming_language,
                model=model,
                speech=speech,
                language=language
            ))
            
            return BaseController.format_success_response(
                {
                    "task_id": task_id,
                    "message": f"Processing started for {len(images)} image(s)",
                    "user": {
                        "id": user["id"],
                        "email": user["email"]
                    }
                },
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Generate task error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @staticmethod
    async def debug(
        task_id: str,
        files: Optional[List[UploadFile]],
        user_id: str,
        user_input: str,
        programming_language: str,
        model: str,
        round: int,
        speech: str,
        language: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Handle task debug request
        
        Args:
            task_id: Task ID
            files: Optional list of uploaded image files
            user_id: User ID
            user_input: User input text
            programming_language: Programming language
            model: Model to use
            round: Round number
            speech: Speech input
            language: Language
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Task debug response
        """
        try:
            # Authenticate user
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            user = supabase.table('users').select("*").eq('id', user_id).execute().data[0]
            
            # Check credits
            await TaskController.check_user_credits(user_id)
            
            # Validate and process files (max 2 for debug)
            images = await TaskController.validate_files(files, max_files=2)
            
            # Create async task
            asyncio.create_task(process_debug(
                user_id=user_id,
                task_id=task_id,
                images=images,
                user_input=user_input,
                programming_language=programming_language,
                model=model,
                round=round,
                speech=speech,
                language=language
            ))
            
            return BaseController.format_success_response(
                {
                    "task_id": task_id,
                    "message": f"Processing started for {len(images)} image(s)",
                    "user": {
                        "id": user["id"],
                        "email": user["email"]
                    }
                },
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Debug task error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @staticmethod
    async def multimodal_generate(
        task_id: str,
        files: List[UploadFile],
        user_id: str,
        user_input: str,
        programming_language: str,
        model: str,
        speech: str,
        language: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Handle multimodal task generation request
        
        Args:
            task_id: Task ID
            files: List of uploaded image files
            user_id: User ID
            user_input: User input text
            programming_language: Programming language
            model: Model to use
            speech: Speech input
            language: Language
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Task creation response
        """
        try:
            # Validate files
            if not files:
                raise HTTPException(
                    status_code=400,
                    detail="No files provided in the request"
                )
            
            # Authenticate user
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            user = supabase.table('users').select("*").eq('id', user_id).execute().data[0]
            
            # Check credits
            await TaskController.check_user_credits(user_id)
            
            # Generate task ID if not provided
            if not task_id:
                task_id = str(uuid.uuid4())
            
            # Validate and process files
            images = await TaskController.validate_files(files, max_files=3)
            
            # Create async task
            asyncio.create_task(process_generate_multimodal(
                task_id=task_id,
                images=images,
                user_id=user_id,
                user_input=user_input,
                programming_language=programming_language,
                model=model,
                speech=speech,
                language=language
            ))
            
            return BaseController.format_success_response(
                {
                    "task_id": task_id,
                    "message": f"Processing started for {len(images)} image(s)",
                    "user": {
                        "id": user["id"],
                        "email": user["email"]
                    }
                },
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Multimodal generate error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @staticmethod
    async def multimodal_debug(
        task_id: str,
        files: Optional[List[UploadFile]],
        user_id: str,
        user_input: str,
        programming_language: str,
        model: str,
        round: int,
        speech: str,
        language: str,
        authorization: Optional[str],
        response: Response
    ) -> Dict[str, Any]:
        """
        Handle multimodal task debug request
        
        Args:
            task_id: Task ID
            files: Optional list of uploaded image files
            user_id: User ID
            user_input: User input text
            programming_language: Programming language
            model: Model to use
            round: Round number
            speech: Speech input
            language: Language
            authorization: Authorization header value
            response: FastAPI Response object
            
        Returns:
            Task debug response
        """
        try:
            # Authenticate user
            user, token_refreshed = await BaseController.authenticate_user(
                authorization, response
            )
            user = supabase.table('users').select("*").eq('id', user_id).execute().data[0]
            
            # Check credits
            await TaskController.check_user_credits(user_id)
            
            # Validate and process files (max 2 for debug)
            images = await TaskController.validate_files(files, max_files=2)
            
            # Create async task
            asyncio.create_task(process_multimodal_debug(
                user_id=user_id,
                task_id=task_id,
                images=images,
                user_input=user_input,
                programming_language=programming_language,
                model=model,
                round=round,
                speech=speech,
                language=language
            ))
            
            return BaseController.format_success_response(
                {
                    "task_id": task_id,
                    "message": f"Processing started for {len(images)} image(s)",
                    "user": {
                        "id": user["id"],
                        "email": user["email"]
                    }
                },
                token_refreshed=None
            )
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Multimodal debug error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @staticmethod
    async def websocket_endpoint(websocket: WebSocket, task_id: str):
        """
        WebSocket endpoint for task-specific real-time updates
        
        Args:
            websocket: WebSocket connection
            task_id: Task ID
        """
        try:
            await manager.connect(websocket, task_id)
            while True:
                # Keep connection alive and wait for messages
                data = await websocket.receive_text()
                logger.info(f"Received message for task {task_id}: {data}")
        except WebSocketDisconnect:
            await manager.disconnect(websocket, task_id)
            logger.info(f"Task {task_id} disconnected")

