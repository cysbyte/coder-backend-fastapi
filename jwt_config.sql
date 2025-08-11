-- Configure JWT token expiration to 1 minute for testing
-- Run this in your Supabase SQL Editor

-- Set JWT expiration to 60 seconds (1 minute)
UPDATE auth.config 
SET jwt_exp = 60 
WHERE id = 1;

-- Alternative: Set via environment variable
-- You can also set this in your Supabase project settings under Environment Variables
-- Add: JWT_EXPIRY = 60

-- Check current JWT settings
SELECT 
    jwt_exp,
    refresh_token_rotation,
    refresh_token_reuse_interval
FROM auth.config 
WHERE id = 1;

-- Note: You may need to restart your Supabase project for changes to take effect
-- Go to Settings -> General -> Restart project
