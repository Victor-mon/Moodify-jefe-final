"""
main.py — FastAPI backend para Moodify
Rutas:
  POST /api/auth/login
  POST /api/auth/registro
  POST /api/auth/logout
  POST /api/transform
  POST /api/translate
  GET  /api/historial
  GET  /api/favoritos
  POST /api/favorito/{id}
  GET  /api/estadisticas
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import auth as auth_module
from auth import (
    auth_login, auth_registro, get_user_from_token,
    guardar_historial, obtener_historial, obtener_favoritos,
    togglear_favorito, obtener_estadisticas,
)

load_dotenv()

# ── Lazy-load del modelo (solo si HF_TOKEN está presente) ────
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    hf_token = os.getenv("HF_TOKEN")
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    if hf_token and not mock_mode:
        print("🔄 Cargando modelo LLM...")
        from model import MessageToneAgent
        agent = MessageToneAgent()
    else:
        print("⚠️  MOCK_MODE activo — el LLM no se cargará (modo preview)")
    yield
    print("👋 Apagando servidor")


app = FastAPI(title="Moodify API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sirve el frontend estático desde /frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ── Helpers ───────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None)):
    """Extrae y valida el JWT de Supabase del header Authorization."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")
    token = authorization.split(" ", 1)[1]
    user  = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return user


# ── Schemas ───────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RegistroRequest(BaseModel):
    email: str
    password: str
    username: str

class TransformRequest(BaseModel):
    mensaje: str

class TranslateRequest(BaseModel):
    textos_es: dict
    idioma: str

class FavoritoRequest(BaseModel):
    estado: bool   # estado ACTUAL (antes del toggle)


# ── Rutas: páginas HTML ───────────────────────────────────────

@app.get("/")
def serve_login():
    path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(path)

@app.get("/app")
def serve_app():
    path = os.path.join(FRONTEND_DIR, "app.html")
    return FileResponse(path)


# ── Rutas: auth ───────────────────────────────────────────────

@app.post("/api/auth/login")
def login(body: LoginRequest):
    ok, msg, token, username = auth_login(body.email, body.password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    return {"ok": True, "message": msg, "token": token, "username": username}


@app.post("/api/auth/registro")
def registro(body: RegistroRequest):
    ok, msg = auth_registro(body.email, body.password, body.username)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/auth/logout")
def logout():
    return {"ok": True}


# ── Rutas: transform / translate ─────────────────────────────

# Respuesta mock para MOCK_MODE
_MOCK_RESPONSE = {
    "diplomatico": "Le comento que el sistema ha presentado una falla técnica desde las 9am. Agradecería mucho su apoyo para escalar el incidente, ya que tenemos tres equipos sin poder operar.",
    "ejecutivo":   "Sistema caído desde las 9am. Impacto: 3 equipos bloqueados. Se requiere escalar a soporte de inmediato.",
    "casual":      "Oye, el sistema se cayó desde las 9 y llevamos horas sin poder trabajar. ¿Puedes escalarlo a soporte?",
    "textos_es": {
        "dipl": "Le comento que el sistema ha presentado una falla técnica desde las 9am. Agradecería mucho su apoyo para escalar el incidente, ya que tenemos tres equipos sin poder operar.",
        "ejec": "Sistema caído desde las 9am. Impacto: 3 equipos bloqueados. Se requiere escalar a soporte de inmediato.",
        "casu": "Oye, el sistema se cayó desde las 9 y llevamos horas sin poder trabajar. ¿Puedes escalarlo a soporte?",
    },
    "detector":   {"idioma": "Español", "emoji": "🇲🇽", "confianza": 85, "advertencia": ""},
    "preview":    "The system has been down since 9am. 3 teams are blocked and we need to escalate to support.",
    "tips": [
        {"icono": "🟡", "titulo": "Hay un poco de tensión aquí",   "texto": "Nombrarlo directamente suele funcionar mucho mejor que insinuarlo."},
        {"icono": "⏰", "titulo": "Esto va contra el reloj",       "texto": "Asegúrate de que el plazo esté en la primera oración."},
    ],
    "tipo": "reporte", "tono": "frustracion", "intensidad": "media",
}


@app.post("/api/transform")
def transform(body: TransformRequest, user=Depends(get_current_user)):
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    if mock_mode or agent is None:
        result = dict(_MOCK_RESPONSE)
    else:
        result = agent.procesar(body.mensaje)

    # Guarda en historial (incluso en mock)
    guardar_historial(
        user_id   = user.id,
        mensaje   = body.mensaje,
        dipl      = result["diplomatico"],
        ejec      = result["ejecutivo"],
        casu      = result["casual"],
        tipo      = result.get("tipo", "general"),
        tono      = result.get("tono", "neutro"),
        intensidad= result.get("intensidad", "baja"),
    )
    return result


@app.post("/api/translate")
def translate(body: TranslateRequest, user=Depends(get_current_user)):
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    if mock_mode or agent is None:
        return {
            "diplomatico": "I kindly inform you that the system has experienced a technical failure since 9am. I would greatly appreciate your support in escalating the incident.",
            "ejecutivo":   "System down since 9am. Impact: 3 teams blocked. Escalation to support required immediately.",
            "casual":      "Hey, the system's been down since 9 and we've been stuck for hours. Can you escalate it to support?",
        }
    dipl, ejec, casu = agent.traducir(body.textos_es, body.idioma)
    return {"diplomatico": dipl, "ejecutivo": ejec, "casual": casu}


# ── Rutas: historial / favoritos / stats ─────────────────────

@app.get("/api/historial")
def historial(user=Depends(get_current_user)):
    return obtener_historial(user.id, limite=30)


@app.get("/api/favoritos")
def favoritos(user=Depends(get_current_user)):
    return obtener_favoritos(user.id)


@app.post("/api/favorito/{record_id}")
def toggle_fav(record_id: str, body: FavoritoRequest, user=Depends(get_current_user)):
    nuevo = togglear_favorito(record_id, body.estado, user.id)
    return {"es_favorito": nuevo}


@app.get("/api/estadisticas")
def estadisticas(user=Depends(get_current_user)):
    return obtener_estadisticas(user.id)