from openai import OpenAI
import os
import asyncio
from typing import Dict, Any, List
import aiohttp
import base64
from utils.ai import get_system_prompt, get_user_prompt, get_gpt_payload, get_claude_payload
from services.database_service import get_record_by_task_id, update_record_status
import json
from services.websocket_service import manager
async def generate_with_openai(texts: list[str], user_input: str, programming_language: str, model: str, task_id: str, speech: str, language: str = 'en') -> dict:
    """
    Process OCR texts using AWS service API with GPT-4
    Args:
        texts: List of OCR texts to analyze
    Returns:
        dict containing success status and analysis results
    """
    try:
        await manager.send_message(task_id, {
            "status": "ai started",
            "step": "ai",
            "message": "AI analysis started for all user input"
        })
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
            {"role": "system", "content": get_system_prompt(language)},
            {"role": "user", "content": get_user_prompt('generate', programming_language, combined_text, user_input, speech)}
        ]
        payload = get_gpt_payload(conversation, model)

        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            # Add /chat endpoint to the URL
            async with session.post(f"{ai_service_url}/gpt-chat", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    await manager.send_message(task_id, {
                        "status": "ai completed",
                        "step": "ai",
                        "message": "AI analysis completed for all user input"
                    })
                    conversation.append({
                        "role": "assistant",
                        "content": result.get("response", "")
                    })
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
        
    
async def debug_with_openai(texts: list[str], user_input: str, programming_language: str, model: str, language: str, task_id: str, speech: str) -> dict:
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
        await manager.send_message(task_id, {
            "status": "ai started",
            "step": "ai",
            "message": "AI analysis started for all user input"
        })
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
            "content": get_user_prompt('debug', programming_language, combined_text, user_input, speech)
        })
        payload = get_gpt_payload(conversation, model)

        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            # Add /chat endpoint to the URL
            async with session.post(f"{ai_service_url}/gpt-chat", json=payload) as response:
                if response.status == 200:
                    await manager.send_message(task_id, {
                        "status": "ai completed",
                        "step": "ai",
                        "message": "AI analysis completed for all user input"
                    })
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
    

async def generate_with_openai_multimodal(ocr_text: str, text: str, images: List[str], programming_language: str = "python", model: str = "o4-mini", language: str = "en", task_id: str = None, speech: str = None) -> dict:
    """
    Process text and images using GPT-4o-mini model with multi-modal capabilities
    Args:
        text: Text input from the user
        images: List of base64 encoded images
        programming_language: Programming Language for code generation (default: python)
        language: Language to use (default: en)
    Returns:
        dict containing success status and analysis results
    """
    try:
        await manager.send_message(task_id, {
            "status": "ai started",
            "step": "ai",
            "message": "AI analysis started for all user input"
        })
        # AWS service API endpoint
        ai_service_url = os.getenv('AI_SERVICE_URL')
        if not ai_service_url:
            return {
                "success": False,
                "error": "AWS service URL not found in environment variables"
            }
        
        # Prepare the conversation with text and images
        conversation = [
            {"role": "system", "content": get_system_prompt(language)},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": get_user_prompt('generate', programming_language, ocr_text, text, speech)}
                ]
            }
        ]
        
        # Add images to the conversation if provided
        if images and len(images) > 0:
            for image in images:
                conversation[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image}"
                    }
                })
        
        # Prepare the request payload
        payload = get_gpt_payload(conversation, model)
        
        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ai_service_url}/gpt-chat", json=payload) as response:
                if response.status == 200:
                    await manager.send_message(task_id, {
                        "status": "ai completed",
                        "step": "ai",
                        "message": "AI analysis completed for all user input"
                    })
                    result = await response.json()
                    conversation.append({
                        "role": "assistant",
                        "content": result.get("response", "")
                    })
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
    
async def debug_with_openai_multimodal(texts: list[str], user_input: str, programming_language: str, model: str, task_id: str, speech: str) -> dict:
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
            "content": get_user_prompt('debug', programming_language, combined_text, user_input, speech)
        })
        payload = get_gpt_payload(conversation, model)

        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            # Add /chat endpoint to the URL
            endpoint = "/gpt-chat" if "gpt" in model else "/claude-chat"
            async with session.post(f"{ai_service_url}{endpoint}", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    # Append assistant's response to conversation
                    conversation.append({
                        "role": "assistant",
                        "content": result.get("response", "")
                    })
                    update_record_status(task_id, {
                        "current_conversation": json.dumps(conversation)
                    })
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
    
async def process_with_openai_mock(ocr_text: str) -> Dict[str, Any]:
    """
    Mock AI analysis function that simulates processing time and returns predefined analysis
    """
    try:
        # Simulate processing time
        await asyncio.sleep(5)
        
        mock_analysis = f"""
Analysis of the coding problem:

1. Problem Summary:
   - This is a Two Sum problem from LeetCode
   - Need to find two numbers in an array that add up to a target value
   - Return the indices of these numbers

2. Input/Output Examples:
   - Input: nums = [2,7,11,15], target = 9
   - Output: [0,1] (because 2 + 7 = 9)

3. Key Points:
   - Time Complexity requirement: O(n)
   - Space Complexity requirement: O(n)
   - Each input has exactly one solution
   - Cannot use the same element twice

4. Suggested Approach:
   - Use a hash map to store visited numbers
   - For each number, check if (target - current_number) exists in hash map
   - If found, return current index and stored index
   - If not found, store current number and index in hash map

5. Common Pitfalls:
   - Using nested loops (O(n²) solution)
   - Not handling edge cases
   - Using the same element twice

6. Follow-up Questions:
   - Can you solve it with O(1) space complexity?
   - What if there are multiple valid solutions?
   - How would you handle negative numbers?

Python Solution Template:
```python
def twoSum(nums: List[int], target: int) -> List[int]:
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
```
        """
        
        return {
            "success": True,
            "analysis": mock_analysis.strip(),
            "service": "mock_ai"
        }
            
    except Exception as e:
        print(f"Mock AI Analysis Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Add different mock responses for different types of problems
MOCK_AI_RESPONSES = {
    "two_sum": """[Two Sum Analysis]...""",
    "linked_list": """[Linked List Analysis]...""",
    "system_design": """[System Design Analysis]...""",
    "error": None
}

async def process_with_openai_mock_with_type(ocr_text: str, mock_type: str = "two_sum") -> Dict[str, Any]:
    """
    Mock AI analysis with different response types
    """
    try:
        await asyncio.sleep(5)
        
        if mock_type == "error":
            return {
                "success": False,
                "error": "Simulated AI analysis error"
            }
            
        mock_analysis = MOCK_AI_RESPONSES.get(mock_type, MOCK_AI_RESPONSES["two_sum"])
        
        return {
            "success": True,
            "analysis": mock_analysis.strip(),
            "service": "mock_ai",
            "mock_type": mock_type
        }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
