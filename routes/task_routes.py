from fastapi import APIRouter, Response, Header, UploadFile, File, Form, WebSocket
from typing import Optional
from controllers.task_controller import TaskController

router = APIRouter(
    prefix="/task",
    tags=["task"]
)

# Initialize controller
task_controller = TaskController()

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for task-specific real-time updates"""
    await task_controller.websocket_endpoint(websocket, task_id)

@router.post("/multimodal_generate")
async def multimodal_generate(
    task_id: str = Form(..., description="Task ID"),
    files: list[UploadFile] = File(..., description="List of image files to upload"),
    user_input: str = Form(..., description="User Input"),
    programming_language: str = Form(..., description="programming language of the user input"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None,
    user_id: str = Form(..., description="User ID of the uploader"),
    model: str = Form(..., description="Model to use for the task"),
    speech: str = Form(..., description="Speech of the user input"),
    language: str = Form(..., description="Language of the user input")
):
    """Handle multimodal task generation request"""
    return await task_controller.multimodal_generate(
        task_id, files, user_id, user_input, programming_language,
        model, speech, language, authorization, response
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
    programming_language: str = Form(..., description="programming language of the user input"),
    round: int = Form(..., description="Round number"),
    speech: str = Form(..., description="Speech of the user input"),
    language: str = Form(..., description="Language of the user input")
):
    """Handle multimodal task debug request"""
    return await task_controller.multimodal_debug(
        task_id, files, user_id, user_input, programming_language,
        model, round, speech, language, authorization, response
    )

@router.post("/generate")
async def generate(
    task_id: str = Form(..., description="Task ID"),
    files: list[UploadFile] = File(..., description="List of image files to upload"),
    title: str = Form(None, description="Optional title for the batch of images"),
    description: str = Form(None, description="Optional description for the batch of images"),
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None,
    user_id: str = Form(..., description="User ID of the uploader"),
    user_input: str = Form(..., description="User Input"),
    screenshot_count: int = Form(..., description="Number of screenshots"),
    programming_language: str = Form(..., description="programming language of the user input"),
    model: str = Form(..., description="Model to use for the task"),
    speech: str = Form(..., description="Speech of the user input"),
    language: str = Form(..., description="Language of the user input")
):
    """Handle task generation request"""
    return await task_controller.generate(
        task_id, files, user_id, user_input, programming_language,
        model, speech, language, screenshot_count, authorization, response
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
    programming_language: str = Form(..., description="programming language of the user input"),
    round: int = Form(..., description="Round number"),
    speech: str = Form(..., description="Speech of the user input"),
    language: str = Form(..., description="Language of the user input")
):
    """Handle task debug request"""
    return await task_controller.debug(
        task_id, files, user_id, user_input, programming_language,
        model, round, speech, language, authorization, response
    )
