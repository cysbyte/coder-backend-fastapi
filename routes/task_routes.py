from fastapi import APIRouter, HTTPException, Response, Header, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from typing import Optional, Union
import asyncio
from services.task_processor import process_image_task, process_debug_task
from services.websocket_service import manager
from utils.auth import validate_access_token
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

@router.post("/upload/image")
async def upload_image(
    files: list[UploadFile] = File(..., description="List of image files to upload"),
    title: str = Form(None, description="Optional title for the batch of images"),
    description: str = Form(None, description="Optional description for the batch of images"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None,
    user_id: str = Form(..., description="User ID of the uploader")
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
        asyncio.create_task(process_image_task(
            task_id=task_id,
            images=images,
            user_id=user_id
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

@router.post("/upload/debug")
async def debug(
    files: list[UploadFile] = File(..., description="List of image files to upload"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    user_id: str = Form(..., description="User ID of the uploader"),
    task_id: str = Form(..., description="Task ID"),
    debug_message: str = Form(..., description="Debug message"),
    response: Response = None
):
    try:
        # Validate files parameter
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided in the request"
            )

        # Validate number of files
        if len(files) > 2:
            raise HTTPException(
                status_code=400,
                detail="Maximum 2 images allowed per request"
            )

        # First validate the access token
        user, token_refreshed = await validate_access_token(authorization, response)
        
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
        asyncio.create_task(process_debug_task(
            user_id=user_id,
            task_id=task_id,
            images=images,
            debug_message=debug_message,
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
