from fastapi import APIRouter, Response, Header
from typing import Optional
from controllers.coder_controller import CoderController

router = APIRouter(
    prefix="/coder",
    tags=["coder"],
)

# Initialize controller
coder_controller = CoderController()

@router.get("")
async def get_coder_data(
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None,
):
    """Get coder data from the coder database"""
    return await coder_controller.get_coder_data(authorization, response)


