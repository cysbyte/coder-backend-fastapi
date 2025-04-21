import asyncio
from typing import Optional
from services.ocr_service import ocr_parse
from services.gpt_service import generate_with_openai, debug_with_openai, generate_with_openai_multimodal
from services.claude_service import generate_with_anthropic, generate_with_anthropic_multimodal
from services.websocket_service import manager
from services.storage_service import upload_to_storage
from services.database_service import update_record_status, save_image_record, update_user_credits
import uuid
from datetime import datetime
import os
import aiohttp
import base64

async def process_generate(
    task_id: str,
    images: list[dict],  # List of dicts containing image_content and filename
    user_id: str,
    user_input: str,
    language: str,
    model: str
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
            "id": task_id,
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
        
        if 'gpt' in model:
            ai_result = await generate_with_openai(ocr_result["texts"], user_input, language, model)
        elif 'claude' in model:
            ai_result = await generate_with_anthropic(ocr_result["texts"], user_input, language, model)
        
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
            solution = analysis_text.strip().replace('---', '')  # If no markers found, use entire text as solution


        # Send final completion message with problem and solution
        await manager.send_message(task_id, {
            "status": "completed",
            "message": "Successfully extracted problem and solution",
            "data": {
                "question": problem,
                "solution": solution
            }
        })

        # Update user credits
        credits_result = await update_user_credits(user_id, -1)
        if not credits_result["success"]:
            await manager.send_message(task_id, {
                "status": "credits error",
                "message": credits_result.get("error", "Failed to update user credits")
            })
        if credits_result["new_credits"] <= 0:
            await manager.send_message(task_id, {
                "status": "no credits",
                "message": "Insufficient credits. Please purchase more credits to continue."
            })

    except Exception as e:
        await manager.send_message(task_id, {
            "status": "error",
            "message": str(e)
        })


async def process_debug(
    task_id: str,
    user_id: str,
    user_input: str,
    images: Optional[list[dict]] = None  # Make images optional
):
    """
    Process a single image with OCR and combine with message for AI analysis
    Args:
        task_id: Unique task identifier
        user_id: User ID of the requester
        user_input: Additional message to combine with OCR text
        images: Optional list of dicts containing image content and filename
    """
    try:
        # Initialize OCR result
        ocr_result = {"success": True, "texts": []}
        
        # Only perform OCR if images are provided
        if images:
            ocr_result = await ocr_parse(images)
            
            if not ocr_result["success"]:
                return {
                    "success": False,
                    "error": ocr_result.get("error", "OCR processing failed")
                }

        # Call AI service using debug_with_openai
        ai_result = await debug_with_openai(ocr_result["texts"], user_input, task_id)
        
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
            solution = analysis_text.strip().replace('---', '')  # If no markers found, use entire text as solution

        # Send final completion message with problem and solution
        await manager.send_message(task_id, {
            "status": "completed",
            "message": "Successfully extracted problem and solution",
            "data": {
                "question": problem,
                "solution": solution
            }
        })

        # Update user credits
        await update_user_credits(user_id, -1)

        return {
            "success": True,
            "analysis": ai_result["analysis"],
            "ocr_text": ocr_result["texts"][0] if ocr_result["texts"] else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def process_generate_multimodal(
    task_id: str,
    images: list[dict],  # List of dicts containing image_content and filename
    user_id: str,
    user_input: str,
    language: str,
    model: str
):
    """
    Process images with OCR and then use multimodal AI analysis
    Args:
        task_id: Unique task identifier
        images: List of dicts containing image content and filename
        user_id: User ID of the requester
        user_input: User's input text
        language: Programming language for code generation
    """
    try:
        # Send start message
        await manager.send_message(task_id, {
            "status": "started",
            "message": f"Starting multimodal processing for {len(images)} images"
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
            "id": task_id,
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

        # Multimodal AI Analysis
        await manager.send_message(task_id, {
            "status": "ai processing",
            "step": "ai",
            "message": "Performing multimodal AI analysis",
            "total_images": len(images)
        })
        
        # Convert images to base64 for multimodal processing
        base64_images = []
        for image in images:
            base64_image = base64.b64encode(image["content"]).decode('utf-8')
            base64_images.append(base64_image)
        
        if 'gpt' in model:
            # Call multimodal AI service
            ai_result = await generate_with_openai_multimodal(
                text=user_input,
                images=base64_images,
                language=language,
                model=model
            )
        elif 'claude' in model:
            ai_result = await generate_with_anthropic_multimodal(
                text=user_input,
                images=base64_images,
                language=language,
                model=model
            )
        
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

        # Update record with AI analysis results
        await update_record_status(record["id"], {
            "ai_analysis": ai_result["analysis"],
            "ai_service": "gpt-o4-mini",
            "conversation": ai_result["conversation"]
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
            solution = analysis_text.strip().replace('---', '')  # If no markers found, use entire text as solution


        # Send final completion message with problem and solution
        await manager.send_message(task_id, {
            "status": "completed",
            "message": "Successfully extracted problem and solution",
            "data": {
                "question": problem,
                "solution": solution
            }
        })

        # Update user credits
        credits_result = await update_user_credits(user_id, -1)
        if not credits_result["success"]:
            await manager.send_message(task_id, {
                "status": "credits error",
                "message": credits_result.get("error", "Failed to update user credits")
            })
        if credits_result["new_credits"] <= 0:
            await manager.send_message(task_id, {
                "status": "no credits",
                "message": "Insufficient credits. Please purchase more credits to continue."
            })

    except Exception as e:
        await manager.send_message(task_id, {
            "status": "error",
            "message": str(e)
        })

