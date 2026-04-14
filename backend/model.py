"""
model.py — MessageToneAgent
Cuantización NF4 corregida para mantenerse bajo ~4.5 GB de VRAM.

Problemas que causaban el consumo de ~7 GB en Colab:
1. bfloat16 en compute_dtype sube el consumo vs float16.
2. Sin bnb_4bit_use_double_quant=True se pierde ~0.5 GB.
3. device_map="auto" con un solo GPU a veces carga algunas capas en fp32.
4. El tokenizer cargaba tensores en CPU y luego los movía, duplicando picos.
5. max_new_tokens muy altos reservan memoria KV-cache innecesaria.
Correcciones aplicadas abajo.
"""

import os
import re
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)
from processing import (
    GateKeeper, DetectorIdioma, AsesorEmocional,
    PreProcesador, IntentExtractor, RoleMatrix,
    PromptBuilder, OutputCleaner,
)


def _build_bnb_config() -> BitsAndBytesConfig:
    """
    Configuración BitsAndBytes optimizada para < 4.5 GB VRAM.

    Cambios clave vs la versión original de Colab:
    - compute_dtype = float16   (bfloat16 usa más VRAM en Ampere y anterior)
    - double_quant  = True      (cuantiza también las constantes de escala: -~0.4 GB)
    - quant_type    = "nf4"     (sin cambio, ya era correcto)
    """
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,      # ← float16, no bfloat16
        bnb_4bit_use_double_quant=True,            # ← reduce ~0.4 GB extra
    )


class MessageToneAgent:
    MODEL_ID = "google/gemma-3-4b-it"

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Moodify | Dispositivo: {self.device}")

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

        # ── Modelo con cuantización corregida ────────────────
        print("📦 Cargando modelo con cuantización NF4 optimizada...")
        bnb = _build_bnb_config()

        # device_map="cuda:0" fuerza todo a la misma GPU y evita que
        # transformers reparta capas entre GPU+CPU (lo que infla el uso).
        # Si no hay GPU usa device_map="auto" normalmente.
        device_map = {"": 0} if self.device == "cuda" else "auto"

        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_ID,
                quantization_config=bnb,
                device_map=device_map,
                token=hf_token,
                attn_implementation="flash_attention_2",
                torch_dtype=torch.float16,            # ← consistente con compute_dtype
            ).eval()
        except Exception:
            # Fallback sin flash attention (GPUs antiguas)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_ID,
                quantization_config=bnb,
                device_map=device_map,
                token=hf_token,
                torch_dtype=torch.float16,
            ).eval()

        # Libera la caché CUDA después de cargar
        if self.device == "cuda":
            torch.cuda.empty_cache()
            vram_gb = torch.cuda.memory_allocated() / 1024 ** 3
            print(f"✅ Modelo listo | VRAM usada: {vram_gb:.2f} GB")
        else:
            print("✅ Modelo listo (CPU)")

        # ── Clases de procesamiento ───────────────────────────
        self.gate      = GateKeeper()
        self.pre_proc  = PreProcesador()
        self.extractor = IntentExtractor()
        self.roles     = RoleMatrix()
        self.builder   = PromptBuilder()
        self.cleaner   = OutputCleaner()

    # ── Generación interna ────────────────────────────────────

    def _generar(self, prompt: str, n_palabras: int, temperatura=0.22, lon_clase="medio") -> str:
        if lon_clase == "muy_corto":
            temperatura = min(temperatura, 0.18)

        chat = [{"role": "user", "content": prompt}]
        tp   = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        encoded = self.tokenizer(tp, return_tensors="pt", truncation=True, max_length=1024)
        inputs  = {k: v.to(self.model.device) for k, v in encoded.items() if k in ("input_ids", "attention_mask")}

        # max_new_tokens acotados: el KV-cache reserva memoria proporcional
        if lon_clase == "muy_corto":
            max_tok = min(50,  max(15,  int(n_palabras * 2.0)))
        elif lon_clase == "corto":
            max_tok = min(110, max(35,  int(n_palabras * 2.2)))
        else:
            max_tok = min(240, max(80,  int(n_palabras * 2.2)))   # ← bajado de 280 a 240

        with torch.inference_mode():                               # ← inference_mode en lugar de no_grad (más eficiente)
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
            inputs  = {k: v.to(self.model.device) for k, v in encoded.items() if k in ("input_ids", "attention_mask")}
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
        prompt = ("Translate this workplace message from Spanish to English. Keep it natural. Output ONLY the translation:\n\n" + mensaje
                  if idioma_origen == "es"
                  else "Traduce este mensaje del inglés al español. Natural y profesional. ÚNICAMENTE la traducción:\n\n" + mensaje)
        chat    = [{"role": "user", "content": prompt}]
        tp      = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        encoded = self.tokenizer(tp, return_tensors="pt", truncation=True, max_length=512)
        inputs  = {k: v.to(self.model.device) for k, v in encoded.items() if k in ("input_ids", "attention_mask")}
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

        # Libera caché entre requests
        if self.device == "cuda":
            torch.cuda.empty_cache()

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