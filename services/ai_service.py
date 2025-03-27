from openai import OpenAI
import os
import asyncio
from typing import Dict, Any
import aiohttp
from utils.ai import system_prompt
from services.database_service import get_record_by_task_id
async def process_with_openai(texts: list[str]) -> dict:
    """
    Process OCR texts using AWS service API with GPT-4
    Args:
        texts: List of OCR texts to analyze
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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": combined_text}
        ]

        # Prepare the request payload with conversation format
        payload = {
            "messages": conversation,
            "model": "gpt-4o-mini"
        }

        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            # Add /chat endpoint to the URL
            async with session.post(f"{ai_service_url}/chat", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "analysis": result.get("response", ""),
                        "service": "openai_gpt4",
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
    
async def debug_with_openai(texts: list[str], message: str, task_id: str) -> dict:
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
        existing_conversation = record.get("conversation", [])
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

        combined_text = f"{combined_text}\n\nUser Message:\n{message}"

        # If no existing conversation or empty conversation, create new one
        if not existing_conversation:
            conversation = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text}
            ]
        else:
            # Use existing conversation and append new message
            conversation = existing_conversation.copy()  # Create a copy to avoid modifying the original
            conversation.append({
                "role": "user",
                "content": message
            })

        # Prepare the request payload with conversation format
        payload = {
            "messages": conversation,
            "model": "gpt-4o-mini"
        }

        # Make POST request to AWS service
        async with aiohttp.ClientSession() as session:
            # Add /chat endpoint to the URL
            async with session.post(f"{ai_service_url}/chat", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    # Append assistant's response to conversation
                    conversation.append({
                        "role": "assistant",
                        "content": result.get("response", "")
                    })
                    return {
                        "success": True,
                        "analysis": result.get("response", ""),
                        "service": "openai_gpt4",
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