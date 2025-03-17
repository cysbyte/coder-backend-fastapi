from openai import OpenAI
import os
import asyncio
from typing import Dict, Any

async def process_with_openai(ocr_text: str) -> dict:
    try:
        # Truncate very long texts
        max_chars = 4000
        truncated_text = ocr_text[:max_chars] if len(ocr_text) > max_chars else ocr_text
        
        if len(ocr_text) > max_chars:
            truncated_text += "... (text truncated)"
            
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        prompt = f"""Analyze this coding problem and provide:
        1. Problem Summary: Brief description of what the problem is asking
        2. Input/Output Examples: Example test cases
        3. Key Points:
           - Time Complexity requirement (if mentioned)
           - Space Complexity requirement (if mentioned)
           - Any constraints or special conditions
        4. Suggested Approach:
           - Main algorithm or data structure to use
           - Key steps to solve the problem
        5. Common Pitfalls: What to watch out for
        6. Follow-up Questions: Any additional challenges mentioned

        Problem Text:
        {truncated_text}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert coding interview coach who helps analyze and break down coding problems. Provide clear, structured analysis with a focus on problem-solving approach and optimization."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,  # Increased token limit for more detailed analysis
            temperature=0.7
        )
        
        return {
            "success": True,
            "analysis": response.choices[0].message.content
        }
        
    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
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