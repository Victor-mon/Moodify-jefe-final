import os
import time
import httpx
import jwt as pyjwt
from supabase import create_client, Client
from supabase.client import ClientOptions
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_KEY     = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")
JWT_SECRET       = os.getenv("SUPABASE_JWT_SECRET", "")   # ← agrega esto a tu .env
MINIMO_STATS     = 10

# ── Clientes con timeouts mayores ────────────────────────────────
# postgrest_client_timeout=60 da margen suficiente en Windows/Docker
supabase: Client = create_client(
    SUPABASE_URL, SUPABASE_KEY,
    options=ClientOptions(
        postgrest_client_timeout=60,
        storage_client_timeout=60,
    )
)

db: Client = create_client(
    SUPABASE_URL, SUPABASE_SERVICE,
    options=ClientOptions(
        postgrest_client_timeout=60,
        storage_client_timeout=60,
    )
)


# ── Helper: reintentos con backoff ────────────────────────────────
def _auth_request_with_timeout(fn, *args, max_intentos=3, espera=2.0, **kwargs):
    """
    Reintenta llamadas de auth hasta max_intentos veces.
    Solo reintenta en errores de red/timeout, no en credenciales inválidas.
    """
    ultimo_error = None
    for intento in range(max_intentos):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            ultimo_error = e
            msg = str(e).lower()
            es_red = any(k in msg for k in (
                "timed out", "timeout", "connect", "network",
                "connection", "unreachable", "refused",
            ))
            if es_red and intento < max_intentos - 1:
                backoff = espera * (intento + 1)   # 2s, 4s, …
                print(f"[auth] Intento {intento + 1} falló (timeout). Reintentando en {backoff:.1f}s…")
                time.sleep(backoff)
                continue
            # Error que no es de red → propagar inmediatamente
            raise
    raise ultimo_error


# ── Validación JWT LOCAL (sin llamada a red) ──────────────────────
def _decode_jwt_local(token: str):
    """
    Decodifica y verifica el JWT de Supabase localmente usando SUPABASE_JWT_SECRET.
    Devuelve el payload o None si el token es inválido/expirado.
    Si JWT_SECRET no está configurado, cae al modo sin verificación de firma
    (solo decodifica — suficiente para extraer el sub/user_id).
    """
    try:
        if JWT_SECRET:
            payload = pyjwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            # Sin secreto: decodificar sin verificar firma (solo para dev/preview)
            payload = pyjwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256"],
            )
        return payload
    except pyjwt.ExpiredSignatureError:
        print("[jwt] Token expirado")
        return None
    except Exception as e:
        print(f"[jwt] Error decodificando: {e}")
        return None


class _LocalUser:
    """Objeto mínimo compatible con lo que espera get_current_user en main.py."""
    def __init__(self, payload: dict):
        self.id    = payload.get("sub", "")
        self.email = payload.get("email", "")


def get_user_from_token(token: str):
    """
    Primero intenta validar el JWT localmente (sin red).
    Si JWT_SECRET no está configurado o la decodificación falla,
    cae al método de red como respaldo.
    """
    payload = _decode_jwt_local(token)
    if payload and payload.get("sub"):
        return _LocalUser(payload)

    # Respaldo: llamada a red (solo si la validación local falló)
    try:
        res = _auth_request_with_timeout(supabase.auth.get_user, token, max_intentos=2, espera=1.5)
        return res.user if res else None
    except Exception as e:
        print(f"[token] Error en respaldo de red: {e}")
        return None


# ── Auth ─────────────────────────────────────────────────────────

def auth_registro(email: str, password: str, username: str) -> tuple:
    try:
        if len(password) < 6:
            return False, "❌ La contraseña debe tener al menos 6 caracteres."
        if len(username.strip()) < 3:
            return False, "❌ El nombre de usuario debe tener al menos 3 caracteres."
        username = username.strip().lower()

        # Verificar username duplicado
        try:
            existing = db.table("profiles").select("id").eq("username", username).execute()
            if existing.data:
                return False, "❌ Ese nombre de usuario ya está en uso."
        except Exception as e:
            print(f"[registro] Error verificando username: {e}")
            return False, "❌ Error de conexión con la base de datos. ¿Está Docker corriendo?"

        # Crear usuario en Supabase Auth
        try:
            res = _auth_request_with_timeout(
                supabase.auth.sign_up,
                {"email": email, "password": password},
                max_intentos=3, espera=2.0,
            )
        except Exception as e:
            msg = str(e)
            print(f"[registro] Error en sign_up: {msg}")
            if "already registered" in msg:
                return False, "❌ Este correo ya está registrado."
            if any(k in msg.lower() for k in ("timed out", "timeout", "connect")):
                return False, "❌ No se pudo conectar a Supabase. Verifica que Docker esté corriendo."
            return False, f"❌ {msg}"

        if not res.user:
            return False, "❌ No se pudo crear la cuenta."

        # Insertar perfil
        try:
            db.table("profiles").insert({
                "id":       res.user.id,
                "username": username,
            }).execute()
        except Exception as e:
            print(f"[registro] Error insertando perfil: {e}")

        return True, "✅ Cuenta creada exitosamente."

    except Exception as e:
        msg = str(e)
        print(f"[registro] Error inesperado: {msg}")
        return False, f"❌ {msg}"


def auth_login(email: str, password: str) -> tuple:
    try:
        res = _auth_request_with_timeout(
            supabase.auth.sign_in_with_password,
            {"email": email.strip(), "password": password},
            max_intentos=3, espera=2.0,
        )

        # Obtener username del perfil
        try:
            profile = db.table("profiles").select("username").eq("id", res.user.id).execute()
            username = profile.data[0]["username"] if profile.data else res.user.email.split("@")[0]
        except Exception:
            username = res.user.email.split("@")[0]

        token = res.session.access_token
        return True, "✅ Bienvenido", token, username

    except Exception as e:
        msg = str(e)
        print(f"[login] Error: {msg}")
        if "Invalid login credentials" in msg:
            return False, "❌ Correo o contraseña incorrectos.", "", ""
        if any(k in msg.lower() for k in ("timed out", "timeout", "connect", "network")):
            return False, "❌ No se pudo conectar a Supabase. Verifica que Docker esté corriendo.", "", ""
        return False, f"❌ {msg}", "", ""


# ── Historial ─────────────────────────────────────────────────────

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
        print(f"[historial] Error guardando: {e}")


def obtener_historial(user_id: str, limite=30):
    try:
        res = db.table("historiales").select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True).limit(limite).execute()
        return res.data or []
    except Exception as e:
        print(f"[historial] Error obteniendo: {e}")
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
    except Exception as e:
        print(f"[favorito] Error: {e}")
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
            "total":        total,
            "favoritos":    favoritos,
            "emociones":    dict(sorted(emociones.items(), key=lambda x: -x[1])),
            "tipos":        dict(sorted(tipos.items(),     key=lambda x: -x[1])),
            "dia_top":      dia_top,
            "msgs_dia_top": dias.get(dia_top, 0),
        }
    except Exception as e:
        print(f"[stats] Error: {e}")
        return {}