"""
model.py — MessageToneAgent
Configuración para CPU + GPU Intel Iris Xe (sin CUDA, sin bitsandbytes).

Estrategia:
- Se carga el modelo en float32 / bfloat16 usando device_map="auto"
  para que accelerate reparta capas entre RAM y la memoria compartida
  de la GPU Intel automáticamente.
- Se usa torch.bfloat16 porque Intel Iris Xe soporta bfloat16 nativo
  vía PyTorch CPU/XPU, lo que reduce el consumo de RAM a ~8 GB.
- Sin cuantización NF4 (requiere CUDA/NVIDIA).
- Se habilita torch.compile() si está disponible para acelerar inferencia.
"""

import os
import re
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)
from processing import (
    GateKeeper, DetectorIdioma, AsesorEmocional,
    PreProcesador, IntentExtractor, RoleMatrix,
    PromptBuilder, OutputCleaner,
)


def _get_dtype_and_device():
    """
    Determina el dtype y device_map óptimos según el hardware disponible.

    - Si hay GPU NVIDIA (CUDA): float16 + device_map auto
    - Si hay GPU Intel (XPU):   bfloat16 + device_map auto
    - CPU pura:                 bfloat16 (más rápido que float32 en CPUs modernas)
    """
    if torch.cuda.is_available():
        print("🟢 CUDA detectado — usando float16 en GPU NVIDIA")
        return torch.float16, "auto"

    # Intel XPU (Arc, Iris Xe) vía torch-xpu o ipex
    try:
        import intel_extension_for_pytorch as ipex  # noqa: F401
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            print("🔵 Intel XPU detectado — usando bfloat16 + IPEX")
            return torch.bfloat16, "xpu"
    except ImportError:
        pass

    # CPU con bfloat16 (Intel Core 12th gen+ lo soporta nativamente)
    print("⚪ Sin GPU dedicada — usando CPU con bfloat16 + device_map auto")
    return torch.bfloat16, "auto"


