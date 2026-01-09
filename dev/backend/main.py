from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import asyncio
from dotenv import load_dotenv

# App imports
from dev.backend.database import engine, get_db
from dev.backend import models

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

# Load env vars first
basedir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(basedir, ".env")
load_dotenv(env_path, override=True)

# Import utils
from dev.backend.utils.scraper import UltimateScraper
from dev.backend.utils.serp import search_google
from dev.backend.utils.llm import analyze_content, generate_meta_tags

app = FastAPI()

from datetime import datetime

# --- Pydantic Models ---

class ProcessRequest(BaseModel):
    type: str  # 'url' or 'text'
    content: str

class HistoryItemCreate(BaseModel):
    title: str
    date_str: str
    full_input: str
    output: str
    type: str

class HistoryItemResponse(HistoryItemCreate):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        orm_mode = True

class HistoryItemUpdate(BaseModel):
    title: str

class PromptsSchema(BaseModel):
    openai_system: str
    openai_user: str
    anthropic_system: str
    anthropic_user: str

# Config
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# OpenRouter/Anthropic key setup
ANTHROPIC_OPENROUTER_API_KEY = os.getenv("ANTHROPIC_OPENROUTER_API_KEY", "")
if not ANTHROPIC_OPENROUTER_API_KEY:
    # Fallback to ANTHROPIC_API_KEY if strictly using that, or notify user
    ANTHROPIC_OPENROUTER_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Helper to get prompts safely ---
