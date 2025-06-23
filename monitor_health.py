#!/usr/bin/env python3
"""
Health monitoring script for the FastAPI application
Run this script to monitor database connectivity and identify issues
"""

import asyncio
import aiohttp
import time
import json
import logging
from datetime import datetime
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "avg_response_time": 0,
            "errors": []
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> Dict:
        """Check basic health endpoint"""
        try:
            start_time = time.time()
            async with self.session.get(f"{self.base_url}/health") as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "response_time": response_time,
                        "data": data
                    }
                else:
                    return {
                        "status": "error",
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "error",
                "response_time": 0,
                "error": str(e)
            }
    
    async def check_detailed_health(self) -> Dict:
        """Check detailed health endpoint"""
        try:
            start_time = time.time()
            async with self.session.get(f"{self.base_url}/health/detailed") as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "response_time": response_time,
                        "data": data
                    }
                else:
                    return {
                        "status": "error",
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "error",
                "response_time": 0,
                "error": str(e)
            }
    
    async def test_role_endpoint(self) -> Dict:
        """Test the role endpoint with a dummy request"""
        try:
            # This is a test request - you might need to adjust based on your auth requirements
            test_data = {
                "user_id": "test_user_123",
                "company_name": "Test Company",
                "role": "Test Role",
                "description": "Test Description"
            }
            
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/role/add",
                json=test_data,
                headers={"Authorization": "Bearer test_token,test_refresh_token"}
            ) as response:
                response_time = time.time() - start_time
                
                return {
                    "status": "success" if response.status in [200, 401, 403] else "error",
                    "response_time": response_time,
                    "status_code": response.status,
                    "data": await response.text() if response.status != 200 else "Success"
                }
        except Exception as e:
            return {
                "status": "error",
                "response_time": 0,
                "error": str(e)
            }
    
    def update_stats(self, result: Dict):
        """Update monitoring statistics"""
        self.stats["total_checks"] += 1
        
        if result["status"] == "success":
            self.stats["successful_checks"] += 1
        else:
            self.stats["failed_checks"] += 1
            self.stats["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "error": result.get("error", "Unknown error"),
                "response_time": result.get("response_time", 0)
            })
        
        # Keep only last 100 errors
        if len(self.stats["errors"]) > 100:
            self.stats["errors"] = self.stats["errors"][-100:]
        
        # Update average response time
        if result.get("response_time", 0) > 0:
            current_avg = self.stats["avg_response_time"]
            total_checks = self.stats["total_checks"]
            self.stats["avg_response_time"] = (current_avg * (total_checks - 1) + result["response_time"]) / total_checks
    
    def print_stats(self):
        """Print current statistics"""
        success_rate = (self.stats["successful_checks"] / self.stats["total_checks"] * 100) if self.stats["total_checks"] > 0 else 0
        
        print(f"\n{'='*50}")
        print(f"Health Monitor Statistics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        print(f"Total Checks: {self.stats['total_checks']}")
        print(f"Successful: {self.stats['successful_checks']}")
        print(f"Failed: {self.stats['failed_checks']}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Response Time: {self.stats['avg_response_time']:.3f}s")
        
        if self.stats["errors"]:
            print(f"\nRecent Errors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][-5:]:  # Show last 5 errors
                print(f"  {error['timestamp']}: {error['error']}")
        
        print(f"{'='*50}")

async def main():
    """Main monitoring loop"""
    # Update this URL to match your deployed application
    base_url = "http://localhost:8000"  # Change to your AWS endpoint
    
    async with HealthMonitor(base_url) as monitor:
        print(f"Starting health monitor for {base_url}")
        print("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                # Check basic health
                health_result = await monitor.check_health()
                monitor.update_stats(health_result)
                
                # Check detailed health every 5th iteration
                if monitor.stats["total_checks"] % 5 == 0:
                    detailed_result = await monitor.check_detailed_health()
                    monitor.update_stats(detailed_result)
                
                # Test role endpoint every 10th iteration
                if monitor.stats["total_checks"] % 10 == 0:
                    role_result = await monitor.test_role_endpoint()
                    monitor.update_stats(role_result)
                
                # Print stats every 10 checks
                if monitor.stats["total_checks"] % 10 == 0:
                    monitor.print_stats()
                
                # Wait 30 seconds between checks
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            print("\nStopping health monitor...")
            monitor.print_stats()

if __name__ == "__main__":
    asyncio.run(main()) 