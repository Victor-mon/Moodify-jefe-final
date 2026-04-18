import os
import re
import time
import jwt as pyjwt
from supabase import create_client, Client
from supabase.client import ClientOptions
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_KEY     = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")
JWT_SECRET       = os.getenv("SUPABASE_JWT_SECRET", "")
MINIMO_STATS     = 10

# ── Clientes Supabase ─────────────────────────────────────────────
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
                backoff = espera * (intento + 1)
                print(f"[auth] Intento {intento + 1} falló (timeout). Reintentando en {backoff:.1f}s…")
                time.sleep(backoff)
                continue
            raise
    raise ultimo_error


# ── Validación JWT LOCAL (sin llamada a red) ──────────────────────
def _decode_jwt_local(token: str):
    """
    Decodifica y verifica el JWT de Supabase localmente.
    Si JWT_SECRET no está configurado, decodifica sin verificar firma
    (suficiente para dev/preview con MOCK_MODE).
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
    """Objeto mínimo compatible con get_current_user en main.py."""
    def __init__(self, payload: dict):
        self.id    = payload.get("sub", "")
        self.email = payload.get("email", "")


def get_user_from_token(token: str):
    """
    Valida el JWT primero localmente (sin red).
    Si falla, usa llamada a red como respaldo.
    """
    payload = _decode_jwt_local(token)
    if payload and payload.get("sub"):
        return _LocalUser(payload)

    try:
        res = _auth_request_with_timeout(supabase.auth.get_user, token, max_intentos=2, espera=1.5)
        return res.user if res else None
    except Exception as e:
        print(f"[token] Error en respaldo de red: {e}")
        return None


# ── Auth ─────────────────────────────────────────────────────────

def _validar_username(username: str) -> tuple[bool, str]:
    """Valida formato del username: solo letras, números y guion bajo."""
    username = username.strip().lower()
    if len(username) < 3:
        return False, "❌ El username debe tener al menos 3 caracteres."
    if len(username) > 30:
        return False, "❌ El username no puede superar 30 caracteres."
    if not re.match(r'^[a-z0-9_]+$', username):
        return False, "❌ El username solo puede contener letras, números y guion bajo (_)."
    return True, username


def auth_registro(email: str, password: str, username: str) -> tuple:
    try:
        # ── 1. Validaciones locales ───────────────────────────────
        if len(password) < 6:
            return False, "❌ La contraseña debe tener al menos 6 caracteres."

        ok, resultado = _validar_username(username)
        if not ok:
            return False, resultado
        username = resultado  # resultado es el username normalizado
        email    = email.strip().lower()

        # ── 2. Verificar username duplicado (SELECT previo) ───────
        try:
            existing = db.table("profiles").select("id").eq("username", username).execute()
            if existing.data:
                return False, "❌ Ese nombre de usuario ya está en uso."
        except Exception as e:
            print(f"[registro] Error verificando username: {e}")
            return False, "❌ Error de conexión con la base de datos."

        # ── 3. Crear usuario en Supabase Auth ─────────────────────
        # Supabase rechaza emails duplicados automáticamente.
        try:
            res = _auth_request_with_timeout(
                supabase.auth.sign_up,
                {"email": email, "password": password},
                max_intentos=3, espera=2.0,
            )
        except Exception as e:
            msg = str(e)
            if "already registered" in msg or "User already registered" in msg:
                return False, "❌ Este correo ya está registrado. ¿Olvidaste tu contraseña?"
            if any(k in msg.lower() for k in ("timed out", "timeout", "connect")):
                return False, "❌ No se pudo conectar a Supabase."
            return False, f"❌ {msg}"

        if not res.user:
            return False, "❌ No se pudo crear la cuenta."

        # ── 4. Insertar perfil en tabla profiles ──────────────────
        # El UNIQUE constraint en Supabase actúa como segunda guarda
        # en caso de race condition entre el SELECT y este INSERT.
        try:
            db.table("profiles").insert({
                "id":       res.user.id,
                "username": username,
                "email":    email,
            }).execute()
        except Exception as e:
            err = str(e).lower()
            if "unique" in err or "duplicate" in err:
                # Race condition: otro usuario tomó el username en el intervalo.
                # Limpiamos el usuario recién creado en Auth para no dejar huérfanos.
                try:
                    db.auth.admin.delete_user(res.user.id)
                except Exception as del_e:
                    print(f"[registro] No se pudo limpiar usuario huérfano: {del_e}")
                return False, "❌ Ese nombre de usuario ya está en uso (intenta con otro)."
            print(f"[registro] Error insertando perfil: {e}")
            # El usuario Auth fue creado pero no tiene perfil.
            # No es crítico — puede funcionar igual con username derivado del email.

        return True, "✅ Cuenta creada exitosamente."

    except Exception as e:
        print(f"[registro] Error inesperado: {e}")
        return False, f"❌ {str(e)}"


def auth_login(email: str, password: str) -> tuple:
    try:
        res = _auth_request_with_timeout(
            supabase.auth.sign_in_with_password,
            {"email": email.strip().lower(), "password": password},
            max_intentos=3, espera=2.0,
        )

        try:
            profile  = db.table("profiles").select("username").eq("id", res.user.id).execute()
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
            return False, "❌ No se pudo conectar a Supabase. Verifica tu conexión.", "", ""
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