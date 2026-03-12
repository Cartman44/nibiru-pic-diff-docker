import asyncio
import os
from io import BytesIO
from typing import Annotated

import httpx
import imagehash
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from PIL import Image
from pydantic import BaseModel

app = FastAPI(title="Image Verifier Pro")

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

# Reutilizăm clientul HTTP pentru a beneficia de Connection Pooling (esențial la sute de request-uri)
async_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, connect=5.0),
    limits=httpx.Limits(max_connections=200, max_keepalive_connections=50)
)

@app.on_event("shutdown")
async def shutdown_event():
    await async_client.aclose()

@app.post("/verify")
async def verify(
    data: CompareRequest, 
    x_api_key: Annotated[str | None, Header()] = None
):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Acces neautorizat")
    
    try:
        headers = {"User-Agent": "ImageBot/1.0"}
        
        # 1. Download asincron și paralel (I/O Bound)
        responses = await asyncio.gather(
            async_client.get(data.url1, headers=headers),
            async_client.get(data.url2, headers=headers)
        )
        
        for res in responses:
            res.raise_for_status()
        
        # 2. Procesare imagine (CPU Bound) - Mutată pe ThreadPool ca să nu blocheze Event Loop-ul
        def process_and_hash(content1, content2):
            img1 = Image.open(BytesIO(content1)).convert('RGB')
            img2 = Image.open(BytesIO(content2)).convert('RGB')
            h1 = imagehash.phash(img1)
            h2 = imagehash.phash(img2)
            return h1, h2

        # Executăm calculul greu fără să înghețăm serverul
        hash1, hash2 = await run_in_threadpool(process_and_hash, responses[0].content, responses[1].content)
        
        diff = hash1 - hash2
        
        return {
            "identical": diff <= 2,
            "distance": int(diff),
            "engine": "pHash-Async"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Eroare: {str(e)}")