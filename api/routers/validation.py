"""API Key Validation Router"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["validation"])


class ValidateKeyRequest(BaseModel):
    provider: str
    api_key: str


@router.post("/validate-key")
def validate_api_key(request: ValidateKeyRequest):
    """Validate an API key."""
    try:
        if request.provider == "anthropic":
            import httpx
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": request.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 5,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                )
                return {"valid": response.status_code == 200, "provider": "anthropic"}

        elif request.provider == "openai":
            import httpx
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "max_tokens": 5,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                )
                return {"valid": response.status_code == 200, "provider": "openai"}
        else:
            return {"valid": False, "error": "Unknown provider"}
    except Exception as e:
        return {"valid": False, "error": str(e)}
