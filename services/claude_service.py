from utils.ai import system_prompt, get_user_prompt, get_claude_payload
from typing import List
import os
import aiohttp
import base64
import json
from services.database_service import get_record_by_task_id, update_record_status

async def generate_with_anthropic(texts: list[str], user_input: str, language: str, model: str, task_id: str, speech: str) -> dict:
    """
    Process OCR texts using AWS service API with GPT-4
    Args:
        texts: List of OCR texts to analyze
        user_input: User's input
        language: Programming language for code generation (default: python)
        model: Claude model to use (default: claude-3-5-sonnet-20240620)
        task_id: Task ID to fetch existing conversation
    Returns:
        dict containing success status and analysis results
    """
    try:
        # AWS service API endpoint
        ai_service_url = os.getenv('AI_SERVICE_URL')
        if not ai_service_url:
            return {
                "success": False,
                "error": "AWS service URL not found in environment variables"
            }
 
        # Prepare the prompt with all texts
        combined_text = "\n\n".join([
            f"Text {i+1}:\n{text}" for i, text in enumerate(texts)
        ])

        conversation = [
            {"role": "user", "content": get_user_prompt('generate', language, combined_text, user_input, speech)}
        ]
        payload = get_claude_payload(conversation, model)

        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            # Add /chat endpoint to the URL
            async with session.post(f"{ai_service_url}/claude-chat", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "analysis": result.get("response", ""),
                        "service": model,
                        "conversation": conversation
                    }
                else:
                    error_text = await response.text()
                    print(f"AI Service Error Response: {error_text}")  # Add logging
                    return {
                        "success": False,
                        "error": f"AI service error: {error_text}",
                        "status_code": response.status
                    }

    except Exception as e:
        print(f"Anthropic Processing Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
        
    """
    Process text and images using Claude model with multi-modal capabilities
    Args:
        text: Text input from the user
        images: List of base64 encoded images
        language: Programming language for code generation (default: python)
        model: Claude model to use (default: claude-3-5-sonnet-20240620)
    Returns:
        dict containing success status and analysis results
    """
    try:
        # AWS service API endpoint
        ai_service_url = os.getenv('AI_SERVICE_URL')
        if not ai_service_url:
            return {
                "success": False,
                "error": "AWS service URL not found in environment variables"
            }
        
        # Prepare the conversation with text and images
        content = []
        
        # Add text content first
        content.append({
            "type": "text",
            "text": get_user_prompt('generate', language, "", text)
        })
        
        # Add images to the content if provided
        if images and len(images) > 0:
            for image in images:
                try:
                    # Decode base64 to binary
                    image_data = base64.b64decode(image)
                    
                    # Check for common image signatures in the binary data
                    # JPEG starts with FF D8 FF
                    # PNG starts with 89 50 4E 47
                    # GIF starts with GIF87a or GIF89a
                    # WebP starts with RIFF....WEBP
                    
                    # Default to JPEG if we can't determine the type
                    media_type = "image/jpeg"
                    
                    # Check for PNG signature
                    if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
                        media_type = "image/png"
                    # Check for GIF signature
                    elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
                        media_type = "image/gif"
                    # Check for WebP signature
                    elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:12]:
                        media_type = "image/webp"
                    
                    # Add image to content with detected media type
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image
                        }
                    })
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    # Skip this image and continue with others
                    continue
        
        conversation = [
            {
                "role": "user",
                "content": content
            }
        ]
        
        # Prepare the request payload
        payload = get_claude_payload(conversation, model)
        
        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ai_service_url}/claude-chat", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "analysis": result.get("response", ""),
                        "service": model,
                        "conversation": conversation
                    }
                else:
                    error_text = await response.text()
                    print(f"AI Service Error Response: {error_text}")  # Add logging
                    return {
                        "success": False,
                        "error": f"AI service error: {error_text}",
                        "status_code": response.status
                    }
                    
    except Exception as e:
        print(f"Multi-modal Processing Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        } 

async def debug_with_anthropic(texts: list[str], user_input: str, language: str, model: str, task_id: str, speech: str) -> dict:
    """
    Process OCR texts using AWS service API with GPT-4
    Args:
        texts: List of OCR texts to analyze
        message: User's debug message
        task_id: Task ID to fetch existing conversation
    Returns:
        dict containing success status and analysis results
    """
    try:
        # AWS service API endpoint
        ai_service_url = os.getenv('AI_SERVICE_URL')
        if not ai_service_url:
            return {
                "success": False,
                "error": "AWS service URL not found in environment variables"
            }

        # Fetch existing record and conversation
        record_result = await get_record_by_task_id(task_id)
        if not record_result["success"]:
            return {
                "success": False,
                "error": f"Failed to fetch record: {record_result.get('error', 'Unknown error')}"
            }

        record = record_result["data"]
        # Ensure existing_conversation is a list
        existing_conversation = record.get("current_conversation", [])
        if isinstance(existing_conversation, str):
            try:
                import json
                existing_conversation = json.loads(existing_conversation)
            except:
                existing_conversation = []

        # Prepare the prompt with all texts
        combined_text = "\n\n".join([
            f"Text {i+1}:\n{text}" for i, text in enumerate(texts)
        ])

        conversation = existing_conversation.copy()
        conversation.append({
            "role": "user",
            "content": get_user_prompt('debug', language, combined_text, user_input, speech)
        })
        payload = get_claude_payload(conversation, model)

        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            # Add /chat endpoint to the URL
            async with session.post(f"{ai_service_url}/claude-chat", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "analysis": result.get("response", ""),
                        "service": model,
                        "conversation": conversation
                    }
                else:
                    error_text = await response.text()
                    print(f"AI Service Error Response: {error_text}")  # Add logging
                    return {
                        "success": False,
                        "error": f"AI service error: {error_text}",
                        "status_code": response.status
                    }

    except Exception as e:
        print(f"OpenAI Processing Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }