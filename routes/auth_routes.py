from fastapi import APIRouter, Response
from typing import Optional
from pydantic import BaseModel
from controllers.auth_controller import AuthController

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# Request models
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

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TestTokenRequest(BaseModel):
    email: str
    password: str

# Initialize controller
auth_controller = AuthController()

@router.post("/signup")
def signup(request: SignUpRequest):
    """User signup endpoint"""
    return auth_controller.signup(request)

@router.post("/signin")
async def login(request: SignInRequest):
    """User signin endpoint"""
    return await auth_controller.signin(request)

@router.post("/signout")
def logout():
    """User signout endpoint"""
    return auth_controller.signout()

@router.get("/user")
def get_user():
    """Get current authenticated user"""
    return auth_controller.get_user()

@router.post("/send-code")
async def send_validation_code(request: ValidationCodeRequest):
    """Send validation code to user's email"""
    return await auth_controller.send_validation_code(request)

@router.post("/test-login-short-token")
async def test_login_short_token(request: TestTokenRequest):
    """Test endpoint that creates a session with very short token expiration"""
    return await auth_controller.test_login_short_token(request)

@router.post("/refresh-token")
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token without requiring full authentication"""
    return await auth_controller.refresh_token(request)

@router.get("/token-info")
async def get_token_info():
    """Get information about current token expiration settings (for debugging)"""
    return await auth_controller.get_token_info()

@router.get("/test-headers")
async def test_headers(response: Response):
    """Test endpoint to verify custom headers are working"""
    return await auth_controller.test_headers(response)

@router.post("/verify-code")
async def verify_validation_code(request: VerifyCodeRequest):
    """Verify the validation code sent to user's email"""
    return await auth_controller.verify_validation_code(request)
