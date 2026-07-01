from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ============ For using in every module ===========
app = FastAPI(
    title   = "Librarain Norton Assigment API",
    version = "1.0.0",
)
origins = [
    "http://localhost:3000",      
    "http://127.0.0.1:3000",       
    "http://localhost:3001",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],            
    allow_headers=["*"],           
)

import asyncio
from api.telegram_bots.bot_polling import start_telegram_polling

@app.on_event("startup")
async def startup_event():
    # Start Telegram polling in a background task
    asyncio.create_task(start_telegram_polling())

# ===== Import all modules here ===========
from api.register import *