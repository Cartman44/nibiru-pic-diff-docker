from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated
import imagehash
from PIL import Image
import httpx
from io import BytesIO
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.sellymedia\.workers\.dev|http://localhost:3000",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY")

class CompareRequest(BaseModel):
    url1: str
    url2: str

@app.get("/")
async def health_check():
    return {"status": "online", "security": "enabled"}

@app.post("/verify")
async def verify(
    data: CompareRequest, 
    x_api_key: Annotated[str | None, Header()] = None
):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="Server configuration error")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Acces neautorizat")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"User-Agent": "Mozilla/5.0"}
            # Descărcăm ambele imagini în paralel
            responses = await asyncio.gather(
                client.get(data.url1, headers=headers),
                client.get(data.url2, headers=headers)
            )
            
            for res in responses:
                res.raise_for_status()
        
        img1 = Image.open(BytesIO(responses[0].content)).convert('RGB')
        img2 = Image.open(BytesIO(responses[1].content)).convert('RGB')
        
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        diff = hash1 - hash2
        
        return {
            "identical": diff <= 2, 
            "distance": int(diff),
            "engine": "pHash"
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Eroare la descărcarea imaginii: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Eroare procesare: {str(e)}")

import asyncio