import asyncio
from services.ocr_service import ocr_parse_mock
from services.ai_service import process_with_openai_mock
from services.websocket_service import manager
from services.storage_service import upload_to_storage
from services.database_service import update_record_status, save_image_record
import uuid
from datetime import datetime


async def process_image_task(task_id: str, image_content: bytes):
    try:
        # First, upload image to Supabase storage
        storage_result = await upload_to_storage(
            file_content=image_content,
            file_name=f"{task_id}.png",  # You might want to get the actual file extension
            content_type="image/png"     # You might want to get the actual content type
        )

        if not storage_result["success"]:
            await manager.send_message(task_id, {
                "status": "storage error",
                "message": f"Failed to upload image: {storage_result.get('error', 'Unknown error')}"
            })
            return

        # Create initial record in Supabase
        initial_record = {
            "task_id": task_id,
            "file_url": storage_result["file_url"],
        }

        save_result = await save_image_record(initial_record)
        
        if not save_result["success"]:
            await manager.send_message(task_id, {
                "status": "save error",
                "message": f"Failed to create record: {save_result.get('error', 'Unknown error')}"
            })
            return

        # Send start message
        await manager.send_message(task_id, {
            "status": "started",
            "message": "Starting image processing"
        })

        # OCR Processing
        await manager.send_message(task_id, {
            "status": "ocr processing",
            "step": "ocr",
            "message": "Performing OCR analysis"
        })
        
        ocr_result = await ocr_parse_mock(image_content)
        
        if not ocr_result["success"]:
            # Update record with OCR error
            await update_record_status(save_result["data"]["id"], {
                "status": "ocr_error",
                "ocr_error": ocr_result.get("error", "OCR processing failed")
            })
            
            await manager.send_message(task_id, {
                "status": "ocr error",
                "step": "ocr",
                "message": ocr_result.get("error", "OCR processing failed")
            })
            return
        
        # Update record with OCR results
        await update_record_status(save_result["data"]["id"], {
            "ocr_text": ocr_result["text"],

        })

        await manager.send_message(task_id, {
            "status": "ocr completed",
            "step": "ocr",
            "message": "OCR analysis completed",
            "data": {
                "ocr_text": ocr_result["text"]
            }
        })

        # AI Analysis
        await manager.send_message(task_id, {
            "status": "ai processing",
            "step": "ai",
            "message": "Performing AI analysis"
        })
        
        ai_result = await process_with_openai_mock(ocr_result["text"])
        
        if not ai_result["success"]:
            # Update record with AI error
            await update_record_status(save_result["data"]["id"], {
                "status": "ai_error",
                "ai_error": ai_result.get("error", "AI analysis failed")
            })
            
            await manager.send_message(task_id, {
                "status": "ai error",
                "step": "ai",
                "message": ai_result.get("error", "AI analysis failed")
            })
            return

        # Update record with AI results
        await update_record_status(save_result["data"]["id"], {
            "ai_analysis": ai_result["analysis"],
        })

        # Send completion message
        await manager.send_message(task_id, {
            "status": "completed",
            "step": "ai",
            "message": "AI analysis completed",
            "data": {
                "ocr_text": ocr_result["text"],
                "ai_analysis": ai_result["analysis"]
            }
        })

    except Exception as e:
        # Update record with general error
        if 'save_result' in locals():
            await update_record_status(save_result["data"]["id"], {
                "status": "error",
                "error_message": str(e)
            })
        
        await manager.send_message(task_id, {
            "status": "error",
            "message": str(e)
        })

