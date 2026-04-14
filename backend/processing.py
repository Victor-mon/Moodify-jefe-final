import re


class GateKeeper:
    _REACCION_PURA = re.compile(
        r'^[\s]*(?:(?:ja){2,}h?|(?:je){2,}|(?:ji){2,}|(?:jo){2,}|'
        r'x\s*d+|XD+|lol+|lmao+|lmfao|rofl|omg|wtf|ajaj+|kek+|hah+a*|heh+|'
        r':\)+|:\(+|:D+|;\)+|uwu+|owo+|:v|v:|[😂🤣😭😅😆😄😁🙂😐😑😶]+\s*'
        r')[\s!.?,]*$', re.IGNORECASE)
    _PREGUNTA_REACCION = re.compile(
        r'^[\s]*(?:(?:en\s+)?serio\s*[?!]+|neta\s*[?!]+|n[e3]ta[?!]*|'
        r'(?:de\s+)?verdad\s*[?!]+|no\s+(?:manch[e]s?|mam[e]s?)\s*[?!]*|'
        r'(?:a\s+)?(?:poco|cuál?|qué)\s*[?!]+|wh?[ao]t\s*[?!]*|'
        r'¿?\s*(?:en\s+serio|de\s+verdad|neta|qué|cómo)\s*[?!]+)[\s]*$', re.IGNORECASE)
    _FRASE_INCOMPLETA = re.compile(
        r'^[\s]*(?:o\s*sea\b[^.!?]{0,30}\.{2,}|o\s*sea\b[\s]*$|'
        r'pues+[\s]*\.{2,}|este+[\s]*\.{2,}|(?:mm+|hm+|eh+|ah+|uh+)[\s]*[.!?]*$|'
        r'(?:bueno|mira|oye)[\s]*\.{3,}$)[\s]*$', re.IGNORECASE)
    _PALABRA_SOLA = re.compile(
        r'^[\s]*(?:hola|adios|adiós|bye|ok|sí|si|no|ya|dale|listo|'
        r'perfecto|sale|va|bueno|claro|gracias|thanks|np|ntp|de\s+nada)[\s!.?]*$', re.IGNORECASE)
    _DATO_SUELTO  = re.compile(r'^[\s]*(?:\d[\d\s:/\-.,]{0,20}|https?://\S+|www\.\S+)[\s]*$')
    _SEÑAL_LABORAL = re.compile(
        r'\b(?:necesito|solicito|pido|quiero\s+(?:pedir|solicitar|informar)|'
        r'informo|comunico|reporto|aviso|notifico|escalo|proyecto|reporte|'
        r'reunión|junta|entrega|cliente|proveedor|fecha|plazo|pendiente|'
        r'presupuesto|propuesta|equipo|área|departamento|oficina|empresa|trabajo|'
        r'hay\s+que|se\s+requiere|es\s+necesario|favor\s+de|podría[s]?|podrían|'
        r'les\s+(?:pido|comento|informo|aviso)|buenos\s+(?:días|tardes|noches)\s+\w|'
        r'estimad[ao]s?|a\s+quien\s+corresponda|permiso|vacaciones|incapacidad|'
        r'sistema|acceso|registro|aplicación|plataforma|actualiz|versión|manual|'
        r'procedimiento|norma|ISO)\b', re.IGNORECASE)

    def evaluar(self, m):
        m = m.strip()
        if self._REACCION_PURA.match(m):      return False, "reaccion"
        if self._PREGUNTA_REACCION.match(m):  return False, "pregunta_reaccion"
        if self._FRASE_INCOMPLETA.match(m):   return False, "incompleto"
        if self._PALABRA_SOLA.match(m):       return False, "palabra_sola"
        if self._DATO_SUELTO.match(m):        return False, "dato_suelto"
        if self._SEÑAL_LABORAL.search(m):     return True,  ""
        if len(m.split()) <= 3:               return False, "muy_corto_sin_contexto"
        return True, ""

    def mensaje_feedback(self, motivo):
        return {
            "reaccion":               "Este mensaje es una reacción, no un mensaje laboral.",
            "pregunta_reaccion":      "Parece una reacción de sorpresa. Incluye el mensaje completo.",
            "incompleto":             "El mensaje parece incompleto. Escribe el mensaje completo.",
            "palabra_sola":           "Una sola palabra no tiene contexto. Escribe el mensaje completo.",
            "dato_suelto":            "Solo hay un dato suelto. Inclúyelo dentro de un mensaje.",
            "muy_corto_sin_contexto": "Muy corto sin contexto laboral. ¿Qué quieres comunicar y a quién?",
        }.get(motivo, "No se detectó intención laboral. Escribe el mensaje completo.")


