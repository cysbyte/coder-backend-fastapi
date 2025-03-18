from typing import Union
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv
from supabase import create_client, Client
from gotrue.errors import AuthApiError
import asyncio

import os
import uuid
import io
import datetime
from google.cloud import vision
import io as python_io
from openai import OpenAI
from services.ocr_service import ocr_parse, ocr_parse_space, ocr_parse_with_fallback, ocr_parse_mock
from services.ai_service import process_with_openai, process_with_openai_mock
from services.storage_service import upload_to_storage
from utils.supabase_client import supabase
from services.websocket_service import manager
from services.task_processor import process_image_task

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 

)

# Add this class for request validation
class SignInRequest(BaseModel):
    email: str
    password: str

class SignUpRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.post("/auth/signup")
def signup(request: SignUpRequest):
    try:
        auth_response = supabase.auth.sign_up({ "email": request.email, "password": request.password })
        return auth_response
    except AuthApiError as e:
        return {"error": e.message}
    
@app.post("/auth/signin")
async def login(request: SignInRequest):
    try:
        user = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if user.user:
            # Check if user exists in users table
            user_query = supabase.table('users').select("*").eq('user_id', user.user.id).execute()
            
            # If user doesn't exist in the users table, create a record
            if not user_query.data:
                user_data = {
                    "user_id": user.user.id,
                    "email": request.email,
                }
                # Insert the user data into the 'users' table
                user_record = supabase.table('users').insert(user_data).execute()
                return {
                    "auth": user,
                    "user_record": user_record.data
                }
            
            return {
                "auth": user,
                "user_record": user_query.data[0]
            }
            
        return user
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/auth/signout")
def logout():
    supabase.auth.signout()
    return {"message": "Signed out successfully"}

@app.get("/auth/user")
def get_user():
    user = supabase.auth.get_user()
    return user

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    try:
        await manager.connect(websocket, task_id)
        # await websocket.accept()
        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            print(data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, task_id)

@app.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    title: str = Form(None),
    description: str = Form(None)
):
    try:
        content = await file.read()
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Create async task
        asyncio.create_task(process_image_task(task_id, content))
        
        # Return task ID immediately
        return {
            "success": True,
            "task_id": task_id,
            "message": "Processing started"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }