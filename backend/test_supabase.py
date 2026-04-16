import os, sys
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

print(f"URL: {url}")
print(f"KEY primeros 40 chars: {key[:40] if key else 'VACÍA'}...")
print()

try:
    from supabase import create_client
    sb = create_client(url, key)
    print("✅ Cliente Supabase creado")
except Exception as e:
    print(f"❌ Error creando cliente: {e}")
    sys.exit(1)

# Test 1: registro
print("\n--- Test 1: Registro ---")
try:
    res = sb.auth.sign_up({
        "email": "test_moodify_diag@test.com",
        "password": "test123456"
    })
    if res.user:
        print(f"✅ Registro OK — UID: {res.user.id}")
        test_uid = res.user.id
    else:
        print("⚠️  Sin usuario en respuesta")
        test_uid = None
except Exception as e:
    print(f"❌ Error en registro: {e}")
    test_uid = None

# Test 2: login
print("\n--- Test 2: Login ---")
try:
    res2 = sb.auth.sign_in_with_password({
        "email": "test_moodify_diag@test.com",
        "password": "test123456"
    })
    if res2.user:
        print(f"✅ Login OK — usuario: {res2.user.email}")
        token = res2.session.access_token
        print(f"   Token (primeros 30): {token[:30]}...")
    else:
        print("❌ Login falló")
        token = None
except Exception as e:
    print(f"❌ Error en login: {e}")
    token = None

# Test 3: tabla profiles
print("\n--- Test 3: Tabla profiles ---")
try:
    res3 = sb.table("profiles").select("*").limit(1).execute()
    print(f"✅ Tabla profiles accesible — filas: {len(res3.data)}")
except Exception as e:
    print(f"❌ Error en profiles: {e}")

# Test 4: tabla historiales
print("\n--- Test 4: Tabla historiales ---")
try:
    res4 = sb.table("historiales").select("*").limit(1).execute()
    print(f"✅ Tabla historiales accesible — filas: {len(res4.data)}")
except Exception as e:
    print(f"❌ Error en historiales: {e}")

print("\n--- Diagnóstico completo ---")