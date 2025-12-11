from fastapi import APIRouter, HTTPException, Query, Response, Header
from typing import Optional
from utils.supabase_client_coder import select_with_retry
from utils.auth import validate_access_token

router = APIRouter(
    prefix="/coder",
    tags=["coder"],
)


@router.get("")
async def get_coder_data(
    authorization: Optional[str] = Header(None, description="Bearer token for authentication"),
    response: Response = None,
):
    try:
        # Validate access token
        user, token_refreshed = await validate_access_token(authorization, response)

        # Query coder database
        result = await select_with_retry('coders', id=1)

        return {
            "success": True,
            "data": result.data,
            "token_refreshed": None
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = str(e).lower()
        if 'timeout' in error_msg or 'connection' in error_msg:
            raise HTTPException(status_code=503, detail="Database connection timeout. Please try again.")
        raise HTTPException(status_code=500, detail=str(e))


