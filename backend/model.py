"""
model.py — MessageToneAgent (modo Colab remoto)
El modelo NO se carga localmente. Toda la inferencia ocurre en
el servidor FastAPI que corre en Google Colab (GPU T4) expuesto
via ngrok. Este archivo solo maneja:
  - El pipeline de processing.py (local, sin GPU)
  - Llamadas HTTP al servidor de Colab
"""

import os
import re
import json
import httpx

from processing import (
    GateKeeper, DetectorIdioma, AsesorEmocional,
    PreProcesador, IntentExtractor, RoleMatrix,
    PromptBuilder, OutputCleaner,
)

# Timeout generoso porque la T4 puede tardar 3-8s por generación
_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class MessageToneAgent:

    def __init__(self):
        self.base_url = os.getenv("COLAB_LLM_URL", "").rstrip("/")
        self.api_key  = os.getenv("COLAB_API_KEY", "")

        if not self.base_url:
            raise ValueError(
                "❌ COLAB_LLM_URL no encontrado en variables de entorno.\n"
                "   Copia la URL de ngrok desde Colab y pégala en tu .env"
            )

        print(f"🌐 Conectando al servidor LLM en Colab: {self.base_url}")
        self._verificar_conexion()

        # Clases de procesamiento — todas corren localmente, sin GPU
        self.gate      = GateKeeper()
        self.pre_proc  = PreProcesador()
        self.extractor = IntentExtractor()
        self.roles     = RoleMatrix()
        self.builder   = PromptBuilder()
        self.cleaner   = OutputCleaner()

        print("✅ MessageToneAgent listo (modo Colab remoto)")

    # ── Helpers HTTP ──────────────────────────────────────────

    def _headers(self):
        return {
            "X-API-Key":    self.api_key,
            "Content-Type": "application/json",
        }

    def _verificar_conexion(self):
        try:
            r = httpx.get(
                f"{self.base_url}/health",
                headers=self._headers(),
                timeout=10.0,
            )
            r.raise_for_status()
            print(f"   ✅ Colab responde: {r.json()}")
        except Exception as e:
            raise ConnectionError(
                f"❌ No se pudo conectar a Colab en {self.base_url}/health\n"
                f"   ¿Está corriendo el servidor y el túnel ngrok?\n"
                f"   Error: {e}"
            )

    def _post(self, endpoint: str, payload: dict) -> dict:
        """Hace un POST al servidor de Colab y devuelve el JSON de respuesta."""
        try:
            r = httpx.post(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                json=payload,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            return r.json()
        except httpx.TimeoutException:
            print(f"[colab] Timeout en {endpoint}")
            return {}
        except httpx.HTTPStatusError as e:
            print(f"[colab] HTTP {e.response.status_code} en {endpoint}: {e.response.text}")
            return {}
        except Exception as e:
            print(f"[colab] Error en {endpoint}: {e}")
            return {}

    # ── Pipeline principal ────────────────────────────────────

    def procesar(self, mensaje: str) -> dict:
        detector = DetectorIdioma()
        asesor   = AsesorEmocional()

        def _err(msg):
            return {
                "error": msg, "diplomatico": msg, "ejecutivo": msg, "casual": msg,
                "detector": detector.detectar(""), "tips": [],
                "tipo": "general", "tono": "neutro", "intensidad": "baja", "textos_es": {},
            }

        if not mensaje or not mensaje.strip():
            return _err("❌ El mensaje no puede estar vacío.")
        if len(mensaje.strip().split()) < 2:
            return _err("⚠️ Agrega al menos 2 palabras.")

        puede, motivo = GateKeeper().evaluar(mensaje)
        if not puede:
            return _err(GateKeeper().mensaje_feedback(motivo))

        # ── Procesamiento local (sin GPU) ─────────────────────
        pre     = PreProcesador().analizar(mensaje)
        intento = IntentExtractor().extraer(mensaje)
        ancla   = IntentExtractor().construir_ancla(intento)
        ctx     = RoleMatrix().analizar(mensaje, pre)
        det     = detector.detectar(mensaje)
        idioma_origen = "en" if det["idioma"] == "Inglés" else "es"
        tips    = asesor.generar(ctx, pre)

        # ── Construir los 3 prompts localmente ────────────────
        prompt_dipl = PromptBuilder().construir(mensaje, "diplomatico", ctx, pre, intento, ancla)
        prompt_ejec = PromptBuilder().construir(mensaje, "ejecutivo",   ctx, pre, intento, ancla)
        prompt_casu = PromptBuilder().construir(mensaje, "casual",      ctx, pre, intento, ancla)

        # ── Llamada única a Colab con los 3 prompts ───────────
        resp = self._post("/generate", {
            "mensaje":      mensaje,
            "prompt_dipl":  prompt_dipl,
            "prompt_ejec":  prompt_ejec,
            "prompt_casu":  prompt_casu,
            "n_palabras":   ctx["palabras"],
            "lon_clase":    pre["longitud_clase"],
            "tiene_emojis": ctx["tiene_emojis"],
        })

        # ── Limpiar respuestas localmente ─────────────────────
        cleaner = OutputCleaner()
        resultados = {}
        for tono, key in [("diplomatico","diplomatico"), ("ejecutivo","ejecutivo"), ("casual","casual")]:
            raw    = resp.get(tono, "")
            limpio = cleaner.limpiar(raw, tono, ctx["tiene_emojis"])
            if not limpio:
                # Reintentar con temperatura más alta
                resp2 = self._post("/generate", {
                    "mensaje":      mensaje,
                    "prompt_dipl":  prompt_dipl if tono == "diplomatico" else "",
                    "prompt_ejec":  prompt_ejec if tono == "ejecutivo"   else "",
                    "prompt_casu":  prompt_casu if tono == "casual"      else "",
                    "n_palabras":   ctx["palabras"],
                    "lon_clase":    pre["longitud_clase"],
                    "tiene_emojis": ctx["tiene_emojis"],
                })
                raw    = resp2.get(tono, "")
                limpio = cleaner.limpiar(raw, tono, ctx["tiene_emojis"])
            resultados[tono] = limpio or "No se pudo generar. Intenta con un mensaje más detallado."

        # ── Preview (traducción del mensaje original) ─────────
        prev_resp = self._post("/preview", {
            "mensaje":       mensaje,
            "idioma_origen": idioma_origen,
        })
        preview = prev_resp.get("preview", "")

        return {
            "diplomatico": resultados["diplomatico"],
            "ejecutivo":   resultados["ejecutivo"],
            "casual":      resultados["casual"],
            "textos_es": {
                "dipl": resultados["diplomatico"],
                "ejec": resultados["ejecutivo"],
                "casu": resultados["casual"],
            },
            "detector":   det,
            "preview":    preview,
            "tips":       tips,
            "tipo":       ctx["tipo"],
            "tono":       ctx["tono_emocional"],
            "intensidad": ctx["intensidad"],
        }

    # ── Traducción ────────────────────────────────────────────

    def traducir(self, textos_es: dict, idioma: str) -> tuple:
        if idioma == "es":
            return (
                textos_es.get("dipl", ""),
                textos_es.get("ejec", ""),
                textos_es.get("casu", ""),
            )

        resp = self._post("/translate", {
            "textos_es": textos_es,
            "idioma":    idioma,
        })

        return (
            resp.get("dipl", textos_es.get("dipl", "")),
            resp.get("ejec", textos_es.get("ejec", "")),
            resp.get("casu", textos_es.get("casu", "")),
        )

    # ── Tips LLM ─────────────────────────────────────────────

    def generar_tips_llm(self, mensaje: str) -> list:
        try:
            pre = PreProcesador().analizar(mensaje)
            ctx = RoleMatrix().analizar(mensaje, pre)

            resp = self._post("/tips", {
                "mensaje": mensaje,
                "tono":    ctx.get("tono_emocional", "neutro"),
                "tipo":    ctx.get("tipo", "general"),
            })

            tips = resp.get("tips", [])

            # Validar estructura
            resultado = []
            for tip in tips[:1]:
                if isinstance(tip, dict) and all(k in tip for k in ("icono", "titulo", "texto")):
                    resultado.append({
                        "icono":  str(tip["icono"])[:4],
                        "titulo": str(tip["titulo"])[:80],
                        "texto":  str(tip["texto"])[:160],
                    })
            return resultado

        except Exception as e:
            print(f"[tips_llm] Error: {e}")
            return []