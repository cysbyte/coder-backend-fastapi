import asyncio
from services.ocr_service import ocr_parse
from services.ai_service import process_with_openai, debug_with_openai
from services.websocket_service import manager
from services.storage_service import upload_to_storage
from services.database_service import update_record_status, save_image_record
import uuid
from datetime import datetime
import os
import aiohttp

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

        # AI Analysis for all texts at once
        await manager.send_message(task_id, {
            "status": "ai processing",
            "step": "ai",
            "message": "Performing AI analysis for all images",
            "total_images": len(images)
        })
        
        ai_result = await process_with_openai(ocr_result["texts"])
        
        if not ai_result["success"]:
            await update_record_status(record["id"], {
                "status": "ai_error",
                "ai_error": ai_result.get("error", "AI analysis failed")
            })
            
            await manager.send_message(task_id, {
                "status": "ai error",
                "step": "ai",
                "message": f"AI analysis failed: {ai_result.get('error', 'AI analysis failed')}"
            })
            return

        # Configure and store conversation
        conversation = ai_result["conversation"]
        conversation.append({
            "role": "assistant",
            "content": ai_result["analysis"]
        })
        # Update record with conversation
        await update_record_status(record["id"], {
            "ai_analysis": ai_result["analysis"],
            "ai_service": "openai_gpt4",
            "conversation": conversation
        })

        # Extract problem and solution from AI analysis
        analysis_text = ai_result["analysis"]
        problem_start = analysis_text.find("[[[")
        problem_end = analysis_text.find("]]]")
        
        if problem_start != -1 and problem_end != -1:
            # Extract problem (content between [[[ and ]]])
            problem = analysis_text[problem_start + 3:problem_end].strip()
            # Extract solution (everything after ]]])
            solution = analysis_text[problem_end + 3:].strip()
        else:
            problem = ""
            solution = analysis_text.strip()  # If no markers found, use entire text as solution


        # Send final completion message with problem and solution
        await manager.send_message(task_id, {
            "status": "completed",
            "message": "Successfully extracted problem and solution",
            "data": {
                "question": problem,
                "solution": solution
            }
        })

    except Exception as e:
        await manager.send_message(task_id, {
            "status": "error",
            "message": str(e)
        })


async def process_debug_task(
    task_id: str,
    images: list[dict]  ,  # Dict containing image_content and filename
    debug_message: str,
):
    """
    Process a single image with OCR and combine with message for AI analysis
    Args:
        task_id: Unique task identifier
        image: Dict containing image content and filename
        message: Additional message to combine with OCR text
        user_id: User ID of the requester
    """
    try:
        # OCR Processing
        ocr_result = await ocr_parse(images)
        
        if not ocr_result["success"]:
            return {
                "success": False,
                "error": ocr_result.get("error", "OCR processing failed")
            }

        # Combine OCR text with message
        combined_text = f"{ocr_result['texts'][0]}\n\nUser Message:\n{debug_message}"

        # Call AI service using debug_with_openai
        ai_result = await debug_with_openai([combined_text], debug_message, task_id)
        
        if not ai_result["success"]:
            return {
                "success": False,
                "error": ai_result.get("error", "AI analysis failed")
            }

        # Update record with new conversation
        await update_record_status(task_id, {
            "ai_analysis": ai_result["analysis"],
            "ai_service": "openai_gpt4",
            "conversation": ai_result["conversation"]
        })

        analysis_text = ai_result["analysis"]
        problem_start = analysis_text.find("[[[")
        problem_end = analysis_text.find("]]]")
        
        if problem_start != -1 and problem_end != -1:
            # Extract problem (content between [[[ and ]]])
            problem = analysis_text[problem_start + 3:problem_end].strip()
            # Extract solution (everything after ]]])
            solution = analysis_text[problem_end + 3:].strip()
        else:
            problem = ""
            solution = analysis_text.strip()  # If no markers found, use entire text as solution


        # Send final completion message with problem and solution
        await manager.send_message(task_id, {
            "status": "completed",
            "message": "Successfully extracted problem and solution",
            "data": {
                "question": problem,
                "solution": solution
            }
        })

        return {
            "success": True,
            "analysis": ai_result["analysis"],
            "ocr_text": ocr_result["texts"][0]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