class DetectorIdioma:
    _ES = re.compile(
        r'\b(?:que|de|en|es|una?|por|con|para|como|pero|todo|más|también|cuando|'
        r'donde|esto|eso|aquí|ahí|hay|muy|bien|ahora|ya|si|no|los|las|del|al|le|'
        r'les|se|me|te|nos|su|sus|mi|mis|tu|tus|tengo|tenemos|tiene|quiero|quería|'
        r'necesito|solicito|pido|informo|comunico|hola|buenas|gracias|favor|día|días|'
        r'semana|junta|reunión|equipo|trabajo|empresa|área|proyecto|reporte|porque|'
        r'aunque|además|entonces|así|siguiente|próximo|anterior|wey|güey|bro|papu|'
        r'cuate|mano|compa|carnal)\b', re.IGNORECASE)
    _EN = re.compile(
        r'\b(?:the|and|for|are|but|not|you|all|can|her|was|one|our|out|day|get|'
        r'has|him|his|how|its|may|new|now|old|see|two|who|will|with|from|they|'
        r'this|that|have|been|said|each|she|which|their|there|were|your|what|'
        r'when|would|about|could|please|thanks|hello|meeting|team|update|feedback|'
        r'deadline|regarding|attached|kindly|schedule|review|report|project)\b', re.IGNORECASE)
    _ES_FUERTE = re.compile(
        r'[áéíóúüñÁÉÍÓÚÜÑ]|¿|¡|\b(?:estimad[ao]s?|saludos|atentamente|mediante|'
        r'adjunto|conforme|asimismo|sin embargo|no obstante)\b', re.IGNORECASE)

    def detectar(self, mensaje):
        if not mensaje or not mensaje.strip():
            return {"idioma": "desconocido", "emoji": "🌐", "confianza": 0, "advertencia": ""}
        m  = mensaje.strip()
        tw = max(len(m.split()), 1)
        hits_es = len(self._ES.findall(m)) + len(self._ES_FUERTE.findall(m)) * 2
        hits_en = len(self._EN.findall(m))
        score_es = hits_es / tw
        score_en = hits_en / tw
        if score_es == 0 and score_en == 0:
            return {"idioma": "desconocido", "emoji": "🌐", "confianza": 0, "advertencia": ""}
        elif score_es >= score_en * 1.5:
            return {"idioma": "Español",  "emoji": "🇲🇽", "confianza": min(100, int(score_es / max(score_es + score_en, 0.01) * 100)), "advertencia": ""}
        elif score_en >= score_es * 1.5:
            return {"idioma": "Inglés",   "emoji": "🇺🇸", "confianza": min(100, int(score_en / max(score_es + score_en, 0.01) * 100)), "advertencia": "⚠️ Moodify está optimizado para español."}
        else:
            return {"idioma": "Mixto (Spanglish)", "emoji": "🌐", "confianza": 50, "advertencia": "⚠️ Mensaje mezclado."}


class AsesorEmocional:
    def generar(self, ctx, pre):
        tips       = []
        tono       = ctx["tono_emocional"]
        intensidad = ctx["intensidad"]
        groserías  = pre["tiene_groserías"]
        slang      = pre["tiene_slang"]
        urgencia   = pre["urgencia_impl"]
        tipo       = ctx["tipo"]
        receptor   = ctx["receptor"]

        if groserías:
            tips.append({"icono": "🔴", "titulo": "Vaya, alguien está de malas",
                "texto": "Noto algo de... energía en tu mensaje 😅. Respira hondo — los mensajes enviados en caliente suelen crear más problemas. La versión diplomática dice lo mismo pero sin el karma."})
            tips.append({"icono": "💡", "titulo": "Mi recomendación: ve por el diplomático",
                "texto": "El tono diplomático es como un abogado silencioso: firme, claro y sin que nadie pueda usarlo en tu contra."})
        elif tono == "frustracion" and intensidad == "alta":
            tips.append({"icono": "🟡", "titulo": "Se nota la frustración — y está bien",
                "texto": "Antes de enviarlo, pregúntate: ¿quieres que entiendan cómo te sientes, o quieres que resuelvan el problema? Si es lo segundo, el ejecutivo es tu mejor aliado."})
        elif tono == "frustracion" and intensidad == "media":
            tips.append({"icono": "🟡", "titulo": "Hay un poco de tensión aquí",
                "texto": "Nombrarlo directamente suele funcionar mucho mejor que insinuarlo."})
        if urgencia or tono == "urgencia":
            tips.append({"icono": "⏰", "titulo": "Esto va contra el reloj",
                "texto": "Asegúrate de que el plazo o la acción requerida estén MUY explícitos. Ponlo en la primera oración."})
        if tipo == "solicitud" and not groserías:
            tips.append({"icono": "🤝", "titulo": "Es una solicitud — juega bien tus cartas",
                "texto": "El tono diplomático aquí es clave. Un 'agradecería' pesa más que un 'necesito'." if receptor == "singular_formal" else "Para pedirle algo a alguien, el tono diplomático generalmente tiene mejor recepción."})
        if slang and not groserías and not tips:
            tips.append({"icono": "💬", "titulo": "Muy coloquial para el contexto",
                "texto": "Si va a un jefe o cliente, te recomiendo la versión ejecutiva o diplomática."})
        if tono == "positivo" and not tips:
            tips.append({"icono": "✅", "titulo": "Buenas vibras, buen momento para comunicar",
                "texto": "El tono casual puede sonar más genuino aquí, aunque el diplomático nunca falla."})
        if not tips:
            tips.append({"icono": "✅", "titulo": "Mensaje neutral y equilibrado",
                "texto": "Elige el tono según tu relación: casual para confianza, diplomático para formalidad, ejecutivo cuando el tiempo del otro vale más."})
        return tips[:3]


class PreProcesador:
    _GROSERÍAS = re.compile(
        r'\b(ch[i1]ng[a4o]|p[i1]nch[e3]|c[a4]br[o0][n3]|p[u4]t[a4]|v[e3]rg[a4]|'
        r'p[e3]nd[e3][j1][o0]|m[a4]m[e3][s5]|m[a4]nch[e3][s5]|c[a4]r[a4][j1][o0]|'
        r'p[u4]t[a4]\s*m[a4]dr[e3])\b', re.IGNORECASE)
    _SLANG   = re.compile(r'\b(pa\b|bro\b|papu\b|jefa?\b|wey\b|wuey\b|güey\b|compa\b|mano\b|carnal\b|cuate\b|morro\b)\b', re.IGNORECASE)
    _URGENCIA = re.compile(r'\b(ya\s+no\s+(?:puedo|aguanto)|necesito\s+(?:ya|urgente|ahorita)|lo\s+antes\s+posible|cuanto\s+antes|no\s+(?:manch|mam)[e]s)\b', re.IGNORECASE)

    def analizar(self, mensaje):
        n = len(mensaje.strip().split())
        return {
            "tiene_groserías": bool(self._GROSERÍAS.search(mensaje)),
            "tiene_slang":     bool(self._SLANG.search(mensaje)),
            "urgencia_impl":   bool(self._URGENCIA.search(mensaje)),
            "carga_emocional": "alta" if self._GROSERÍAS.search(mensaje) else "normal",
            "longitud_clase":  "muy_corto" if n <= 5 else "corto" if n <= 12 else "medio" if n <= 30 else "largo",
            "n_palabras":      n,
        }


