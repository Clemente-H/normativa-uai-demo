"""Arma maqueta/index.html (autocontenido) desde plantilla.html + data/atribuciones.json.
Uso (desde demo_app/): uv run python -I maqueta/armar.py
"""
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = json.loads((AQUI.parent / "data" / "atribuciones.json").read_text(encoding="utf-8"))

DATA["urls"] = {
    "2025": "https://uai.cdn7pm.net/documentos/reglamentos-academicos-2025.pdf",
    "2024": "https://alumno.uai.cl/assets/uploads/2024/04/reglamentos-uai-2024.pdf",
    "2023": "https://alumno.uai.cl/assets/uploads/2023/01/reglamentos-uai-2023.pdf",
    "2022": "https://alumno.uai.cl/assets/uploads/2022/01/reglamento_2022.pdf",
    "2021": "https://alumno.uai.cl/assets/uploads/sites/3/2021/09/reglamentos-2021.pdf",
    "2020": "https://alumno.uai.cl/assets/uploads/sites/3/2020/03/reglamentos-2020.pdf",
    "2019": "https://alumno.uai.cl/assets/uploads/sites/2/2019/01/reglamentos-2019-vf.pdf",
    "2018": "https://alumno.uai.cl/assets/uploads/sites/2/2018/05/reglamento_2018.pdf",
}
U = DATA["urls"]

DATA["hallazgos"] = [
    {"id": "h2", "tipo": "Contradicción", "titulo": "Director o Decano de Pregrado, en el mismo compilado 2025",
     "detalle": "Licenciaturas habla siempre de Decano de Pregrado. Convalidaciones sigue diciendo Director/a de Pregrado. La página de autoridades solo lista Decano/a.",
     "evidencia": "Convalidaciones, art. 13, p. 19 | Licenciaturas D.A. 16-2025", "url": U["2025"] + "#page=19"},
    {"id": "h6", "tipo": "Contradicción", "titulo": "2 días hábiles o 48 horas para justificar",
     "detalle": "El reglamento da 2 días hábiles desde que cesa el impedimento. La web de Secretaría de Viña dice 48 horas. Con un fin de semana de por medio no es lo mismo.",
     "evidencia": "Licenciaturas 2025, art. 23, p. 9 | alumno.uai.cl", "url": U["2025"] + "#page=9"},
    {"id": "h10", "tipo": "Contradicción", "titulo": "Los artículos se corren un número desde 2024",
     "detalle": "Anulación pasa del art. 45 al 46, suspensión del 46 al 47, cambio de sede del 34 al 35. Citar el artículo sin el año lleva a error.",
     "evidencia": "Licenciaturas 2023 vs 2024 y 2025", "url": U["2024"] + "#page=15"},
    {"id": "h1", "tipo": "Vigencia", "titulo": "Convalidaciones 2025 dice \"a partir de 2024\"",
     "detalle": "El compilado de la promoción 2025 reutiliza el decreto 94-2023, que se aplica a quienes ingresaron a partir de 2024. No es un error, pero confunde.",
     "evidencia": "Convalidaciones, art. 1, p. 18", "url": U["2025"] + "#page=18"},
    {"id": "h11", "tipo": "Vigencia", "titulo": "El Código de Honor 2023 no menciona la IA",
     "detalle": "El compilado 2023 trae la versión 51-2021. Desde 2024, el art. 7 sanciona usar IA sin citar. Rige la versión vigente, no la del compilado.",
     "evidencia": "Código de Honor 2023 vs 2024, art. 7", "url": U["2024"] + "#page=25"},
    {"id": "h7", "tipo": "Vigencia", "titulo": "Versiones derogadas siguen publicadas",
     "detalle": "Conviven en línea dos políticas de IA (2025 y 2026), dos reglamentos de personal académico y dos de magíster. Un buscador puede citar la versión superada.",
     "evidencia": "uai.cdn7pm.net | 11-11-2026", "url": "https://uai.cdn7pm.net/documentos/politica-de-inteligencia-artificial-uai.pdf"},
    {"id": "h3", "tipo": "Referencia rota", "titulo": "Un decreto sin número",
     "detalle": "El Reglamento de Derechos y Deberes aparece encabezado como \"DECRETO RECTORÍA Nº - 2019\".",
     "evidencia": "Compilado 2025, p. 62", "url": U["2025"] + "#page=62"},
    {"id": "h4", "tipo": "Referencia rota", "titulo": "Cita un Código de Honor derogado",
     "detalle": "Derechos y Deberes remite al Decreto 52/2016, reemplazado tres veces desde entonces, y al Orgánico 9/2019 cuando el resto cita el 3/2020.",
     "evidencia": "Compilado 2025, p. 62", "url": U["2025"] + "#page=62"},
    {"id": "h5", "tipo": "Vacío", "titulo": "Falta el artículo 30",
     "detalle": "El Reglamento de Becas de Excelencia del compilado 2024 salta del artículo 29 al 31.",
     "evidencia": "Compilado 2024, pp. 52-53", "url": U["2024"] + "#page=52"},
]

