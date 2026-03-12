import asyncio
import os
from io import BytesIO
from typing import Annotated

import httpx
import imagehash
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

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
        raise HTTPException(status_code=500, detail="Server configuration error: API_KEY missing")
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Acces neautorizat")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            # Descarcă ambele imagini în paralel
            tasks = [
                client.get(data.url1, headers=headers),
                client.get(data.url2, headers=headers)
            ]
            responses = await asyncio.gather(*tasks)
            
            for res in responses:
                res.raise_for_status()
        
        # Procesare imagini (PIL este sincron, dar pHash e rapid)
        img1 = Image.open(BytesIO(responses[0].content)).convert('RGB')
        img2 = Image.open(BytesIO(responses[1].content)).convert('RGB')
        
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        diff = hash1 - hash2
        
        return {
            "identical": diff <= 2, # Poți urca la 5 dacă vrei să fii mai tolerant cu compresia
            "distance": int(diff),
            "engine": "pHash"
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Eroare la descărcare: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Eroare procesare: {str(e)}")