class IntentExtractor:
    _NUMEROS = re.compile(r'\b\d[\d,./\-]*\b')
    _FECHAS  = re.compile(r'\b(?:hoy|mañana|ayer|(?:este|próximo|el)\s+\w+|\d{1,2}\s+de\s+\w+|semana\s+(?:que\s+entra|pasada|esta))\b', re.I)
    _HORAS   = re.compile(r'\d{1,2}(?::\d{2})?\s*(?:am|pm|hrs?|h)\b', re.I)
    _MONTOS  = re.compile(r'\$\s*\d[\d,.\s]*(?:MXN|USD|pesos|dólares)?\b', re.I)
    _OBJETOS = re.compile(r'\b(?:vacaciones|reporte[s]?|horario|tareas?|proyecto|permiso|solicitud|sistema|aplicaci[oó]n|registro|acceso|entrega|propuesta|presupuesto|reunión|junta|oficina|resultados?|actividades?|manual|norma|ISO|lineamientos?|cumplimiento|versión|presentación)\b', re.I)
    _VERBO   = re.compile(r'\b(?:necesito|solicito|pido|quiero|debo|hay\s+que|informo|comunico|reporto|escalo|avisar?|notificar?|podemos|pueden|vamos\s+a|se\s+requiere|he\s+\w+do|comparto|estaré|enviando)\b', re.I)
    _CAUSA   = re.compile(r'\b(?:porque|por(?:que)?\s+(?:la|el|las|los|su)|debido\s+a|ya\s+que|dado\s+que|a\s+causa\s+de)\b', re.I)
    _CONSEC  = re.compile(r'\b(?:por\s+(?:eso|lo\s+tanto)|entonces|así\s+que|por\s+lo\s+que)\b', re.I)
    _AREAS   = re.compile(r'\b(?:recursos\s+humanos|RH\b|RRHH\b|HR\b|marketing|ventas|comercial|sistemas?|TI\b|IT\b|tecnolog[ií]a|infraestructura|desarrollo|contabilidad|finanzas|administraci[oó]n|tesorería|operaciones?|log[ií]stica|almacén|producci[oó]n|legal|jurídico|compliance|direcci[oó]n|gerencia|soporte|helpdesk|mesa\s+de\s+ayuda|compras|adquisiciones|proveedores|calidad|QA\b|auditoría|atenci[oó]n\s+a\s+clientes?)\b', re.IGNORECASE)
    _SALUDO  = re.compile(r'^(?P<saludo>(?:hola|oye|buenos?\s+(?:días|tardes|noches)|estimad[ao]s?|querido[s]?|buen\s+día)\s*[,:]?\s*(?P<nombre>[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]{2,}(?:\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]{2,})?)?)', re.IGNORECASE | re.UNICODE)

    def extraer(self, mensaje):
        saludo_m = self._SALUDO.match(mensaje.strip())
        return {
            "numeros":        self._NUMEROS.findall(mensaje),
            "fechas":         self._FECHAS.findall(mensaje),
            "horas":          self._HORAS.findall(mensaje),
            "montos":         self._MONTOS.findall(mensaje),
            "objetos":        self._OBJETOS.findall(mensaje),
            "verbo_clave":    self._VERBO.findall(mensaje),
            "tiene_causa":    bool(self._CAUSA.search(mensaje)),
            "tiene_consec":   bool(self._CONSEC.search(mensaje)),
            "personas":       [],
            "empresas":       [],
            "areas":          list(dict.fromkeys(m.group(0) for m in self._AREAS.finditer(mensaje)))[:3],
            "saludo_apertura": saludo_m.group("saludo").strip() if saludo_m else None,
            "nombre_saludo":   saludo_m.group("nombre").strip() if (saludo_m and saludo_m.group("nombre")) else None,
        }

    def construir_ancla(self, intento):
        partes = []
        if intento["numeros"]: partes.append(f"números exactos: {', '.join(intento['numeros'][:4])}")
        if intento["fechas"]:  partes.append(f"referencias de tiempo: {', '.join(intento['fechas'][:3])}")
        if intento["horas"]:   partes.append(f"horas exactas: {', '.join(intento['horas'][:3])}")
        if intento["montos"]:  partes.append(f"montos exactos: {', '.join(intento['montos'][:3])}")
        if intento["objetos"]: partes.append(f"tema central: {', '.join(set(intento['objetos'][:3]))}")
        if intento["areas"]:   partes.append(f"áreas de trabajo: {', '.join(intento['areas'][:3])}")
        if intento.get("saludo_apertura"): partes.append(f"SALUDO DE APERTURA: '{intento['saludo_apertura']}' — adaptar al tono")
        if intento["verbo_clave"]:         partes.append(f"acción principal: {intento['verbo_clave'][0]}")
        if intento["tiene_causa"] and intento["tiene_consec"]: partes.append("estructura: causa → consecuencia (NO invertir)")
        elif intento["tiene_causa"]: partes.append("hay una causa explícita (NO eliminar)")
        return "\n".join(f"  · {p}" for p in partes) if partes else "  · Preservar significado literal completo"


