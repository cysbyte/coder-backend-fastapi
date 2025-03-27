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
        response = supabase.table('tasks').select('*').eq('task_id', task_id).execute()
        
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
    