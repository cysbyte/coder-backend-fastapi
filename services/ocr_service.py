from google.cloud import vision
import io
import requests
import os
from typing import Optional
from dotenv import load_dotenv
import mimetypes
import base64
import asyncio

# Add these at the top of the file
MOCK_RESPONSES = {
    "leetcode": [
        """
        1431. Kids With the Greatest Number of Candies
        
        There are n kids with candies. You are given an integer array candies, where each candies[i] represents the number of candies the ith kid has, and an integer extraCandies, denoting the number of extra candies that you have.

        Return a boolean array result of length n, where result[i] is true if, after giving the ith kid all the extraCandies, they will have the greatest number of candies among all the kids, or false otherwise.

        Note that multiple kids can have the greatest number of candies.
        """,
        """
        1. Two Sum
        
        Given an array of integers nums and an integer target, return indices of the two numbers in nums such that they add up to target.
        
        You may assume that each input would have exactly one solution, and you may not use the same element twice.
        
        You can return the answer in any order.
        """,
        """
        2. Add Two Numbers
        
        You are given two non-empty linked lists representing two non-negative integers. The digits are stored in reverse order, and each of their nodes contains a single digit. Add the two numbers and return the sum as a linked list.
        
        You may assume the two numbers do not contain any leading zero, except the number 0 itself.
        """
    ],
    "system_design": [
        "Design a distributed cache system",
        "Design a real-time chat application",
        "Design a URL shortening service"
    ],
    "error": None
}

async def ocr_parse(image_content: bytes) -> str:
    try:
        # Create a client
        client = vision.ImageAnnotatorClient.from_service_account_json('ocr-service-account.json')

        # Create image object
        image = vision.Image(content=image_content)

        # Perform text detection
        response = client.text_detection(image=image)
        texts = response.text_annotations

        if texts and texts[0].description.strip():
            # Get the full text from the first annotation
            full_text = texts[0].description
            return {
                "success": True,
                "text": full_text
            }
        
        return {
            "success": False,
            "error": "No text found",
            "text": ""
        }

    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "text": ""
        }

async def ocr_parse_space(image_content: bytes, content_type: str = None, filename: str = None) -> dict:
    """
    Parse image text using OCR.space API
    Args:
        image_content: The image file content in bytes
        content_type: The MIME type of the image (e.g., 'image/jpeg')
        filename: Original filename with extension
    """
    try:
        api_key = os.getenv('OCR_SPACE_API_KEY')
        if not api_key:
            return {
                "success": False,
                "error": "OCR.space API key not found"
            }

        url = "https://api.ocr.space/parse/image"
        
        # Determine file extension
        file_ext = None
        if filename:
            file_ext = os.path.splitext(filename)[1]
        elif content_type:
            file_ext = mimetypes.guess_extension(content_type)
        
        if not file_ext:
            file_ext = '.png'  # Default to jpg if no extension found
            
        # Convert bytes to base64
        base64_image = base64.b64encode(image_content).decode()
        
        # Prepare payload
        payload = {
            'apikey': api_key,
            'language': 'eng',
            'isOverlayRequired': False,
            'detectOrientation': True,
            'OCREngine': 2,
            'scale': True,
            'base64Image': f"data:{content_type or 'image/jpeg'};base64,{base64_image}",
            'filetype': file_ext.replace('.', '')  # Remove dot from extension
        }
        
        # Make POST request
        response = requests.post(url, json=payload)
        result = response.json()
        
        # Check if the OCR was successful
        if result.get('OCRExitCode') == 1:
            parsed_text = ""
            for text_result in result.get('ParsedResults', []):
                parsed_text += text_result.get('ParsedText', '')
            
            return {
                "success": True,
                "text": parsed_text.strip(),
                "confidence": result.get('OCRConfidencePercent'),
                "raw_response": result
            }
        else:
            return {
                "success": False,
                "error": result.get('ErrorMessage', 'OCR processing failed'),
                "raw_response": result
            }
            
    except Exception as e:
        print(f"OCR.space API Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Function to try both OCR services
async def ocr_parse_with_fallback(
    image_content: bytes,
    content_type: str = None,
    filename: str = None
) -> dict:
    """
    Try Google Cloud Vision first, fall back to OCR.space if it fails
    """
    try:
        # Try Google Cloud Vision first
        google_result = await ocr_parse(image_content)
        if google_result and len(google_result.strip()) > 0:
            return {
                "success": True,
                "text": google_result,
                "service": "google_vision"
            }
        
        # If Google Vision fails or returns no text, try OCR.space
        ocr_space_result = await ocr_parse_space(
            image_content,
            content_type=content_type,
            filename=filename
        )
        if ocr_space_result["success"]:
            return {
                "success": True,
                "text": ocr_space_result["text"],
                "confidence": ocr_space_result.get("confidence"),
                "service": "ocr_space"
            }
        
        # If both services fail
        return {
            "success": False,
            "error": "Both OCR services failed to extract text",
            "google_error": "No text extracted" if google_result else "Service failed",
            "ocr_space_error": ocr_space_result.get("error", "Unknown error")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def ocr_parse_mock(images: list[dict], mock_type: str = "leetcode") -> dict:
    """
    Mock OCR function that processes multiple images and returns mock texts
    Args:
        images: List of dicts containing image content and filename
        mock_type: Type of mock response to return
    """
    try:
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Get mock texts based on type
        mock_texts = MOCK_RESPONSES.get(mock_type, MOCK_RESPONSES["leetcode"])
        
        # Simulate error if mock_type is "error"
        if mock_type == "error":
            return {
                "success": False,
                "error": "Simulated OCR error"
            }
        
        # Return empty results if mock_type is "empty"
        if mock_type == "empty":
            return {
                "success": True,
                "texts": [""] * len(images),
                "service": "mock_ocr",
                "confidence": 0
            }
        
        # Ensure we have enough mock texts
        while len(mock_texts) < len(images):
            mock_texts.extend(mock_texts)
        
        # Take only the number of texts we need
        mock_texts = mock_texts[:len(images)]
        
        return {
            "success": True,
            "texts": mock_texts,
            "service": "mock_ocr",
            "confidence": 99.9,
            "mock_type": mock_type
        }
            
    except Exception as e:
        print(f"Mock OCR Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        } 