class RoleMatrix:
    _SC_PLURAL_EMI  = [(r'\b(nosotros|nuestro[as]?)\b', 12), (r'\b(tenemos|estamos|debemos|haremos)\b', 9), (r'\b(informamos|comunicamos|avisamos|solicitamos)\b', 10), (r'\b(confirmamos|queremos|necesitamos|podemos)\b', 8), (r'\bnos\b', 5)]
    _SC_YO          = [(r'\byo\b', 14), (r'\bhe\s+(?:recibido|enviado|visto|hecho|tenido)\b', 13), (r'\bme\s+(?:gustar[ií]a|interesa|parece|urge)\b', 11), (r'\b(mi|mis)\b', 5), (r'\bme\b', 4), (r'\b(necesito|quiero|tengo|estoy)\b', 9), (r'\b(pido|solicito|creo|hice)\b', 9)]
    _SC_PLURAL_REC  = [(r'\b(ustedes|todos|tod[ao]s)\b', 14), (r'\b(les\b)', 9), (r'\b(equipo|compañer[oa]s|colegas|personal)\b', 9), (r'\b(pueden|tienen|deben|hagan|revisen)\b', 8)]
    _SC_SING_FORMAL = [(r'\busted\b', 16), (r'\bsu\s+(?:apoyo|respuesta|atención)\b', 8), (r'\b(estimad[ao]|le\s+(?:comento|informo|solicito))\b', 10)]
    _SC_SING_INF    = [(r'\btú\b', 14), (r'\bte\b', 7), (r'\btu\b', 6), (r'\b(puedes|tienes|debes|podrías)\b', 9), (r'\b(bro|papu|jefa?|wey|mano|compa)\b', 7)]
    _TIPO_PATS = [
        ("pregunta",   re.compile(r'\?|¿', re.I)),
        ("queja",      re.compile(r'\b(harto|frustrad|cansad|no\s+puede\s+ser|molest)\b', re.I)),
        ("solicitud",  re.compile(r'\b(quisiera|solicito|pido|permiso|podría[s]?|me\s+gustaría|vacaciones|necesito\s+que)\b', re.I)),
        ("comunicado", re.compile(r'\b(informamos|comunicamos|avisamos|notificamos)\b', re.I)),
        ("reporte",    re.compile(r'\b(el\s+cliente|el\s+sistema|no\s+ha\s+llegado|lleva.{1,20}sin)\b', re.I)),
        ("aviso",      re.compile(r'\b(importante|recordar|avisar|tomar\s+en\s+cuenta|es\s+necesario\s+que)\b', re.I)),
    ]
    _TONO_PATS = {
        "frustracion": re.compile(r'\b(harto|frustrad|cansad|ya\s+no|nunca|siempre|pinche|ch[i]ng[ao]|p[u]ta|no\s+manch[e]s|increíble|colmo|ridículo|asco)\b', re.I),
        "urgencia":    re.compile(r'\b(urgente|ahorita|ya|ahora|inmediato|cuanto\s+antes|hoy\s+mismo|pronto)\b', re.I),
        "positivo":    re.compile(r'\b(excelente|logr|ganamos|cerramos|felicit|gracias|feliz|contento|orgullos|buenas\s+noticias|éxito)\b', re.I),
    }

    def analizar(self, mensaje, pre):
        m  = mensaje.strip()
        ml = m.lower()
        sc_nos = sum(p for pat, p in self._SC_PLURAL_EMI  if re.search(pat, ml))
        sc_yo  = sum(p for pat, p in self._SC_YO          if re.search(pat, ml)) + (3 if pre["tiene_slang"] else 0)
        emisor = "nosotros" if (sc_nos >= 8 and sc_nos > sc_yo * 1.25) else ("yo" if sc_yo >= 5 else ("nosotros" if sc_nos >= 8 else "indeterminado"))
        sc_pl   = sum(p for pat, p in self._SC_PLURAL_REC  if re.search(pat, ml))
        sc_sgfo = sum(p for pat, p in self._SC_SING_FORMAL if re.search(pat, ml))
        sc_sgin = sum(p for pat, p in self._SC_SING_INF    if re.search(pat, ml))
        sc_sg   = sc_sgfo + sc_sgin
        receptor = "plural" if (sc_pl > sc_sg and sc_pl >= 5) else \
                   ("singular_formal" if (sc_sg > sc_pl and sc_sg >= 4 and sc_sgfo > sc_sgin) else \
                   ("singular_informal" if (sc_sg > sc_pl and sc_sg >= 4) else "indeterminado"))
        tipo = "general"
        for t, pat in self._TIPO_PATS:
            if pat.search(m):
                tipo = t
                break
        if emisor == "nosotros" and re.search(r'\b(informamos|comunicamos|avisamos)\b', ml): tipo = "comunicado"
        elif emisor == "yo" and re.search(r'\b(solicito|pido|quisiera|permiso|vacaciones)\b', ml):  tipo = "solicitud"
        scores = {k: len(v.findall(m)) for k, v in self._TONO_PATS.items()}
        scores["frustracion"] += 2 if pre["tiene_groserías"] else 0
        tono_em   = "frustracion" if scores["frustracion"] >= 1 else ("urgencia" if scores["urgencia"] >= 2 else ("positivo" if scores["positivo"] >= 2 else "neutro"))
        intensidad = "alta" if (scores["frustracion"] >= 2 or pre["tiene_groserías"]) else ("media" if scores["frustracion"] == 1 else "baja")
        _EMJ = re.compile("[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001FA00-\U0001FAFF]+", re.UNICODE)
        return {
            "emisor":             emisor,
            "receptor":           receptor,
            "tipo":               tipo,
            "tono_emocional":     tono_em,
            "intensidad":         intensidad,
            "nombre_dest":        None,
            "tiene_emojis":       bool(_EMJ.search(m)),
            "palabras":           len(m.split()),
            "registro_receptor":  "formal" if sc_sgfo > sc_sgin else "informal",
        }


