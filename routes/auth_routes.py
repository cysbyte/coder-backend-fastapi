from fastapi import APIRouter, HTTPException, Response, Header
from typing import Optional
from pydantic import BaseModel
from supabase import Client
from gotrue.errors import AuthApiError
from utils.supabase_client import supabase
from utils.auth import validate_access_token

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

class SignInRequest(BaseModel):
    email: str
    password: str

class SignUpRequest(BaseModel):
    email: str
    password: str

class ValidationCodeRequest(BaseModel):
    email: str

class VerifyCodeRequest(BaseModel):
    email: str
    code: str

@router.post("/signup")
def signup(request: SignUpRequest):
    try:
        auth_response = supabase.auth.sign_up({ "email": request.email, "password": request.password })
        return auth_response
    except AuthApiError as e:
        return {"error": e.message}

@router.post("/signin")
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

@router.post("/signout")
def logout():
    supabase.auth.signout()
    return {"message": "Signed out successfully"}

@router.get("/user")
def get_user():
    user = supabase.auth.get_user()
    return user

@router.post("/send-code")
async def send_validation_code(request: ValidationCodeRequest):
    """
    Send validation code to user's email
    """
    try:
        # Send validation code using Supabase
        response = supabase.auth.sign_in_with_otp({
            "email": request.email
        })
        
        return {
            "success": True,
            "message": "Validation code sent successfully",
            "data": response
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/verify-code")
async def verify_validation_code(request: VerifyCodeRequest):
    """
    Verify the validation code sent to user's email
    """
    try:
        # Verify the code using Supabase
        response = supabase.auth.verify_otp({
            "email": request.email,
            "token": request.code,
            "type": "email"
        })
        
        if response.user:
            # Check if user exists in users table
            user_query = supabase.table('users').select("*").eq('id', response.user.id).execute()
            
            # If user doesn't exist in the users table, create a record
            if not user_query.data:
                user_data = {
                    "id": response.user.id,
                    "email": request.email,
                }
                # Insert the user data into the 'users' table
                user_record = supabase.table('users').insert(user_data).execute()
                return {
                    "success": True,
                    "auth": response,
                    "user_record": user_record.data
                }
            
            return {
                "success": True,
                "auth": response,
                "user_record": user_query.data[0]
            }
            
        return {
            "success": False,
            "error": "Invalid validation code"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
