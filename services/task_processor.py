import asyncio
from services.ocr_service import ocr_parse
from services.ai_service import process_with_openai_mock
from services.websocket_service import manager
from services.storage_service import upload_to_storage
from services.database_service import update_record_status, save_image_record
import uuid
from datetime import datetime


async def process_image_task(
    task_id: str,
    images: list[dict],  # List of dicts containing image_content and filename
    user_id: str
):
    try:
        # Send start message
        await manager.send_message(task_id, {
            "status": "started",
            "message": f"Starting processing for {len(images)} images"
        })

        # Upload all images to storage first
        storage_results = []
        for index, image in enumerate(images):
            await manager.send_message(task_id, {
                "status": "uploading",
                "message": f"Uploading image {index + 1} of {len(images)}",
                "current_image": index + 1,
                "total_images": len(images)
            })

            storage_result = await upload_to_storage(
                file_content=image["content"],
                file_name=image["filename"],
                content_type="image/png"    
            )

            if not storage_result["success"]:
                await manager.send_message(task_id, {
                    "status": "storage error",
                    "message": f"Failed to upload image {image['filename']}: {storage_result.get('error', 'Unknown error')}",
                    "current_image": index + 1,
                    "total_images": len(images)
                })
                continue

            storage_results.append(storage_result)

        # Create a single record with arrays of URLs and filenames
        initial_record = {
            "task_id": task_id,
            "image_urls": [result["file_url"] for result in storage_results],
            "file_names": [image["filename"] for image in images],
            "user_id": user_id,
            "file_type": "image/png",
            "total_images": len(images)
        }

        save_result = await save_image_record(initial_record)
        
        if not save_result["success"]:
            await manager.send_message(task_id, {
                "status": "save error",
                "message": f"Failed to create record: {save_result.get('error', 'Unknown error')}"
            })
            return

        record = save_result["data"]

        # OCR Processing for all images
        await manager.send_message(task_id, {
            "status": "ocr processing",
            "step": "ocr",
            "message": "Performing OCR analysis for all images",
            "total_images": len(images)
        })
        
        ocr_result = await ocr_parse(images)
        
        if not ocr_result["success"]:
            await manager.send_message(task_id, {
                "status": "ocr error",
                "step": "ocr",
                "message": ocr_result.get("error", "OCR processing failed")
            })
            return

        # Update record with OCR results
        await update_record_status(record["id"], {
            "ocr_texts": ocr_result["texts"],
            "ocr_service": "google_vision"
        })

        await manager.send_message(task_id, {
            "status": "ocr completed",
            "step": "ocr",
            "message": "OCR analysis completed for all images",
            "data": {
                "texts": ocr_result["texts"]
            }
        })

        # AI Analysis for all texts
        await manager.send_message(task_id, {
            "status": "ai processing",
            "step": "ai",
            "message": "Performing AI analysis for all images",
            "total_images": len(images)
        })
        
        results = []
        ai_analyses = []
        for index, text in enumerate(ocr_result["texts"]):
            ai_result = await process_with_openai_mock(text)
            
            if not ai_result["success"]:
                await update_record_status(record["id"], {
                    "status": "ai_error",
                    "ai_error": f"Failed for image {index + 1}: {ai_result.get('error', 'AI analysis failed')}"
                })
                
                await manager.send_message(task_id, {
                    "status": "ai error",
                    "step": "ai",
                    "message": f"AI analysis failed for image {index + 1}: {ai_result.get('error', 'AI analysis failed')}",
                    "current_image": index + 1,
                    "total_images": len(images)
                })
                continue

            # Add result to lists
            results.append({
                "filename": images[index]["filename"],
                "ocr_text": text,
                "ai_analysis": ai_result["analysis"]
            })
            ai_analyses.append(ai_result["analysis"])

            await manager.send_message(task_id, {
                "status": "image completed",
                "step": "ai",
                "message": f"Completed processing image {index + 1}",
                "data": {
                    "ocr_text": text,
                    "ai_analysis": ai_result["analysis"]
                },
                "current_image": index + 1,
                "total_images": len(images)
            })

        # Update record with AI results
        await update_record_status(record["id"], {
            "ai_analyses": ai_analyses,
            "ai_service": "mock"
        })

        # Send final completion message
        await manager.send_message(task_id, {
            "status": "completed",
            "message": f"Completed processing all {len(images)} images",
            "results": results
        })

    except Exception as e:
        await manager.send_message(task_id, {
            "status": "error",
            "message": str(e)
        })

