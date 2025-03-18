from utils.supabase_client import supabase
import uuid
import datetime

async def upload_to_storage(file_content: bytes, file_name: str, content_type: str):
    try:
        unique_filename = f"{uuid.uuid4()}{file_name}"
        
        response = supabase.storage.from_('images').upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": content_type}
        )
        
        file_url = supabase.storage.from_('images').get_public_url(unique_filename)
        
        return {
            "success": True,
            "file_name": unique_filename,
            "file_url": file_url
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

