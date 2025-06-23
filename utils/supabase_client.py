from supabase import create_client, Client
import os
import asyncio
import time
from dotenv import load_dotenv
from typing import Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Create Supabase client with timeout configuration
supabase: Client = create_client(url, key)

# Configure timeouts for the underlying HTTP client
if hasattr(supabase, 'rest') and hasattr(supabase.rest, 'client'):
    # Set timeout for HTTP requests
    supabase.rest.client.timeout = 30.0  # 30 seconds timeout

class SupabaseRetryClient:
    """Wrapper for Supabase client with retry logic"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.client = supabase
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute a Supabase operation with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Execute the operation
                result = operation(*args, **kwargs)
                
                # If we get here, the operation was successful
                return result
                
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                # Check if this is a retryable error
                retryable_errors = [
                    'timeout', 'connection', 'network', 'temporary', 
                    'service unavailable', 'gateway timeout', 'bad gateway',
                    'too many requests', 'rate limit'
                ]
                
                is_retryable = any(error in error_msg for error in retryable_errors)
                
                if not is_retryable or attempt == self.max_retries - 1:
                    # Don't retry non-retryable errors or if we've exhausted retries
                    logger.error(f"Supabase operation failed after {attempt + 1} attempts: {str(e)}")
                    raise e
                
                # Calculate delay with exponential backoff
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Supabase operation failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s: {str(e)}")
                
                # Wait before retrying
                await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        raise last_exception

# Create a retry-enabled client instance
retry_client = SupabaseRetryClient()

# Helper functions for common operations
async def insert_with_retry(table: str, data: dict) -> Any:
    """Insert data with retry logic"""
    return await retry_client.execute_with_retry(
        lambda: supabase.table(table).insert(data).execute()
    )

async def select_with_retry(table: str, **kwargs) -> Any:
    """Select data with retry logic"""
    query = supabase.table(table).select('*')
    
    # Apply filters
    for key, value in kwargs.items():
        query = query.eq(key, value)
    
    return await retry_client.execute_with_retry(
        lambda: query.execute()
    )

async def update_with_retry(table: str, data: dict, **kwargs) -> Any:
    """Update data with retry logic"""
    query = supabase.table(table).update(data)
    
    # Apply filters
    for key, value in kwargs.items():
        query = query.eq(key, value)
    
    return await retry_client.execute_with_retry(
        lambda: query.execute()
    )

async def delete_with_retry(table: str, **kwargs) -> Any:
    """Delete data with retry logic"""
    query = supabase.table(table).delete()
    
    # Apply filters
    for key, value in kwargs.items():
        query = query.eq(key, value)
    
    return await retry_client.execute_with_retry(
        lambda: query.execute()
    ) 