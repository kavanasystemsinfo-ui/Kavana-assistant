"""KAVANA Assistant — API Principal FastAPI."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.rag import RAGEngine
from src.llm import LLMClient
from src.auth import AuthHandler

logger = logging.getLogger("kavana.assistant")

app = FastAPI(
    title="KAVANA Assistant IA",
    description="Asistente técnico inteligente para maquinaria industrial",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGEngine()
llm = None
auth = AuthHandler()

MANUALS_DIR = Path(__file__).resolve().parent.parent / "data" / "manuals"


# --- Schemas ---

class ChatRequest(BaseModel):
    question: str
    machine_filter: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = []


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


# --- Events ---

@app.on_event("startup")
async def startup():
    global llm
    import os
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        llm = LLMClient(api_key=api_key)
    # Indexar manuales disponibles
    if MANUALS_DIR.exists():
        for f in sorted(MANUALS_DIR.glob("*.json")):
            try:
                with open(f) as fh:
                    manual = json.load(fh)
                count = rag.index_manual(manual)
                if count:
                    logger.info("📚 Indexado %s: %d entradas", f.name, count)
            except Exception as e:
                logger.warning("⚠️ Error indexando %s: %s", f.name, e)


# --- Endpoints ---

@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "ok",
        "documents_indexed": rag.collection.count(),
        "llm_ready": llm is not None,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Responde a una pregunta del operario usando RAG + LLM."""
    if not llm:
        raise HTTPException(503, "LLM no configurado. Falta OPENAI_API_KEY")

    # 1. Buscar en RAG
    results = rag.query(req.question, k=5)

    if not results:
        return ChatResponse(
            answer="No encontré información relevante en los manuales. "
                   "¿Podrías reformular la pregunta o especificar la máquina?",
            sources=[],
        )

    # 2. Generar respuesta con LLM
    answer = llm.ask(req.question, results)

    return ChatResponse(
        answer=answer,
        sources=[
            {"machine": r["machine"], "section": r["section"],
             "code": r["code"], "score": round(r["score"], 3)}
            for r in results[:3]
        ],
    )


@app.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Autenticación de usuario."""
    user = auth.authenticate(req.email, req.password)
    if not user:
        raise HTTPException(401, "Credenciales inválidas")
    token = auth.generate_token(user)
    return LoginResponse(token=token, user=user)


@app.post("/upload")
async def upload_manual(file: UploadFile = File(...)):
    """Carga un manual técnico (JSON) al sistema."""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(400, "Solo se aceptan archivos JSON")

    content = await file.read()
    try:
        manual = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "JSON inválido")

    count = rag.index_manual(manual)
    return {
        "message": f"Manual '{manual.get('machine', 'desconocido')}' procesado",
        "entries_indexed": count,
    }


@app.get("/machines")
def list_machines():
    """Lista las máquinas disponibles en los manuales indexados."""
    manuals = []
    if MANUALS_DIR.exists():
        for f in MANUALS_DIR.glob("*.json"):
            with open(f) as fh:
                m = json.load(fh)
                manuals.append({
                    "machine": m.get("machine", ""),
                    "category": m.get("category", ""),
                    "sections": [s["id"] for s in m.get("sections", [])],
                })
    return {"machines": manuals}


@app.get("/stats")
def stats():
    """Estadísticas del sistema."""
    return {
        "documents_indexed": rag.collection.count(),
        "collections": len(rag.client.list_collections()),
    }
