# Redis Caching Implementation

This document describes the Redis caching implementation for the role management endpoints.

## Overview

Redis caching has been implemented to improve performance for the `get_roles_by_user` endpoint by reducing database queries for frequently accessed user roles.

## Configuration

### Environment Variables

Add the following Redis configuration to your `.env` file:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_DEFAULT_TTL=300
```

### Dependencies

The Redis client library has been added to `requirements.txt`:
```
redis==5.2.1
```

## Implementation Details

### Cache Strategy

1. **Cache Key Format**: `user_roles:{user_id}`
2. **Default TTL**: 5 minutes (300 seconds)
3. **Cache Invalidation**: Automatic on role creation/deletion

### Endpoints with Caching

#### GET `/role/get/{user_id}`
- **Cache Behavior**: 
  - First checks Redis cache for user roles
  - If cache hit: Returns cached data with `"cached": true`
  - If cache miss: Queries database, caches result, returns with `"cached": false`
- **Response Format**:
  ```json
  {
    "success": true,
    "data": [...],
    "token_refreshed": false,
    "cached": true/false
  }
  ```

#### POST `/role/add`
- **Cache Behavior**: Automatically invalidates user's role cache after successful role creation
- **Logging**: Logs cache invalidation for monitoring

#### DELETE `/role/{role_id}`
- **Cache Behavior**: Automatically invalidates the affected user's role cache after successful deletion
- **Logging**: Logs cache invalidation for monitoring

### Administrative Endpoints

#### DELETE `/role/cache/{user_id}`
- **Purpose**: Manually invalidate cache for a specific user
- **Use Case**: Administrative cache management
- **Response**:
  ```json
  {
    "success": true,
    "message": "Cache invalidated for user {user_id}",
    "token_refreshed": false
  }
  ```

#### DELETE `/role/cache/all`
- **Purpose**: Manually invalidate all user role caches
- **Use Case**: Bulk cache management
- **Response**:
  ```json
  {
    "success": true,
    "message": "Invalidated {count} cached entries",
    "deleted_count": 5,
    "token_refreshed": false
  }
  ```

## Error Handling

### Redis Connection Failures
- If Redis is unavailable, the application gracefully falls back to database queries
- No errors are thrown to the client when Redis is down
- All Redis operations are wrapped in try-catch blocks

### Cache Operation Failures
- Failed cache operations are logged but don't affect the main functionality
- Database queries remain the primary data source

## Monitoring

### Logging
The implementation includes comprehensive logging:
- Cache hits and misses
- Cache invalidation events
- Redis connection status
- Cache operation failures

### Example Log Messages
```
INFO: Retrieved 3 roles from cache for user user123
INFO: Cache miss for user user123, querying database
INFO: Cached 3 roles for user user123
INFO: Invalidated roles cache for user user123 after adding new role
WARNING: Failed to cache roles for user user123
```

## Performance Benefits

1. **Reduced Database Load**: Frequently accessed user roles are served from cache
2. **Faster Response Times**: Cache hits provide sub-millisecond response times
3. **Scalability**: Redis can handle high concurrent access patterns
4. **Automatic Invalidation**: Ensures data consistency without manual intervention

## Best Practices

1. **TTL Management**: Default 5-minute TTL balances freshness with performance
2. **Graceful Degradation**: Application works normally even if Redis is unavailable
3. **Automatic Invalidation**: Cache is automatically cleared when data changes
4. **Comprehensive Logging**: All cache operations are logged for monitoring

## Setup Instructions

1. Install Redis server on your system
2. Add Redis configuration to your `.env` file
3. Install the Redis Python client: `pip install redis==5.2.1`
4. Restart your FastAPI application

## Testing

To test the caching functionality:

1. Make a request to `GET /role/get/{user_id}` - should return `"cached": false`
2. Make the same request again - should return `"cached": true`
3. Add or delete a role - cache should be invalidated
4. Make the request again - should return `"cached": false` (cache miss) 