DATA["chat"] = [
    {"pregunta": "¿Quién aprueba una convalidación?", "claves": ["convalid"], "estado": "respondida",
     "texto": "La aprueba el/la **Director/a de Pregrado**, previa consulta a la Escuela o Facultad. En asignaturas de Derecho, el/la Decano/a de Derecho.\nOjo: en el mismo compilado, Licenciaturas ya no habla de Director sino de **Decano de Pregrado**. Lo marqué como hallazgo.",
     "citas": [{"año": "2025", "id": "convalidacion"}], "derivar": "Secretaría Académica de Pregrado, que recibe la solicitud",
     "foco": {"año": 2025, "tramite": "convalidacion", "hallazgo": "h2"}},
    {"pregunta": "¿Quién autoriza una suspensión de estudios?", "claves": ["suspen", "suspend"], "estado": "falta_año",
     "texto": "**Depende del año de ingreso.** El máximo no cambia (2 semestres en la licenciatura), pero sí quién autoriza: en 2023 y 2024, el **Director de Pregrado**; en 2025, el **Decano de Pregrado**; entre 2020 y 2022, cualquiera de los dos.\n¿En qué año ingresó el estudiante? Mira cómo cambió en el tablero.",
     "citas": [{"año": "2023", "id": "suspension"}, {"año": "2025", "id": "suspension"}], "derivar": "Secretaría Académica de Pregrado",
     "foco": {"tramite": "suspension", "vista": "tiempo", "play": True}},
    {"pregunta": "Confírmame que con ingreso 2025 puede suspender 3 semestres", "claves": ["confírm", "confirm", "3 semestres", "tres semestres"], "estado": "contradiccion",
     "texto": "**No puedo confirmarlo.** El máximo son 2 semestres en la licenciatura. Más allá de eso, solo excepcionalmente y con autorización del **Decano de Pregrado**. En 2025 desaparece la Comisión de Gracia de esta decisión.",
     "citas": [{"año": "2025", "id": "suspension_adicional"}], "derivar": "Decano/a de Pregrado",
     "foco": {"año": 2025, "tramite": "suspension_adicional"}},
    {"pregunta": "¿Qué plazo hay para justificar una inasistencia?", "claves": ["justific", "inasist", "falt"], "estado": "respondida",
     "texto": "**2 días hábiles** desde que cesa el impedimento, ante la **Secretaría Académica de Pregrado**. Solo cuentan causas de salud. Ojo: una página web de la UAI dice 48 horas.",
     "citas": [{"año": "2025", "id": "justificacion"}], "derivar": "Secretaría Académica de Pregrado",
     "foco": {"año": 2025, "tramite": "justificacion", "hallazgo": "h6"}},
    {"pregunta": "¿Cuál es el horario de la Secretaría Académica?", "claves": ["horario", "atención", "atencion"], "estado": "no_esta",
     "texto": "**No está en los reglamentos cargados.** Registré la pregunta para que el responsable de contenidos decida si se agrega la fuente.",
     "derivar": "Secretaría Académica de Pregrado"},
]

import csv
def _estado(v, doc):
    v2 = v.lower()
    if v2.startswith("vigente para la promoción"): return "Vigente"
    if "duplicado" in v2: return "Duplicado"
    if "no normativo" in v2: return "No normativo"
    if any(k in v2 for k in ["reemplazada", "superado", "histórico", "derogad"]): return "Superado"
    if any(k in v2 for k in ["dudosa", "aparente", "desactualizada"]): return "Revisar"
    return "Vigente"
def _tipo(doc):
    d = doc.lower()
    for k, n, s in [("compilado", "Compilado", "REG"), ("calendario", "Calendario", "CAL"), ("código de honor", "Código de Honor", "HON"), ("política", "Política", "POL"), ("protocolo", "Política", "POL"), ("guía", "Guía", "GUI"), ("malla", "Comunicaciones", "COM"), ("folleto", "Comunicaciones", "COM"), ("reglamento", "Reglamento", "REG"), ("autoridades", "Web UAI", "WEB"), ("secretaría", "Web UAI", "WEB")]:
        if k in d: return n, s
    return "Otro", "DOC"
DOCS = []
for r in csv.DictReader(open(AQUI.parent.parent / "corpus" / "fichas_documentos.csv", encoding="utf-8")):
    tipo, sigla = _tipo(r["documento"])
    DOCS.append({"documento": r["documento"], "cohortes": r["cohortes"], "vigencia": r["vigencia"], "responsable": r["responsable"], "enlace": r["enlace"], "estado": _estado(r["vigencia"], r["documento"]), "tipo": tipo, "sigla": sigla})
for n, why in [("Compilado de reglamentos 2026", "No publicado: la promoción 2026 no tiene reglamento de licenciaturas en línea"),
               ("Organigrama con cargos de segundo nivel", "Solo existe la lista de autoridades de primer nivel"),
               ("Reglamentos internos de la Escuela de Comunicaciones y Periodismo", "Práctica, titulación, normas de la Escuela: pedir a la Escuela"),
               ("Procedimientos de Secretaría Académica", "Solo hay páginas web con plazos de 2020")]:
    DOCS.append({"documento": n, "cohortes": "Pendiente", "vigencia": why, "responsable": "", "enlace": "", "estado": "Falta", "tipo": "Falta para el piloto", "sigla": "?"})
DATA["documentos"] = DOCS

html = (AQUI / "plantilla.html").read_text(encoding="utf-8")
html = html.replace("/*__DATA__*/null", json.dumps(DATA, ensure_ascii=False))
(AQUI / "index.html").write_text(html, encoding="utf-8")
print("ok", len(html) // 1024, "KB")