class OutputCleaner:
    _PREFIJOS  = re.compile(r'^[\s\n]*(?:(?:mensaje\s+)?refactorizado\s*[:\-–]?\s*|respuesta\s+(?:diplomática|ejecutiva|casual)\s*[:\-–]?\s*|\*{0,2}(?:refactorizado|versión\s+\w+)\*{0,2}\s*[:\-–]?\s*|aquí\s+(?:está|te\s+dejo|tienes|va)\s*[^:\n]*[:\-–]?\s*|(?:claro|por\s+supuesto|con\s+gusto|entendido)[,.]?\s*|nota\s*[:\-–]\s*[^\n]+\n\s*)', re.IGNORECASE | re.MULTILINE)
    _SUFIJOS   = re.compile(r'\n+(?:espero\s+que\s+(?:esto|te|le)\s+.{0,80}$|nota\s*[:\-–]\s*.{0,120}$|si\s+necesitas\s+.{0,80}$|puedo\s+ajustar\s+.{0,80}$)', re.IGNORECASE | re.DOTALL)
    _ETIQUETAS = re.compile(r'(?:tono\s+)?(?:diplomático|ejecutivo|casual)\s*[:\-–]\s*', re.IGNORECASE)
    _NO_LATINO = re.compile(r'\s*[\u0370-\u03ff\u0400-\u04ff\u0600-\u06ff\u0900-\u0fff\u3000-\u9fff\uac00-\ud7af].*', re.DOTALL)
    _EMOJIS    = re.compile("[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001FA00-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]+", re.UNICODE)
    _RELLENO   = re.compile(r'\s*[,.]?\s*(?:¿(?:verdad|no|órale|sí|entendido|correcto|de\s+acuerdo|vamos\s+bien)\?|,\s*¿(?:sí|no|verdad|órale)\?)', re.IGNORECASE)
    _PALABRAS_EN = {'okay','sorry','check','feedback','update','meeting','call','team','deadline','cool','awesome','sure','thanks','bye','hello','please','wait','stop','done','nice','great','bad','let','make','take','give','need','want','know','think','see','come','look','try','keep','use','send','bro','dude','guys','man','just','then','well','now','here','there','this','that','with','and','the','for','are','but','not','what','all','were','when','your','can','which','their','will','other','about','many','them','these','some','her','would','him','into','has','two'}

    def limpiar(self, texto, tono, tiene_emojis_orig):
        if not texto:
            return ""
        texto = self._PREFIJOS.sub("", texto).strip()
        texto = self._SUFIJOS.sub("",  texto).strip()
        texto = self._ETIQUETAS.sub("", texto).strip()
        texto = self._NO_LATINO.sub("", texto).strip()
        parrafos = [p.strip() for p in re.split(r'\n{2,}', texto) if p.strip()]
        if len(parrafos) >= 2 and any(parrafos[1].lower().startswith(k) for k in ["otra versión", "versión alternativa", "también puedes", "o bien", "alternativamente"]):
            texto = parrafos[0]
        else:
            texto = "\n\n".join(parrafos)
        if tono in ("diplomatico", "ejecutivo"):
            texto = self._EMOJIS.sub("", texto).strip()
            texto = re.sub(r'\s{2,}', ' ', texto)
            texto = re.sub(r'^\s*[,.:;]\s*', '', texto).strip()
        elif tono == "casual":
            if not tiene_emojis_orig:
                texto = self._EMOJIS.sub("", texto).strip()
            texto = self._RELLENO.sub("", texto).strip()
            palabras = [p for p in texto.split() if p and (p[0].isupper() or re.sub(r'[^a-zA-Z]', '', p).lower() not in self._PALABRAS_EN)]
            texto = ' '.join(palabras).strip()
            if len(texto.split()) < 2:
                return ""
        texto = re.sub(r' {2,}', ' ', texto)
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        if texto and not texto[0].isupper():
            texto = texto[0].upper() + texto[1:]
        if texto and not re.search(r'[.!?]$', texto.rstrip()):
            texto = texto.rstrip() + '.'
        return texto.strip()


