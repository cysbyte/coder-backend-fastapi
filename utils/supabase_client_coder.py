from supabase import create_client, Client
import os
import asyncio
from dotenv import load_dotenv
from typing import Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Separate env vars for the coder database
CODER_SUPABASE_URL: str | None = 'https://rasucxryuccifqifgbkj.supabase.co'
CODER_SUPABASE_KEY: str | None = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJhc3VjeHJ5dWNjaWZxaWZnYmtqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIxNDYzNDYsImV4cCI6MjA1NzcyMjM0Nn0.A1DIf2BF1ZCNNvIacZu5OYhFUtY9zzWwZ6gce-c4A_0'

if not CODER_SUPABASE_URL or not CODER_SUPABASE_KEY:
    logger.warning("Coder Supabase credentials are not fully set. Set CODER_SUPABASE_URL and CODER_SUPABASE_KEY.")

# Create Supabase client for coder DB
coder_supabase: Client = create_client(CODER_SUPABASE_URL or "", CODER_SUPABASE_KEY or "")

# Configure timeouts for the underlying HTTP client if available
if hasattr(coder_supabase, 'rest') and hasattr(coder_supabase.rest, 'client'):
    coder_supabase.rest.client.timeout = 30.0


class CoderSupabaseRetryClient:
    """Wrapper for coder Supabase client with retry logic"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.client = coder_supabase
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def execute_with_retry(self, operation, *args, **kwargs):
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                retryable_errors = [
                    'timeout', 'connection', 'network', 'temporary',
                    'service unavailable', 'gateway timeout', 'bad gateway',
                    'too many requests', 'rate limit'
                ]
                is_retryable = any(error in error_msg for error in retryable_errors)
                if not is_retryable or attempt == self.max_retries - 1:
                    logger.error(f"Coder Supabase operation failed after {attempt + 1} attempts: {str(e)}")
                    raise e
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Coder Supabase failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)
        raise last_exception


# Public helper bound to coder DB
coder_retry_client = CoderSupabaseRetryClient()

async def select_with_retry(table: str, **kwargs) -> Any:
    """Select data with retry logic"""
    query = coder_supabase.table(table).select('*')
    
    # Apply filters
    for key, value in kwargs.items():
        query = query.eq(key, value)
    
    return await coder_retry_client.execute_with_retry(
        lambda: query.execute()
    )

async def coder_select_with_retry(table: str, select: str = '*', **filters) -> Any:
    query = coder_supabase.table(table).select(select)
    for key, value in filters.items():
        query = query.eq(key, value)
    return await coder_retry_client.execute_with_retry(lambda: query.execute())


