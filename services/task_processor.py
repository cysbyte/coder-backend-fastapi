import asyncio
from services.ocr_service import ocr_parse_mock
from services.ai_service import process_with_openai_mock
from services.websocket_service import manager
import uuid

async def process_image_task(task_id: str, image_content: bytes):
    try:
        # Send start message
        await manager.send_message(task_id, {
            "status": "started",
            "message": "Starting image processing"
        })

        # OCR Processing
        await manager.send_message(task_id, {
            "status": "processing",
            "step": "ocr",
            "message": "Performing OCR analysis"
        })
        
        ocr_result = await ocr_parse_mock(image_content)
        
        if not ocr_result["success"]:
            await manager.send_message(task_id, {
                "status": "error",
                "step": "ocr",
                "message": ocr_result.get("error", "OCR processing failed")
            })
            return

        # AI Analysis
        await manager.send_message(task_id, {
            "status": "processing",
            "step": "ai",
            "message": "Performing AI analysis"
        })
        
        ai_result = await process_with_openai_mock(ocr_result["text"])
        
        if not ai_result["success"]:
            await manager.send_message(task_id, {
                "status": "error",
                "step": "ai",
                "message": ai_result.get("error", "AI analysis failed")
            })
            return

        # Send completion message
        await manager.send_message(task_id, {
            "status": "completed",
            "data": {
                "ocr_text": ocr_result["text"],
                "ai_analysis": ai_result["analysis"]
            }
        })

    except Exception as e:
        await manager.send_message(task_id, {
            "status": "error",
            "message": str(e)
        }) 