class PromptBuilder:
    def construir(self, mensaje, tono, ctx, pre, intento, ancla):
        emisor     = ctx["emisor"]
        receptor   = ctx["receptor"]
        tipo       = ctx["tipo"]
        tono_em    = ctx["tono_emocional"]
        intensidad = ctx["intensidad"]
        palabras   = ctx["palabras"]
        lon_clase  = pre["longitud_clase"]
        groserías  = pre["tiene_groserías"]
        slang      = pre["tiene_slang"]
        reg_rec    = ctx.get("registro_receptor", "informal")

        estrategia = "ESTRATEGIA — MENSAJE MUY CORTO:\nCambia el tono únicamente. Misma brevedad." if lon_clase == "muy_corto" else \
                     ("ESTRATEGIA — MENSAJE CORTO:\nMantén la respuesta breve." if lon_clase == "corto" else \
                      "ESTRATEGIA — PRESERVACIÓN COMPLETA:\nConserva TODO el contenido. Cada dato, fecha, acción y razón DEBE aparecer en la versión reescrita.")
        slang_instr = f"SLANG/GROSERÍAS — carga emocional: {intensidad}\nTransmite ESA MISMA INTENSIDAD en tono {tono.upper()}.\nNO uses las palabras originales. SÍ preserva la fuerza.\n" if (groserías or slang) else ""
        perspectiva = self._perspectiva(emisor, receptor, reg_rec)
        tono_def    = self._tono_principios(tono, tono_em, intensidad, lon_clase, tipo)
        tipo_nota   = {
            "pregunta":   "PREGUNTA — la respuesta también debe serlo.",
            "queja":      "QUEJA — debe seguir siéndolo.",
            "solicitud":  "SOLICITUD — conserva TODOS los detalles.",
            "comunicado": "COMUNICADO — mantén emisor grupal.",
            "reporte":    "REPORTE — no lo conviertas en directiva.",
            "aviso":      "AVISO — conserva el objetivo de notificación.",
            "general":    "Conserva el tipo del mensaje original.",
        }.get(tipo, "Conserva el tipo y propósito.")
        min_w = max(4, int(palabras * 0.80))
        max_w = max(15, int(palabras * (1.4 if lon_clase in ("muy_corto", "corto") else 2.2)))
        return f"""Eres un experto en comunicación profesional en México.\n\nTAREA: Cambiar ÚNICAMENTE el tono. El contenido NO cambia.\n\nANÁLISIS:\nQuién habla: {emisor} | A quién: {receptor} ({reg_rec}) | Tipo: {tipo}\nTono emocional: {tono_em} (intensidad {intensidad}) | Palabras: {palabras}\n\nNÚCLEOS SEMÁNTICOS — preservar:\n{ancla}\n──────────────────────────────────────────────\n{estrategia}\n{perspectiva}\n\n{tono_def}\n\n{('──────────────────────────────\n'+slang_instr) if slang_instr else ''}\nTipo de mensaje: {tipo_nota}\n\nPROHIBICIONES ABSOLUTAS:\n· NO escribas prefijos ni etiquetas\n· NO generes dos versiones\n· NO cambies quién hace qué\n· NO añadas información nueva\n· NO uses palabras en inglés\n· Si el mensaje es corto, tu respuesta también lo es\n\nLongitud objetivo: {min_w} a {max_w} palabras.\n\nMENSAJE ORIGINAL:\n"{mensaje}"\n\nEscribe ÚNICAMENTE el mensaje reescrito. Sin comillas. Sin prefijos. Sin explicaciones."""

    def _perspectiva(self, emisor, receptor, reg_rec):
        lineas = ["PERSPECTIVA GRAMATICAL:"]
        if emisor == "yo":
            lineas += ["· EMISOR = YO. Verbos: solicito, quiero, informo.", "  NUNCA: hemos, solicitamos."]
        elif emisor == "nosotros":
            lineas += ["· EMISOR = NOSOTROS. Verbos: solicitamos, queremos.", "  NUNCA: solicito, quiero."]
        else:
            lineas += ["· Mantén la misma persona verbal del original."]
        if receptor == "plural":
            lineas += ["· RECEPTOR = USTEDES. Usa: les, pueden, tienen. NUNCA: tú, te."]
        elif receptor == "singular_formal":
            lineas += ["· RECEPTOR = USTED. Usa: usted, su, le. NUNCA: tú, te, tu."]
        elif receptor == "singular_informal":
            lineas += ["· RECEPTOR = TÚ. Usa: te, tu, puedes. NUNCA: ustedes, les."]
        else:
            lineas += ["· Mantén los pronombres del original."]
        return "\n".join(lineas)

    def _tono_principios(self, tono, tono_em, intensidad, lon_clase, tipo):
        em_nota = ""
        if tono_em == "frustracion" and intensidad in ("media", "alta"):
            em_nota = {"diplomatico": "\nFrustración → firmeza respetuosa.", "ejecutivo": "\nFrustración → hecho + impacto + acción. Sin emociones.", "casual": "\nFrustración real → refléjala directamente."}.get(tono, "")
        elif tono_em == "urgencia":
            em_nota = "\nUrgencia → transmítela en el registro del tono."
        long_nota = "\nMensaje corto → respuesta igualmente corta." if lon_clase in ("muy_corto", "corto") else ""
        if tono == "diplomatico":
            base = "TONO DIPLOMÁTICO — identidad: RELACIÓN PRIMERO\n· Reconoce el contexto humano mientras expone el asunto.\n· Construcciones clave: 'Agradecería', 'Sería de gran apoyo'\n· Suaviza sin perder firmeza.\nPROHIBIDO: viñetas, frases burocráticas, placeholders."
        elif tono == "ejecutivo":
            base = "TONO EJECUTIVO — identidad: RESULTADO PRIMERO\n1. HECHO: primera oración = dato más importante.\n2. IMPACTO: consecuencia.\n3. ACCIÓN: qué se necesita hacer.\n· Voz activa. Frases cortas.\nPROHIBIDO: 'Agradecería', cierres suaves, relleno."
        else:
            base = "TONO CASUAL LABORAL — identidad: PERSONA REAL EN EL TRABAJO\n· Compañero de confianza mexicano. Directo y auténtico.\n· Conectores: porque, así que, por eso.\n· Español de México. Sin inglés."
        return base + em_nota + long_nota