def get_or_create_prompts(db: Session):
    config = db.query(models.DBPromptsConfig).filter(models.DBPromptsConfig.id == 1).first()
    if not config:
        # Fallback to files or defaults
        base_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_dir = os.path.join(base_dir, "prompts")
        
        def read_file(name):
            try:
                with open(os.path.join(prompts_dir, name), "r", encoding="utf-8") as f:
                    return f.read()
            except:
                return ""
        
        # Default empty strings if files missing
        openai_sys = read_file("1ra_consulta_systemprompt.txt")
        openai_user = read_file("1ra_consulta_human_instructions.txt")
        anthropic_sys = read_file("consulta_final_systemprompt.txt")
        anthropic_user = read_file("consulta_final_human_instructions.txt")
        
        # Save to DB so next time it's there
        new_config = models.DBPromptsConfig(
            id=1,
            openai_system=openai_sys,
            openai_user=openai_user,
            anthropic_system=anthropic_sys,
            anthropic_user=anthropic_user
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        return new_config
    return config

# --- ENDPOINTS ---

@app.post("/api/process")
async def process_data(request: ProcessRequest, db: Session = Depends(get_db)):
    # 1. Fetch prompts *before* starting the async generator
    # to avoid thread-local DB issues inside the generator if not careful.
    prompts_config = get_or_create_prompts(db)
    
    # Capture values
    p_openai_sys = prompts_config.openai_system
    p_openai_user = prompts_config.openai_user
    p_anthropic_sys = prompts_config.anthropic_system
    p_anthropic_user = prompts_config.anthropic_user

    async def event_generator():
        try:
            yield json.dumps({"status": "info", "message": "Iniciando proceso..."}) + "\n"
            
            scraped_data = None
            text_for_analysis = ""
            
            # Step 1: Scrape
            if request.type == "url":
                yield json.dumps({"status": "info", "message": f"Scrapeando URL: {request.content}..."}) + "\n"
                scraper = UltimateScraper()
                try:
                    scraped_data = await asyncio.to_thread(scraper.scrape, request.content)
                except Exception as e:
                    yield json.dumps({"status": "error", "message": f"Error executando scraper: {str(e)}"}) + "\n"
                    return

                if not scraped_data:
                    yield json.dumps({"status": "error", "message": "Fallo al scrapear la URL."}) + "\n"
                    return
                
                text_for_analysis = scraped_data['full_text']
                yield json.dumps({"status": "success", "message": "Scraping completado."}) + "\n"
                
            else:
                yield json.dumps({"status": "info", "message": "Procesando texto ingresado..."}) + "\n"
                text_for_analysis = request.content
                scraped_data = text_for_analysis

            # Step 2: OpenAI Analysis
            yield json.dumps({"status": "info", "message": "Analizando contenido con OpenAI..."}) + "\n"
            if not OPENAI_API_KEY:
                 yield json.dumps({"status": "error", "message": "No OPENAI_API_KEY found."}) + "\n"
                 return

            try:
                # Pass prompts!
                analysis_result_tuple = await asyncio.to_thread(
                    analyze_content, 
                    scraped_data, 
                    OPENAI_API_KEY, 
                    p_openai_sys, 
                    p_openai_user
                )
                analysis_result, sys_prompt, user_prompt = analysis_result_tuple
                
            except Exception as e:
                 yield json.dumps({"status": "error", "message": f"Error OpenAI: {str(e)}"}) + "\n"
                 return

            yield json.dumps({"status": "success", "message": "Análisis lingüístico completado.", "data": analysis_result}) + "\n"
            
            # Step 3: SERP Search
            keyword = analysis_result.get("palabra_clave_principal")
            if not keyword:
                yield json.dumps({"status": "error", "message": "No se identificó palabra clave principal."}) + "\n"
                return
                
            yield json.dumps({"status": "info", "message": f"Buscando '{keyword}' en Google..."}) + "\n"
            try:
                serp_result = await asyncio.to_thread(search_google, keyword, SERPER_API_KEY)
            except Exception as e:
                yield json.dumps({"status": "error", "message": f"Error SerperDev: {str(e)}"}) + "\n"
                return

            if "error" in serp_result:
                 yield json.dumps({"status": "error", "message": f"Error en SERP: {serp_result['error']}"}) + "\n"
                 return
                 
            yield json.dumps({"status": "success", "message": "Resultados de búsqueda obtenidos.", "data": serp_result}) + "\n"
            
            # Step 4: Anthropic Generation
            yield json.dumps({"status": "info", "message": "Generando Meta Tags con Claude..."}) + "\n"
            
            if not ANTHROPIC_OPENROUTER_API_KEY:
                 yield json.dumps({"status": "error", "message": "No ANTHROPIC_OPENROUTER_API_KEY found."}) + "\n"
                 return

            try:
                # Pass prompts!
                final_output_tuple = await asyncio.to_thread(
                    generate_meta_tags, 
                    analysis_result, 
                    text_for_analysis, 
                    serp_result, 
                    ANTHROPIC_OPENROUTER_API_KEY,
                    p_anthropic_sys,
                    p_anthropic_user
                )
                final_output, sys_prompt, user_prompt = final_output_tuple
                
            except Exception as e:
                 yield json.dumps({"status": "error", "message": f"Error OpenRouter/Anthropic: {str(e)}"}) + "\n"
                 return
            
            yield json.dumps({"status": "complete", "message": "Generación completada.", "data": final_output}) + "\n"
            
        except Exception as e:
            yield json.dumps({"status": "error", "message": f"Error crítico inesperado: {str(e)}"}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# --- HISTORY API ---

@app.get("/api/history", response_model=List[HistoryItemResponse])
def get_history(db: Session = Depends(get_db)):
    return db.query(models.DBHistoryItem).order_by(models.DBHistoryItem.id.desc()).all()

@app.post("/api/history", response_model=HistoryItemResponse)
def create_history(item: HistoryItemCreate, db: Session = Depends(get_db)):
    try:
        db_item = models.DBHistoryItem(
            title=item.title,
            date_str=item.date_str,
            full_input=item.full_input,
            output=item.output,
            type=item.type
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception as e:
        print(f"CRITICAL DB ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/history/{item_id}")
def delete_history(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.DBHistoryItem).filter(models.DBHistoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"status": "success"}

@app.put("/api/history/{item_id}")
def update_history(item_id: int, item: HistoryItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(models.DBHistoryItem).filter(models.DBHistoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.title = item.title
    db.commit()
    db.refresh(db_item)
    return db_item


# --- PROMPTS API ---

@app.get("/api/prompts")
def get_prompts_endpoint(db: Session = Depends(get_db)):
    config = get_or_create_prompts(db)
    return {
        "openai_system": config.openai_system,
        "openai_user": config.openai_user,
        "anthropic_system": config.anthropic_system,
        "anthropic_user": config.anthropic_user
    }

@app.post("/api/prompts")
async def save_prompts_endpoint(prompts: PromptsSchema, db: Session = Depends(get_db)):
    config = get_or_create_prompts(db) # Use get_or_create to ensure row 1 exists
    
    config.openai_system = prompts.openai_system
    config.openai_user = prompts.openai_user
    config.anthropic_system = prompts.anthropic_system
    config.anthropic_user = prompts.anthropic_user
    
    db.commit()
    return {"status": "success", "message": "Prompts actualizados correctamente"}

# Serve frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"Warning: Frontend path {frontend_path} does not exist.")
