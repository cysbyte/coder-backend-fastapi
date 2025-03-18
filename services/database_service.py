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
        response = supabase.table('images').update(update_data).eq('id', record_id).execute()
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
        response = supabase.table('images').insert(image_data).execute()
        return {
            "success": True,
            "data": response.data[0]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 
    