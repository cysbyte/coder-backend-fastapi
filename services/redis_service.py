import redis
import json
import os
from typing import Optional, Any, Dict, List
from dotenv import load_dotenv
import logging

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

class RedisService:
    """Redis service for caching operations"""
    
    def __init__(self):
        # Get Redis configuration from environment variables
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_db = int(os.getenv('REDIS_DB', 0))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        
        # Default cache TTL in seconds (5 minutes)
        self.default_ttl = int(os.getenv('REDIS_DEFAULT_TTL', 300))
        
        try:
            # Initialize Redis connection
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis connected successfully to {self.redis_host}:{self.redis_port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate a Redis key with prefix and identifier"""
        return f"{prefix}:{identifier}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.redis_client:
            return None
            
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting value from Redis for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache with optional TTL"""
        if not self.redis_client:
            return False
            
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Error setting value in Redis for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        if not self.redis_client:
            return False
            
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting value from Redis for key {key}: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error deleting pattern {pattern} from Redis: {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis_client:
            return False
            
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Error checking existence of key {key} in Redis: {str(e)}")
            return False
    
    async def get_roles_cache_key(self, user_id: str) -> str:
        """Generate cache key for user roles"""
        return self._generate_key("user_roles", user_id)
    
    async def cache_user_roles(self, user_id: str, roles: List[Dict], ttl: Optional[int] = None) -> bool:
        """Cache user roles in Redis"""
        key = await self.get_roles_cache_key(user_id)
        return await self.set(key, roles, ttl)
    
    async def get_cached_user_roles(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user roles from Redis"""
        key = await self.get_roles_cache_key(user_id)
        return await self.get(key)
    
    async def invalidate_user_roles_cache(self, user_id: str) -> bool:
        """Invalidate user roles cache"""
        key = await self.get_roles_cache_key(user_id)
        return await self.delete(key)
    
    async def invalidate_all_user_roles_cache(self) -> int:
        """Invalidate all user roles cache"""
        pattern = "user_roles:*"
        return await self.delete_pattern(pattern)

# Create a global instance
redis_service = RedisService() 