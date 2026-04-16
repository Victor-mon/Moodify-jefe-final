import os
import time
import httpx
from supabase import create_client, Client
from supabase.client import ClientOptions
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_KEY     = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE = os.getenv("SUPABASE_SERVICE_KEY")
MINIMO_STATS     = 10

# ── Clientes con timeouts generosos para Docker local en Windows ──
supabase: Client = create_client(
    SUPABASE_URL, SUPABASE_KEY,
    options=ClientOptions(
        postgrest_client_timeout=30,
        storage_client_timeout=30,
    )
)

db: Client = create_client(
    SUPABASE_URL, SUPABASE_SERVICE,
    options=ClientOptions(
        postgrest_client_timeout=30,
        storage_client_timeout=30,
    )
)

# ── Helper: llamadas auth con timeout explícito via httpx ────────
def _auth_request_with_timeout(fn, *args, max_intentos=3, espera=1.5, **kwargs):
    """
    Envuelve una llamada de Supabase auth reintentándola hasta max_intentos veces.
    Captura timeouts de httpx (que la librería supabase-py no expone directamente).
    """
    ultimo_error = None
    for intento in range(max_intentos):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            ultimo_error = e
            msg = str(e).lower()
            # Solo reintentar en timeouts o errores de red, no en credenciales inválidas
            if any(k in msg for k in ("timed out", "timeout", "connect", "network", "connection")):
                if intento < max_intentos - 1:
                    print(f"[auth] Intento {intento + 1} falló (timeout). Reintentando en {espera}s...")
                    time.sleep(espera)
                    continue
            # Error que no es de red → no reintentar
            raise
    raise ultimo_error


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
                {"email": email, "password": password}
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
                "username": username
            }).execute()
        except Exception as e:
            print(f"[registro] Error insertando perfil: {e}")
            # El usuario se creó en auth pero no en profiles — no es crítico para el login
            # pero lo reportamos

        return True, "✅ Cuenta creada exitosamente."

    except Exception as e:
        msg = str(e)
        print(f"[registro] Error inesperado: {msg}")
        return False, f"❌ {msg}"


def auth_login(email: str, password: str) -> tuple:
    try:
        res = _auth_request_with_timeout(
            supabase.auth.sign_in_with_password,
            {"email": email.strip(), "password": password}
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


def get_user_from_token(token: str):
    try:
        res = _auth_request_with_timeout(supabase.auth.get_user, token)
        return res.user if res else None
    except Exception as e:
        print(f"[token] Error: {e}")
        return None


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