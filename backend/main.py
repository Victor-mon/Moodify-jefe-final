"""
main.py — FastAPI backend para Moodify
Rutas:
  POST   /api/auth/login
  POST   /api/auth/registro
  POST   /api/auth/logout
  POST   /api/auth/reset-password
  GET    /api/perfil
  PUT    /api/perfil/username
  PUT    /api/perfil/email
  DELETE /api/cuenta
  POST   /api/transform          ← ahora con StreamingResponse
  POST   /api/translate
  GET    /api/historial
  GET    /api/favoritos
  POST   /api/favorito/{id}
  GET    /api/estadisticas
"""

import os
import re
import json
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import auth as auth_module
from auth import (
    auth_login, auth_registro, get_user_from_token,
    guardar_historial, obtener_historial, obtener_favoritos,
    togglear_favorito, obtener_estadisticas,
    supabase as supabase_client,
    db,
)

load_dotenv()

# ── Lazy-load del modelo ────────────────────────────────────
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    hf_token  = os.getenv("HF_TOKEN")
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

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/css",    StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js",     StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")),  name="js")
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ── Helpers ───────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")
    token = authorization.split(" ", 1)[1]
    user  = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return user

def sse_event(data: dict) -> str:
    """Formatea un evento Server-Sent Events."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


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
    estado: bool

class ResetRequest(BaseModel):
    email: str

class UsernameRequest(BaseModel):
    username: str

class EmailRequest(BaseModel):
    email: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

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


@app.post("/api/auth/reset-password")
def reset_password(body: ResetRequest):
    try:
        supabase_client.auth.reset_password_email(body.email.strip().lower())
    except Exception as e:
        print(f"[reset] Error: {e}")
    return {"ok": True, "message": "Si existe una cuenta con ese correo, recibirás un enlace."}


# ── Rutas: perfil ─────────────────────────────────────────────

@app.get("/api/perfil")
def perfil(user=Depends(get_current_user)):
    try:
        profile = db.table("profiles").select("username, email").eq("id", user.id).execute()
        if profile.data:
            return {
                "username": profile.data[0].get("username") or user.email.split("@")[0],
                "email":    profile.data[0].get("email")    or getattr(user, "email", ""),
            }
        return {
            "username": getattr(user, "email", "usuario").split("@")[0],
            "email":    getattr(user, "email", ""),
        }
    except Exception as e:
        print(f"[perfil] Error: {e}")
        return {
            "username": getattr(user, "email", "usuario").split("@")[0],
            "email":    getattr(user, "email", ""),
        }


@app.put("/api/perfil/username")
def cambiar_username(body: UsernameRequest, user=Depends(get_current_user)):
    nuevo = body.username.strip().lower()
    if len(nuevo) < 3:
        raise HTTPException(status_code=400, detail="❌ El username debe tener al menos 3 caracteres.")
    if len(nuevo) > 30:
        raise HTTPException(status_code=400, detail="❌ El username no puede superar 30 caracteres.")
    if not re.match(r'^[a-z0-9_]+$', nuevo):
        raise HTTPException(status_code=400, detail="❌ Solo letras, números y guion bajo (_).")
    try:
        existing = db.table("profiles").select("id").eq("username", nuevo).execute()
        if existing.data and existing.data[0]["id"] != user.id:
            raise HTTPException(status_code=400, detail="❌ Ese nombre de usuario ya está en uso.")
        db.table("profiles").update({"username": nuevo}).eq("id", user.id).execute()
        return {"ok": True, "username": nuevo}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[username] Error: {e}")
        raise HTTPException(status_code=500, detail="❌ Error al actualizar el nombre de usuario.")


@app.put("/api/perfil/email")
def cambiar_email(body: EmailRequest, user=Depends(get_current_user)):
    nuevo_email = body.email.strip().lower()
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', nuevo_email):
        raise HTTPException(status_code=400, detail="❌ Correo electrónico inválido.")
    try:
        db.table("profiles").update({"email": nuevo_email}).eq("id", user.id).execute()
        return {"ok": True, "message": "Se ha enviado un enlace de verificación a tu nuevo correo."}
    except Exception as e:
        print(f"[email] Error: {e}")
        raise HTTPException(status_code=500, detail="❌ Error al actualizar el correo.")


# ── Ruta: eliminar cuenta ─────────────────────────────────────

@app.delete("/api/cuenta")
def eliminar_cuenta(user=Depends(get_current_user)):
    try:
        try:
            db.table("historiales").delete().eq("user_id", user.id).execute()
        except Exception as e:
            print(f"[delete] Error borrando historial: {e}")
        try:
            db.table("profiles").delete().eq("id", user.id).execute()
        except Exception as e:
            print(f"[delete] Error borrando perfil: {e}")
        try:
            db.auth.admin.delete_user(user.id)
        except Exception as e:
            print(f"[delete] Error borrando usuario Auth: {e}")
        return {"ok": True, "message": "Cuenta eliminada correctamente."}
    except Exception as e:
        print(f"[delete] Error general: {e}")
        raise HTTPException(status_code=500, detail="❌ Error al eliminar la cuenta.")


# ── Mock response ─────────────────────────────────────────────

_MOCK_RESPONSE = {
    "diplomatico": "Le comento que el sistema ha presentado una falla técnica desde las 9am. Agradecería mucho su apoyo para escalar el incidente, ya que tenemos tres equipos sin poder operar.",
    "ejecutivo":   "Sistema caído desde las 9am. Impacto: 3 equipos bloqueados. Se requiere escalar a soporte de inmediato.",
    "casual":      "Oye, el sistema se cayó desde las 9 y llevamos horas sin poder trabajar. ¿Puedes escalarlo a soporte?",
    "textos_es": {
        "dipl": "Le comento que el sistema ha presentado una falla técnica desde las 9am. Agradecería mucho su apoyo para escalar el incidente, ya que tenemos tres equipos sin poder operar.",
        "ejec": "Sistema caído desde las 9am. Impacto: 3 equipos bloqueados. Se requiere escalar a soporte de inmediato.",
        "casu": "Oye, el sistema se cayó desde las 9 y llevamos horas sin poder trabajar. ¿Puedes escalarlo a soporte?",
    },
    "detector":  {"idioma": "Español", "emoji": "🇲🇽", "confianza": 85, "advertencia": ""},
    "preview":   "The system has been down since 9am. 3 teams are blocked and we need to escalate to support.",
    "tips": [
        {"icono": "🟡", "titulo": "Hay un poco de tensión aquí",
         "texto": "Nombrarlo directamente suele funcionar mucho mejor que insinuarlo."},
        {"icono": "⏰", "titulo": "Esto va contra el reloj",
         "texto": "Asegúrate de que el plazo esté en la primera oración."},
    ],
    "tipo": "reporte", "tono": "frustracion", "intensidad": "media",
}


# ── Ruta: transform con streaming ────────────────────────────

@app.post("/api/transform")
async def transform(body: TransformRequest, user=Depends(get_current_user)):
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"

    async def event_stream():
        import asyncio

        if mock_mode or agent is None:
            # ── MOCK: simula etapas con delays reales ──────────
            etapas = [
                (12,  "analizando",  "Analizando mensaje..."),
                (25,  "idioma",      "Detectando idioma..."),
                (38,  "preview",     "Generando vista previa..."),
                (55,  "dipl",        "Generando tono diplomático..."),
                (72,  "ejec",        "Generando tono ejecutivo..."),
                (88,  "casu",        "Generando tono casual..."),
                (96,  "guardando",   "Guardando en historial..."),
            ]
            for pct, stage, label in etapas:
                yield sse_event({"type": "progress", "pct": pct, "stage": stage, "label": label})
                await asyncio.sleep(0.18)

            result = dict(_MOCK_RESPONSE)

        else:
            # ── MODELO REAL: etapas reales ─────────────────────
            yield sse_event({"type": "progress", "pct": 10, "stage": "analizando", "label": "Analizando mensaje..."})
            await asyncio.sleep(0)

            yield sse_event({"type": "progress", "pct": 22, "stage": "idioma", "label": "Detectando idioma..."})
            await asyncio.sleep(0)

            yield sse_event({"type": "progress", "pct": 35, "stage": "preview", "label": "Generando vista previa..."})
            await asyncio.sleep(0)

            yield sse_event({"type": "progress", "pct": 42, "stage": "dipl", "label": "Generando tono diplomático..."})
            await asyncio.sleep(0)

            result    = agent.procesar(body.mensaje)
            tips_llm  = agent.generar_tips_llm(body.mensaje)
            if tips_llm:
                result["tips"] = tips_llm

            yield sse_event({"type": "progress", "pct": 78, "stage": "ejec", "label": "Generando tono ejecutivo..."})
            await asyncio.sleep(0)

            yield sse_event({"type": "progress", "pct": 91, "stage": "casu", "label": "Generando tono casual..."})
            await asyncio.sleep(0)

            yield sse_event({"type": "progress", "pct": 96, "stage": "guardando", "label": "Guardando en historial..."})
            await asyncio.sleep(0)

        # Guardar historial
        guardar_historial(
            user_id    = user.id,
            mensaje    = body.mensaje,
            dipl       = result["diplomatico"],
            ejec       = result["ejecutivo"],
            casu       = result["casual"],
            tipo       = result.get("tipo", "general"),
            tono       = result.get("tono", "neutro"),
            intensidad = result.get("intensidad", "baja"),
        )

        # Evento final con todos los datos
        yield sse_event({"type": "done", "pct": 100, **result})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ── Rutas: translate ──────────────────────────────────────────

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

@app.put("/api/perfil/password")
def cambiar_password(body: PasswordChangeRequest, user=Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="❌ La contraseña debe tener al menos 6 caracteres.")
    try:
        # Obtener el email del usuario
        profile = db.table("profiles").select("email").eq("id", user.id).execute()
        email = profile.data[0]["email"] if profile.data else getattr(user, "email", "")
        if not email:
            raise HTTPException(status_code=400, detail="❌ No se encontró el correo del usuario.")

        # Verificar contraseña actual intentando hacer login
        try:
            supabase_client.auth.sign_in_with_password({"email": email, "password": body.old_password})
        except Exception:
            raise HTTPException(status_code=400, detail="❌ La contraseña actual es incorrecta.")

        # Actualizar contraseña directamente via admin
        db.auth.admin.update_user_by_id(user.id, {"password": body.new_password})
        return {"ok": True, "message": "✅ Contraseña actualizada correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[password] Error: {e}")
        raise HTTPException(status_code=500, detail="❌ Error al actualizar la contraseña.")