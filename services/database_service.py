from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

async def update_record_status(record_id: str, update_data: dict):
    """Helper function to update record status in Supabase"""
    try:
        response = supabase.table('tasks').update(update_data).eq('id', record_id).execute()
        return {
            "success": True,
            "data": response.data[0]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 
    
async def save_image_record(image_data: dict):
    try:
        response = supabase.table('tasks').insert(image_data).execute()
        return {
            "success": True,
            "data": response.data[0]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 
    
async def get_record_by_task_id(task_id: str) -> dict:
    """
    Fetch a record by task_id from Supabase
    Args:
        task_id: The task ID to fetch
    Returns:
        dict containing the record data or error information
    """
    try:
        response = supabase.table('tasks').select('*').eq('id', task_id).execute()
        
        if response.data and len(response.data) > 0:
            return {
                "success": True,
                "data": response.data[0]
            }
        else:
            return {
                "success": False,
                "error": "Record not found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 
    
async def update_user_credits(user_id: str, credit_change: int) -> dict:
    """
    Update user's free_credit in the users table
    Args:
        user_id: The user's ID
        credit_change: Amount to change (negative for reduction)
    Returns:
        dict containing success status and updated user data
    """
    try:
        
        # First get current credits
        user_query = supabase.table('users').select('free_credit').eq('id', user_id).execute()
        
        if not user_query.data or len(user_query.data) == 0:
            return {
                "success": False,
                "error": "User not found"
            }
            
        current_credits = user_query.data[0].get('free_credit', 0)
        new_credits = max(0, current_credits + credit_change)  # Ensure credits don't go below 0
        
        # Update credits
        response = supabase.table('users').update({
            'free_credit': new_credits
        }).eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            return {
                "success": True,
                "data": response.data[0]
            }
        else:
            return {
                "success": False,
                "error": "Failed to update credits"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 
    
async def get_user_credits(user_id: str) -> dict:
    """
    Get user's free_credit from the users table
    Args:
        user_id: The user's ID
    Returns:
        dict containing success status and user's credit information
    """
    try:
        response = supabase.table('users').select('free_credit').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            return {
                "success": True,
                "data": {
                    "free_credit": response.data[0].get('free_credit', 0)
                }
            }
        else:
            return {
                "success": False,
                "error": "User not found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 
    