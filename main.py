from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import imagehash
from PIL import Image
import requests
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
def health_check():
    return {"status": "online", "security": "enabled"}

@app.post("/verify")
async def verify(data: CompareRequest, x_api_key: str = Header(None)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="Server configuration error")

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Acces neautorizat")
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        
        res1 = requests.get(data.url1, headers=headers, timeout=10)
        res2 = requests.get(data.url2, headers=headers, timeout=10)
        
        res1.raise_for_status()
        res2.raise_for_status()
        
        # Procesare imagini: Convertim în RGB pentru a evita erori la PNG-uri transparente
        img1 = Image.open(BytesIO(res1.content)).convert('RGB')
        img2 = Image.open(BytesIO(res2.content)).convert('RGB')
        
        # Generare Perceptual Hash
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        
        # Calculăm diferența (Hamming Distance)
        diff = hash1 - hash2
        
        return {
            "identical": diff <= 1,
            "distance": int(diff),
            "engine": "pHash"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))