class MessageToneAgent:
    MODEL_ID = "google/gemma-3-4b-it"

    def __init__(self):
        self.dtype, device_map = _get_dtype_and_device()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Moodify | dtype: {self.dtype} | device_map: {device_map}")

        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("❌ HF_TOKEN no encontrado en variables de entorno")

        # ── Tokenizer ────────────────────────────────────────
        print("📦 Cargando tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.MODEL_ID,
            token=hf_token,
            padding_side="left",
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        # ── Modelo sin cuantización ──────────────────────────
        # device_map="auto" reparte capas entre CPU y cualquier
        # acelerador disponible (GPU Intel via shared memory).
        print("📦 Cargando modelo en bfloat16 (sin cuantización)...")
        print("   Esto puede tardar 2-5 minutos la primera vez...")

        load_kwargs = dict(
            token=hf_token,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,   # carga capa por capa, evita pico de RAM doble
        )

        # device_map="auto" usa accelerate para repartir capas
        # entre CPU RAM y GPU shared memory automáticamente.
        # Si tienes 31 GB de RAM puedes cargar todo el modelo (~8 GB en bf16).
        if device_map == "auto":
            load_kwargs["device_map"] = "auto"
        elif device_map == "xpu":
            # Intel XPU: cargar en CPU primero, mover a XPU
            load_kwargs["device_map"] = "cpu"

        self.model = AutoModelForCausalLM.from_pretrained(
            self.MODEL_ID,
            **load_kwargs,
        ).eval()

        # Mover a XPU si está disponible
        if device_map == "xpu":
            try:
                import intel_extension_for_pytorch as ipex
                self.model = ipex.optimize(self.model, dtype=self.dtype)
                self.model = self.model.to("xpu")
                self.device = "xpu"
                print("✅ Modelo movido a Intel XPU")
            except Exception as e:
                print(f"⚠️  No se pudo mover a XPU: {e} — usando CPU")
                self.device = "cpu"

        # torch.compile acelera ~20-40% en CPU Intel (requiere PyTorch 2.0+)
        if self.device == "cpu":
            try:
                print("⚡ Aplicando torch.compile para acelerar CPU...")
                self.model = torch.compile(
                    self.model,
                    mode="reduce-overhead",   # balance entre compilación y velocidad
                    backend="inductor",
                )
                print("✅ torch.compile aplicado")
            except Exception as e:
                print(f"⚠️  torch.compile no disponible: {e}")

        # Reporte de memoria
        ram_gb = torch.cuda.memory_allocated() / 1024**3 if torch.cuda.is_available() else 0
        print(f"✅ Modelo listo | RAM GPU: {ram_gb:.2f} GB (resto en RAM del sistema)")

        # ── Clases de procesamiento ───────────────────────────
        self.gate      = GateKeeper()
        self.pre_proc  = PreProcesador()
        self.extractor = IntentExtractor()
        self.roles     = RoleMatrix()
        self.builder   = PromptBuilder()
        self.cleaner   = OutputCleaner()

    # ── Generación interna ────────────────────────────────────

    def _get_model_device(self):
        """Obtiene el device real donde está el primer parámetro del modelo."""
        try:
            return next(self.model.parameters()).device
        except Exception:
            return torch.device(self.device)

    def _generar(self, prompt: str, n_palabras: int, temperatura=0.22, lon_clase="medio") -> str:
        if lon_clase == "muy_corto":
            temperatura = min(temperatura, 0.18)

        chat    = [{"role": "user", "content": prompt}]
        tp      = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        encoded = self.tokenizer(tp, return_tensors="pt", truncation=True, max_length=1024)

        # Mover inputs al device correcto
        model_device = self._get_model_device()
        inputs = {k: v.to(model_device) for k, v in encoded.items()
                  if k in ("input_ids", "attention_mask")}

        # Límites de tokens conservadores para no saturar RAM
        if lon_clase == "muy_corto":
            max_tok = min(50,  max(15,  int(n_palabras * 2.0)))
        elif lon_clase == "corto":
            max_tok = min(110, max(35,  int(n_palabras * 2.2)))
        else:
            max_tok = min(220, max(80,  int(n_palabras * 2.0)))

        with torch.inference_mode():
            out = self.model.generate(
                **inputs,
                max_new_tokens=max_tok,
                temperature=temperatura,
                top_p=0.88,
                top_k=35,
                do_sample=True,
                repetition_penalty=1.07,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                use_cache=True,
            )

        if hasattr(out, "sequences"):
            out = out.sequences
        if out is None or len(out) == 0:
            return ""
        gen = out[0][inputs["input_ids"].shape[-1]:]
        return self.tokenizer.decode(gen, skip_special_tokens=True).strip()

    # ── Traducción ────────────────────────────────────────────

    def traducir(self, textos_es: dict, idioma_destino: str) -> tuple:
        if idioma_destino == "es":
            return textos_es.get("dipl", ""), textos_es.get("ejec", ""), textos_es.get("casu", "")

        model_device = self._get_model_device()
        traducciones = []
        for nombre_tono, texto in [("diplomatic", textos_es.get("dipl", "")),
                                    ("executive",  textos_es.get("ejec", "")),
                                    ("casual",     textos_es.get("casu", ""))]:
            if not texto or texto.startswith("No se pudo"):
                traducciones.append(texto)
                continue
            n_palabras = len(texto.split())
            max_tok    = min(280, max(40, int(n_palabras * 2.0)))
            prompt = (f"Translate the following professional workplace message from Spanish to English.\n"
                      f"Tone: {nombre_tono}. Preserve tone, register, and all specific data.\n"
                      f"Output ONLY the translated message.\n\n{texto}")
            chat    = [{"role": "user", "content": prompt}]
            tp      = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
            encoded = self.tokenizer(tp, return_tensors="pt", truncation=True, max_length=1024)
            inputs  = {k: v.to(model_device) for k, v in encoded.items()
                       if k in ("input_ids", "attention_mask")}
            with torch.inference_mode():
                out = self.model.generate(
                    **inputs, max_new_tokens=max_tok, temperature=0.15,
                    top_p=0.90, top_k=30, do_sample=True, repetition_penalty=1.05,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            if hasattr(out, "sequences"):
                out = out.sequences
            gen       = out[0][inputs["input_ids"].shape[-1]:]
            resultado = self.tokenizer.decode(gen, skip_special_tokens=True).strip()
            resultado = re.sub(r'^(?:here\s+(?:is|you\s+go)[^:]*:|translation\s*:|translated\s*:)\s*', '', resultado, flags=re.IGNORECASE).strip()
            if resultado and not resultado[0].isupper():
                resultado = resultado[0].upper() + resultado[1:]
            if resultado and not re.search(r'[.!?]$', resultado.rstrip()):
                resultado = resultado.rstrip() + '.'
            traducciones.append(resultado or texto)
        return tuple(traducciones)

    def _traducir_preview(self, mensaje: str, idioma_origen: str) -> str:
        model_device = self._get_model_device()
        prompt = ("Translate this workplace message from Spanish to English. Keep it natural. Output ONLY the translation:\n\n" + mensaje
                  if idioma_origen == "es"
                  else "Traduce este mensaje del inglés al español. Natural y profesional. ÚNICAMENTE la traducción:\n\n" + mensaje)
        chat    = [{"role": "user", "content": prompt}]
        tp      = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        encoded = self.tokenizer(tp, return_tensors="pt", truncation=True, max_length=512)
        inputs  = {k: v.to(model_device) for k, v in encoded.items()
                   if k in ("input_ids", "attention_mask")}
        max_tok = min(100, max(20, int(len(mensaje.split()) * 1.6)))
        with torch.inference_mode():
            out = self.model.generate(
                **inputs, max_new_tokens=max_tok, temperature=0.1,
                top_p=0.90, top_k=20, do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        if hasattr(out, "sequences"):
            out = out.sequences
        gen       = out[0][inputs["input_ids"].shape[-1]:]
        resultado = self.tokenizer.decode(gen, skip_special_tokens=True).strip()
        return re.sub(r'^(?:here\s+is[^:]*:|translation\s*:|traducción\s*:|aquí\s+(?:está|tienes)[^:]*:)\s*', '', resultado, flags=re.IGNORECASE).strip()

    # ── Pipeline principal ────────────────────────────────────

    def procesar(self, mensaje: str) -> dict:
        detector = DetectorIdioma()
        asesor   = AsesorEmocional()

        def _err(msg):
            return {"error": msg, "diplomatico": msg, "ejecutivo": msg, "casual": msg,
                    "detector": detector.detectar(""), "tips": [],
                    "tipo": "general", "tono": "neutro", "intensidad": "baja", "textos_es": {}}

        if not mensaje or not mensaje.strip():
            return _err("❌ El mensaje no puede estar vacío.")
        if len(mensaje.strip().split()) < 2:
            return _err("⚠️ Agrega al menos 2 palabras.")

        puede, motivo = GateKeeper().evaluar(mensaje)
        if not puede:
            fb = GateKeeper().mensaje_feedback(motivo)
            return _err(fb)

        pre     = PreProcesador().analizar(mensaje)
        intento = IntentExtractor().extraer(mensaje)
        ancla   = IntentExtractor().construir_ancla(intento)
        ctx     = RoleMatrix().analizar(mensaje, pre)
        det     = detector.detectar(mensaje)
        idioma_origen = "en" if det["idioma"] == "Inglés" else "es"

        preview = self._traducir_preview(mensaje, idioma_origen)
        tips    = asesor.generar(ctx, pre)

        resultados = {}
        for tono in ("diplomatico", "ejecutivo", "casual"):
            prompt = PromptBuilder().construir(mensaje, tono, ctx, pre, intento, ancla)
            raw    = self._generar(prompt, ctx["palabras"], lon_clase=pre["longitud_clase"])
            limpio = OutputCleaner().limpiar(raw, tono, ctx["tiene_emojis"])
            if not limpio:
                raw    = self._generar(prompt, ctx["palabras"], temperatura=0.28, lon_clase=pre["longitud_clase"])
                limpio = OutputCleaner().limpiar(raw, tono, ctx["tiene_emojis"])
            resultados[tono] = limpio or "No se pudo generar. Intenta con un mensaje más detallado."

        return {
            "diplomatico": resultados["diplomatico"],
            "ejecutivo":   resultados["ejecutivo"],
            "casual":      resultados["casual"],
            "textos_es": {
                "dipl": resultados["diplomatico"],
                "ejec": resultados["ejecutivo"],
                "casu": resultados["casual"],
            },
            "detector":    det,
            "preview":     preview,
            "tips":        tips,
            "tipo":        ctx["tipo"],
            "tono":        ctx["tono_emocional"],
            "intensidad":  ctx["intensidad"],
        }
    def generar_tips_llm(self, mensaje: str) -> list:
        """
        Genera tips contextuales + humor usando el LLM.
        Se llama en paralelo con procesar() desde main.py.
        Devuelve lista de dicts con icono, titulo, texto.
        En caso de error devuelve lista vacía (el frontend
        ya tiene fallback con los tips rule-based).
        """
        try:
            pre = PreProcesador().analizar(mensaje)
            ctx = RoleMatrix().analizar(mensaje, pre)
            tono    = ctx.get("tono_emocional", "neutro")
            tipo    = ctx.get("tipo", "general")
            groserías = pre.get("tiene_groserías", False)

            prompt = (
                "Eres Moodi, un asistente de comunicación laboral mexicano. "
                "Tienes personalidad: eres directo, empático y con humor sutil. "
                "Analiza el siguiente mensaje y genera exactamente 3 items en JSON.\n\n"
                f"Mensaje: \"{mensaje[:300]}\"\n"
                f"Tono emocional detectado: {tono}\n"
                f"Tipo de mensaje: {tipo}\n"
                f"Tiene groserías: {groserías}\n\n"
                "Reglas:\n"
                "- Item 1: consejo sobre el tono o impacto del mensaje\n"
                "- Item 2: consejo práctico de redacción\n"
                "- Item 3: un chiste o comentario con humor ligero relacionado al mensaje o tono\n"
                "- Usa iconos: 🔴 para urgente/alerta, 🟡 para precaución, ✅ para positivo, 💡 para consejo, 😄 para humor\n"
                "- Máximo 20 palabras en 'titulo', máximo 35 palabras en 'texto'\n"
                "- Responde ÚNICAMENTE con un array JSON válido, sin texto adicional, sin markdown:\n"
                "[{\"icono\":\"💡\",\"titulo\":\"...\",\"texto\":\"...\"},...]"
            )

            model_device = self._get_model_device()
            chat    = [{"role": "user", "content": prompt}]
            tp      = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
            encoded = self.tokenizer(tp, return_tensors="pt", truncation=True, max_length=768)
            inputs  = {k: v.to(model_device) for k, v in encoded.items()
                       if k in ("input_ids", "attention_mask")}

            with torch.inference_mode():
                out = self.model.generate(
                    **inputs,
                    max_new_tokens=180,
                    temperature=0.55,
                    top_p=0.90,
                    top_k=40,
                    do_sample=True,
                    repetition_penalty=1.05,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,
                )

            if hasattr(out, "sequences"):
                out = out.sequences
            gen = out[0][inputs["input_ids"].shape[-1]:]
            raw = self.tokenizer.decode(gen, skip_special_tokens=True).strip()

            # Limpiar y parsear JSON
            import re, json
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if not match:
                return []
            tips = json.loads(match.group(0))

            # Validar estructura
            resultado = []
            for tip in tips[:3]:
                if isinstance(tip, dict) and "icono" in tip and "titulo" in tip and "texto" in tip:
                    resultado.append({
                        "icono":  str(tip["icono"])[:4],
                        "titulo": str(tip["titulo"])[:80],
                        "texto":  str(tip["texto"])[:160],
                    })
            return resultado

        except Exception as e:
            print(f"[tips_llm] Error: {e}")
            return []