from fastapi import APIRouter, HTTPException, Response, Header, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from typing import Optional, Union
import asyncio
import base64
from services.task_processor import process_generate, process_debug, process_generate_multimodal, process_multimodal_debug
from services.websocket_service import manager
from utils.auth import validate_access_token
from services.database_service import get_user_credits
import uuid

router = APIRouter(
    prefix="/task",
    tags=["task"]
)

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    try:
        await manager.connect(websocket, task_id)
        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            print(data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, task_id)

@router.post("/multimodal_generate")
async def multimodal_generate(
    files: list[UploadFile] = File(..., description="List of image files to upload"),
    user_input: str = Form(..., description="User Input"),
    language: str = Form(..., description="Language of the user input"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None,
    user_id: str = Form(..., description="User ID of the uploader"),
    model: str = Form(..., description="Model to use for the task")
):
    try:
        # Validate files parameter
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided in the request"
            )

        # Validate number of files
        if len(files) > 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum 3 images allowed per request"
            )

        # First validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Check user's remaining credits
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
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Prepare images for processing
        images = []
        for file in files:
            # Validate file type
            if not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type for {file.filename}. Only images are allowed."
                )

            # Read file content
            content = await file.read()
            
            # Validate file size (e.g., 10MB limit)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if len(content) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum limit of 10MB for {file.filename}"
                )
            
            # Add image to list
            images.append({
                "content": content,
                "filename": file.filename
            })
        
        # Create async task with all images
        asyncio.create_task(process_generate_multimodal(
            task_id=task_id,
            images=images,
            user_id=user_id,
            user_input=user_input,
            language=language,
            model=model
        ))
        
        # Return task information
        return {
            "success": True,
            "task_id": task_id,
            "message": f"Processing started for {len(images)} image(s)",
            "user": {
                "id": user.id,
                "email": user.email
            },
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # For unexpected errors, return 500
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/multimodal_debug")
async def multimodal_debug(
    files: Optional[list[UploadFile]] = File(None, description="List of image files to upload"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    user_id: str = Form(..., description="User ID of the uploader"),
    task_id: str = Form(..., description="Task ID"),
    user_input: str = Form(..., description="User Input"),
    response: Response = None,
    model: str = Form(..., description="Model to use for the task"),
    language: str = Form(..., description="Language of the user input"),
    round: int = Form(..., description="Round number")
):
    try:
        # Validate number of files
        if files and len(files) > 2:
            raise HTTPException(
                status_code=400,
                detail="Maximum 2 images allowed per request"
            )

        # First validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)

        # Check user's remaining credits
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
        # Prepare images for processing
        images = []
        if files:
            for file in files:
                # Validate file type
                if not file.content_type.startswith('image/'):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type for {file.filename}. Only images are allowed."
                    )

            # Read file content
            content = await file.read()
            
            # Validate file size (e.g., 10MB limit)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if len(content) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum limit of 10MB for {file.filename}"
                )
            
            # Add image to list
            images.append({
                "content": content,
                "filename": file.filename
            })
        
        # Create async task with all images
        asyncio.create_task(process_multimodal_debug(
            user_id=user_id,
            task_id=task_id,
            images=images,
            user_input=user_input,
            language=language,
            model=model,
            round=round
        ))
        
        # Return task information
        return {
            "success": True,
            "task_id": task_id,
            "message": f"Processing started for {len(images)} image(s)",
            "user": {
                "id": user.id,
                "email": user.email
            },
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # For unexpected errors, return 500
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/generate")
async def upload_image(
    files: list[UploadFile] = File(..., description="List of image files to upload"),
    title: str = Form(None, description="Optional title for the batch of images"),
    description: str = Form(None, description="Optional description for the batch of images"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None,
    user_id: str = Form(..., description="User ID of the uploader"),
    user_input = Form(..., description="User Input"),
    language: str = Form(..., description="Language of the user input"),
    model: str = Form(..., description="Model to use for the task"),
    speech: str = Form(..., description="Speech of the user input")
):
    try:
        # Validate files parameter
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided in the request"
            )

        # Validate number of files
        if len(files) > 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum 3 images allowed per request"
            )

        # First validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
        # Check user's remaining credits
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
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Prepare images for processing
        images = []
        for file in files:
            # Validate file type
            if not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type for {file.filename}. Only images are allowed."
                )

            # Read file content
            content = await file.read()
            
            # Validate file size (e.g., 10MB limit)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if len(content) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum limit of 10MB for {file.filename}"
                )
            
            # Add image to list
            images.append({
                "content": content,
                "filename": file.filename
            })
        
        # Create async task with all images
        asyncio.create_task(process_generate(
            task_id=task_id,
            images=images,
            user_id=user_id,
            user_input=user_input,
            language=language,
            model=model,
            speech=speech
        ))
        
        # Return task information
        return {
            "success": True,
            "task_id": task_id,
            "message": f"Processing started for {len(images)} image(s)",
            "user": {
                "id": user.id,
                "email": user.email
            },
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # For unexpected errors, return 500
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/debug")
async def debug(
    files: Optional[list[UploadFile]] = File(None, description="List of image files to upload"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    user_id: str = Form(..., description="User ID of the uploader"),
    task_id: str = Form(..., description="Task ID"),
    user_input: str = Form(..., description="User Input"),
    response: Response = None,
    model: str = Form(..., description="Model to use for the task"),
    language: str = Form(..., description="Language of the user input"),
    round: int = Form(..., description="Round number"),
    speech: str = Form(..., description="Speech of the user input")
):
    try:
        # Validate number of files
        if files and len(files) > 2:
            raise HTTPException(
                status_code=400,
                detail="Maximum 2 images allowed per request"
            )

        # First validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)

        # Check user's remaining credits
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
        # Prepare images for processing
        images = []
        if files:
            for file in files:
                # Validate file type
                if not file.content_type.startswith('image/'):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type for {file.filename}. Only images are allowed."
                    )

            # Read file content
            content = await file.read()
            
            # Validate file size (e.g., 10MB limit)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if len(content) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum limit of 10MB for {file.filename}"
                )
            
            # Add image to list
            images.append({
                "content": content,
                "filename": file.filename
            })
        
        # Create async task with all images
        asyncio.create_task(process_debug(
            user_id=user_id,
            task_id=task_id,
            images=images,
            user_input=user_input,
            language=language,
            model=model,
            round=round,
            speech=speech
        ))
        
        # Return task information
        return {
            "success": True,
            "task_id": task_id,
            "message": f"Processing started for {len(images)} image(s)",
            "user": {
                "id": user.id,
                "email": user.email
            },
            "token_refreshed": token_refreshed
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # For unexpected errors, return 500
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
