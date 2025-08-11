from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client
import os
import time
import logging
import builtins

# Load environment variables
load_dotenv()

# Disable prints in production or when explicitly requested
_env = os.environ.get("ENV") or os.environ.get("PYTHON_ENV") or os.environ.get("APP_ENV")
_disable_prints_flag = str(os.environ.get("DISABLE_PRINTS", "")).lower() in ("1", "true", "yes")
_is_production = (_env or "").lower() in ("production", "prod")
if _disable_prints_flag or _is_production:
    builtins.print = lambda *args, **kwargs: None

# Configure logging (default to INFO in production, DEBUG otherwise unless LOG_LEVEL is set)
_default_level = "INFO" if (_disable_prints_flag or _is_production) else "DEBUG"
_log_level = os.environ.get("LOG_LEVEL", _default_level).upper()
logging.basicConfig(level=getattr(logging, _log_level, logging.INFO))
logger = logging.getLogger(__name__)

# Initialize Supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
    expose_headers=["New-Access-Token", "New-Refresh-Token"],
)

# Include routers
from routes import auth_routes, user_routes, task_routes, role_routes
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(task_routes.router)
app.include_router(role_routes.router)

@app.get("/")
def read_root():
    return {"Hello": "World!!!"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint to monitor database connectivity
    """
    try:
        start_time = time.time()
        
        # Test database connection with a simple query
        result = supabase.table('roles').select('count', count='exact').limit(1).execute()
        
        response_time = time.time() - start_time
        
        return {
            "status": "healthy",
            "database": "connected",
            "response_time_ms": round(response_time * 1000, 2),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with more comprehensive diagnostics
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check environment variables
    env_vars = {
        "SUPABASE_URL": bool(os.environ.get("SUPABASE_URL")),
        "SUPABASE_KEY": bool(os.environ.get("SUPABASE_KEY")),
    }
    
    health_status["checks"]["environment"] = {
        "status": "ok" if all(env_vars.values()) else "error",
        "details": env_vars
    }
    
    # Check database connection
    try:
        start_time = time.time()
        result = supabase.table('roles').select('count', count='exact').limit(1).execute()
        db_response_time = time.time() - start_time
        
        health_status["checks"]["database"] = {
            "status": "ok",
            "response_time_ms": round(db_response_time * 1000, 2),
            "connection": "active"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e),
            "connection": "failed"
        }
        health_status["status"] = "unhealthy"
    
    return health_status