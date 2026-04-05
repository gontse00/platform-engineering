from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
import os

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "survivor-super-secret-key")
ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    email: str

@router.post("/login")
async def login(request: LoginRequest):
    # For your local mission, we'll keep it simple: 
    # If the email exists in our 'admins' table, we grant a token.
    # (In a real scenario, you'd check a password here too)
    
    # Mocking a successful check for now to get you running
    token_data = {
        "sub": request.email,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}