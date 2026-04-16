import os
from supabase import create_client, Client
from supabase.client import ClientOptions
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE  = os.getenv("SUPABASE_SERVICE_KEY")
MINIMO_STATS = 10

supabase: Client = create_client(
    SUPABASE_URL, SUPABASE_KEY,
    options=ClientOptions(postgrest_client_timeout=120, storage_client_timeout=120)
)

db: Client = create_client(
    SUPABASE_URL, SUPABASE_SERVICE,
    options=ClientOptions(postgrest_client_timeout=120, storage_client_timeout=120)
)

# ── Auth ─────────────────────────────────────────────────────

def auth_registro(email: str, password: str, username: str) -> tuple:
    try:
        if len(password) < 6:
            return False, "❌ La contraseña debe tener al menos 6 caracteres."
        if len(username.strip()) < 3:
            return False, "❌ El nombre de usuario debe tener al menos 3 caracteres."
        username = username.strip().lower()
        existing = db.table("profiles").select("id").eq("username", username).execute()
        if existing.data:
            return False, "❌ Ese nombre de usuario ya está en uso."
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            db.table("profiles").insert({"id": res.user.id, "username": username}).execute()
            return True, "✅ Cuenta creada exitosamente."
        return False, "❌ No se pudo crear la cuenta."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg:
            return False, "❌ Este correo ya está registrado."
        if "timed out" in msg.lower():
            return False, "⚠️ Intenta iniciar sesión — la cuenta pudo haberse creado."
        return False, f"❌ {msg}"


def auth_login(email: str, password: str) -> tuple:
    try:
        import time
        for intento in range(2):
            try:
                res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
                break
            except Exception as e:
                if intento == 0 and "timed out" in str(e).lower():
                    time.sleep(1)
                    continue
                raise
        profile = db.table("profiles").select("username").eq("id", res.user.id).execute()
        username = profile.data[0]["username"] if profile.data else res.user.email.split("@")[0]
        token = res.session.access_token
        return True, "✅ Bienvenido", token, username
    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "❌ Correo o contraseña incorrectos.", "", ""
        if "timed out" in msg.lower():
            return False, "❌ Conexión lenta — intenta de nuevo.", "", ""
        return False, f"❌ {msg}", "", ""


def get_user_from_token(token: str):
    try:
        res = supabase.auth.get_user(token)
        return res.user if res else None
    except Exception:
        return None


# ── Historial ────────────────────────────────────────────────

def guardar_historial(user_id: str, mensaje, dipl, ejec, casu, tipo, tono, intensidad):
    try:
        db.table("historiales").insert({
            "user_id":             user_id,
            "mensaje_original":    mensaje[:500],
            "version_diplomatica": dipl[:500],
            "version_ejecutiva":   ejec[:500],
            "version_casual":      casu[:500],
            "tipo_mensaje":        tipo,
            "tono_emocional":      tono,
            "intensidad":          intensidad,
            "es_favorito":         False,
        }).execute()
    except Exception as e:
        print(f"[historial] Error: {e}")


def obtener_historial(user_id: str, limite=30):
    try:
        res = db.table("historiales").select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True).limit(limite).execute()
        return res.data or []
    except Exception as e:
        print(f"[historial] Error: {e}")
        return []


def obtener_favoritos(user_id: str):
    try:
        res = db.table("historiales").select("*") \
            .eq("user_id", user_id).eq("es_favorito", True) \
            .order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[favoritos] Error: {e}")
        return []


def togglear_favorito(record_id: str, estado: bool, user_id: str) -> bool:
    try:
        db.table("historiales") \
            .update({"es_favorito": not estado}) \
            .eq("id", record_id).eq("user_id", user_id).execute()
        return not estado
    except Exception:
        return estado


def obtener_estadisticas(user_id: str):
    try:
        res = db.table("historiales") \
            .select("tipo_mensaje,tono_emocional,es_favorito,created_at") \
            .eq("user_id", user_id).execute()
        items = res.data or []
        total = len(items)
        if total == 0:
            return {"total": 0}
        emociones, tipos, dias = {}, {}, {}
        favoritos = 0
        for it in items:
            t  = it.get("tono_emocional", "neutro") or "neutro"
            tp = it.get("tipo_mensaje",   "general") or "general"
            emociones[t]  = emociones.get(t, 0) + 1
            tipos[tp]     = tipos.get(tp, 0) + 1
            if it.get("es_favorito"):
                favoritos += 1
            fecha = (it.get("created_at", "") or "")[:10]
            if fecha:
                dias[fecha] = dias.get(fecha, 0) + 1
        dia_top = max(dias, key=dias.get) if dias else "—"
        return {
            "total":         total,
            "favoritos":     favoritos,
            "emociones":     dict(sorted(emociones.items(), key=lambda x: -x[1])),
            "tipos":         dict(sorted(tipos.items(),     key=lambda x: -x[1])),
            "dia_top":       dia_top,
            "msgs_dia_top":  dias.get(dia_top, 0),
        }
    except Exception as e:
        print(f"[stats] Error: {e}")
        return {}