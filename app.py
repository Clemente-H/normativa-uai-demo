"""Asistente de normativa académica UAI | demo Micropráctica 3 (CENIA).

Chat con citas verificadas contra el PDF oficial, comparación entre cohortes y panel compartido.
Variables de entorno: OPENROUTER_API_KEY (obligatoria), MAX_CALLS (tope de llamadas, por defecto 400).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import threading
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI
from rapidfuzz import fuzz

DATA = Path(__file__).parent / "data"
MODELOS = [
    "deepseek/deepseek-v4.1-flash",
    "anthropic/claude-haiku-5.5",
    "google/gemini-3.8-flash",
    "anthropic/claude-sonnet-5.5",
]
MAX_CALLS = int(os.environ.get("MAX_CALLS", "400"))
UMBRAL = 85  # similitud mínima (0-100) para dar una cita por verificada

st.set_page_config(page_title="Asistente de normativa UAI", page_icon=":material/gavel:", layout="wide")


# ---------------------------------------------------------------- datos y estado compartido
@st.cache_resource
def cargar_corpus() -> dict[int, dict]:
    corpus = {}
    for f in sorted(DATA.glob("compilado_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for p in d["pages"]:
            p["norm"] = normalizar(p["text"])
        corpus[d["year"]] = d
    return corpus


@st.cache_resource
def registro() -> dict:
    """Estado compartido entre todas las sesiones (todos ven el mismo panel)."""
    return {"items": [], "lock": threading.Lock(), "calls": 0}


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).lower()
    t = re.sub(r"-\s*\n\s*", "", t)  # palabras cortadas al final de línea
    t = re.sub(r"[\"“”«»']", "", t)
    return re.sub(r"\s+", " ", t).strip()


def contexto(years: list[int]) -> str:
    corpus = cargar_corpus()
    partes = []
    for y in years:
        d = corpus[y]
        partes.append(f"<<<DOCUMENTO: {d['titulo']} (aplica a quienes ingresaron en {y})>>>")
        for p in d["pages"]:
            partes.append(f"=== Compilado {y} | Página {p['page']} ===\n{p['text']}")
    return "\n\n".join(partes)


# ---------------------------------------------------------------- prompts
INSTRUCCIONES = """Eres el asistente de normativa académica de pregrado de la Universidad Adolfo Ibáñez para docentes y personal administrativo de la Facultad de Comunicaciones.
Responde usando SOLO los documentos entregados, sin conocimiento externo.
Reglas:
- Máximo 5 líneas o pasos numerados. Claro y cordial.
- Cada afirmación normativa debe ir respaldada por una cita LITERAL copiada del documento (entre 8 y 40 palabras, sin modificar ni una palabra), con su página según los marcadores "=== Compilado AAAA | Página N ===".
- Nombra cargos o unidades, nunca personas. Si te preguntan por el nombre de una persona, di que no está en los documentos y deriva a la unidad.
- Si la regla depende del año de ingreso y hay más de un compilado con reglas distintas, dilo, resume la diferencia y pide el año de ingreso.
- Si te piden confirmar algo que el documento contradice, corrígelo con la cita.
- Si la información no está en los documentos, dilo explícitamente (estado "no_esta") y sugiere a qué unidad derivar.
"""

FORMATO_CHAT = """Devuelve SOLO un objeto JSON válido, sin texto adicional, con esta forma:
{"estado": "respondida" | "parcial" | "falta_año" | "no_esta" | "contradiccion",
 "respuesta": "texto breve en markdown",
 "citas": [{"año": 2025, "reglamento": "nombre del reglamento", "articulo": "Artículo 12", "pagina": 19, "cita": "texto literal copiado del documento"}],
 "derivar_a": "cargo o unidad"}"""

FORMATO_COMPARAR = """Compara cómo responde cada compilado a la pregunta. Devuelve SOLO un objeto JSON válido:
{"tema": "título corto",
 "por_año": [{"año": 2023, "respuesta": "1 a 3 líneas", "citas": [{"año": 2023, "reglamento": "...", "articulo": "...", "pagina": 15, "cita": "texto literal"}]}],
 "cambio": true | false,
 "que_cambio": "una o dos líneas: qué cambió entre cohortes, o 'Sin cambios' "}
Incluye una entrada por cada compilado entregado, en orden de año. Si un compilado no trata el tema, dilo en su respuesta y deja citas vacías."""


# ---------------------------------------------------------------- llamada al modelo
def llamar(modelo: str, years: list[int], mensajes: list[dict], formato: str) -> dict:
    reg = registro()
    with reg["lock"]:
        if reg["calls"] >= MAX_CALLS:
            return {"estado": "error", "respuesta": "Se alcanzó el tope de consultas de la demo.", "citas": []}
        reg["calls"] += 1

    key = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY", None)
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    bloque_docs = {"type": "text", "text": contexto(years)}
    if modelo.startswith("anthropic/"):
        bloque_docs["cache_control"] = {"type": "ephemeral"}
    system = [
        {"type": "text", "text": INSTRUCCIONES},
        bloque_docs,
        {"type": "text", "text": formato},
    ]
    try:
        r = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "system", "content": system}, *mensajes],
            temperature=0,
            max_tokens=4000,
            extra_headers={"X-Title": "Demo normativa UAI"},
            extra_body={"reasoning": {"effort": "low"}, "usage": {"include": True}},
        )
        texto = r.choices[0].message.content or ""
        costo = getattr(r, "usage", None) and (r.usage.model_extra or {}).get("cost")
        if costo:
            with reg["lock"]:
                reg["costo"] = reg.get("costo", 0.0) + float(costo)
    except Exception as e:  # noqa: BLE001
        return {"estado": "error", "respuesta": f"Error al consultar el modelo: {e}", "citas": []}
    return parsear(texto)


def parsear(texto: str) -> dict:
    t = re.sub(r"```(?:json)?", "", texto).strip()
    ini = t.find("{")
    if ini >= 0:
        try:
            obj, _ = json.JSONDecoder(strict=False).raw_decode(t[ini:])
            if isinstance(obj, dict):
                return obj
        except Exception:  # noqa: BLE001
            pass
        m = re.search(r'"respuesta"\s*:\s*"((?:[^"\\]|\\.)*)', t, flags=re.S)
        if m:
            try:
                resp = json.loads('"' + m.group(1) + '"', strict=False)
            except Exception:  # noqa: BLE001
                resp = m.group(1)
            est = re.search(r'"estado"\s*:\s*"([a-zñ_]+)"', t)
            return {"estado": est.group(1) if est else "parcial", "respuesta": resp, "citas": []}
    return {"estado": "parcial", "respuesta": texto, "citas": []}


# ---------------------------------------------------------------- verificación de citas
def verificar(cita: dict, years: list[int]) -> dict:
    """Busca la cita literal en el PDF. Devuelve estado, página real y fragmento resaltado."""
    corpus = cargar_corpus()
    q = normalizar(str(cita.get("cita", "")))
    if len(q) < 15:
        return {"ok": False, "motivo": "sin cita literal"}
    try:
        y = int(cita.get("año") or years[0])
    except (TypeError, ValueError):
        y = years[0]
    if y not in corpus:
        y = years[0]
    pags = corpus[y]["pages"]
    try:
        pag = int(cita.get("pagina"))
    except (TypeError, ValueError):
        pag = -1

    def buscar(p):
        al = fuzz.partial_ratio_alignment(q, p["norm"])
        return al.score, al.dest_start, al.dest_end

    candidatas = [p for p in pags if p["page"] == pag] or []
    mejor = None
    for p in candidatas:
        s, a, b = buscar(p)
        mejor = (s, p, a, b)
    if not mejor or mejor[0] < UMBRAL:
        for p in pags:
            s, a, b = buscar(p)
            if not mejor or s > mejor[0]:
                mejor = (s, p, a, b)
    s, p, a, b = mejor
    ok = s >= UMBRAL
    n = p["norm"]
    frag = (
        html.escape(n[max(0, a - 220) : a])
        + "<mark>"
        + html.escape(n[a:b])
        + "</mark>"
        + html.escape(n[b : b + 220])
    )
    return {
        "ok": ok,
        "score": round(s),
        "año": y,
        "pagina_real": p["page"],
        "pagina_citada": pag,
        "url": f"{corpus[y]['url']}#page={p['page']}",
        "fragmento": frag,
    }


def verificar_todas(citas: list[dict], years: list[int]) -> list[dict]:
    with ThreadPoolExecutor() as ex:
        return list(ex.map(lambda c: verificar(c, years), citas))


# ---------------------------------------------------------------- piezas de interfaz
ESTADOS = {
    "respondida": (":green-badge[:material/check_circle: Respondida]"),
    "parcial": (":orange-badge[:material/rule: Respuesta parcial]"),
    "falta_año": (":blue-badge[:material/calendar_month: Depende del año de ingreso]"),
    "no_esta": (":red-badge[:material/search_off: No está en los documentos]"),
    "contradiccion": (":violet-badge[:material/warning: Contradicción entre documentos]"),
    "error": (":red-badge[:material/error: Error]"),
}


def mostrar_citas(citas: list[dict], verifs: list[dict]) -> None:
    for c, v in zip(citas, verifs):
        etiqueta = f"{c.get('reglamento', 'Reglamento')} | {c.get('articulo', '')} | p. {c.get('pagina', '?')}"
        if v.get("ok"):
            badge = ":green-badge[:material/verified: Cita verificada en el PDF]"
            if v["pagina_real"] != v["pagina_citada"]:
                badge += f" :orange-badge[página corregida: {v['pagina_real']}]"
        else:
            badge = ":red-badge[:material/gpp_bad: Cita no encontrada en el PDF]"
        with st.expander(f"{etiqueta}"):
            st.markdown(badge)
            st.markdown(f"> {c.get('cita', '')}")
            if v.get("fragmento"):
                st.caption(f"Texto del compilado {v['año']}, página {v['pagina_real']} (similitud {v['score']}%):")
                st.markdown(
                    f"<div style='font-size:0.85rem;line-height:1.5;padding:.6rem;border-radius:6px;"
                    f"background:rgba(127,127,127,.08)'>…{v['fragmento']}…</div>",
                    unsafe_allow_html=True,
                )
                st.link_button("Abrir PDF oficial en esa página", v["url"], icon=":material/open_in_new:")


def mostrar_respuesta(m: dict) -> None:
    res = m["res"]
    st.markdown(ESTADOS.get(res.get("estado"), ESTADOS["parcial"]))
    st.markdown(res.get("respuesta", ""))
    if res.get("derivar_a"):
        st.markdown(f"**Derivar a:** {res['derivar_a']}")
    if res.get("citas"):
        n_ok = sum(1 for v in m["verifs"] if v.get("ok"))
        st.caption(f"Fuentes | {n_ok} de {len(m['verifs'])} citas verificadas automáticamente contra el PDF oficial")
        mostrar_citas(res["citas"], m["verifs"])


def anotar_feedback(item_id: str, key: str) -> None:
    val = st.session_state.get(key)
    reg = registro()
    with reg["lock"]:
        for it in reg["items"]:
            if it["id"] == item_id:
                it["feedback"] = {None: "", 0: "negativo", 1: "positivo"}[val]


# ---------------------------------------------------------------- app
corpus = cargar_corpus()
YEARS = sorted(corpus)

with st.sidebar:
    st.markdown("### :material/gavel: Normativa UAI")
    st.caption("Demo CENIA | Micropráctica 3 | ConectIA 2026")
    modelo = st.selectbox("Modelo (vía OpenRouter)", MODELOS, index=0)
    st.divider()
    st.markdown("**Cómo funciona**")
    st.markdown(
        "1. El modelo lee el compilado completo de reglamentos de la cohorte.\n"
        "2. Responde y copia frases literales como respaldo.\n"
        "3. La app busca cada frase en el PDF oficial, **sin IA**, y marca si existe y en qué página."
    )
    st.divider()
    st.caption("Documentos: compilados oficiales de reglamentos de pregrado UAI " + ", ".join(map(str, YEARS)) + ". Sin datos de estudiantes.")

tab_chat, tab_comp, tab_panel = st.tabs(
    [":material/chat: Asistente", ":material/compare_arrows: Comparar cohortes", ":material/dashboard: Panel"]
)

# ---------------- asistente
with tab_chat:
    st.markdown("#### Pregúntale a los reglamentos")
    opciones = [str(y) for y in reversed(YEARS)] + ["No lo sé"]
    anio = st.segmented_control("Año de ingreso del estudiante", opciones, default=opciones[0], key="anio")
    anio = anio or opciones[0]
    years = YEARS if anio == "No lo sé" else [int(anio)]

    ejemplos = [
        "¿Quién aprueba una convalidación de asignaturas?",
        "Un estudiante faltó a una prueba por enfermedad. ¿Qué plazo tiene para justificar?",
        "Confírmame que un estudiante puede suspender 3 semestres",
        "¿Un estudiante puede usar IA en un trabajo?",
        "¿Cuál es el horario de atención de la Secretaría Académica?",
    ]
    ej = st.pills("Ejemplos", ejemplos, key="ej", label_visibility="collapsed")

    if "msgs" not in st.session_state:
        st.session_state.msgs = []

    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.markdown(m["content"])
            else:
                mostrar_respuesta(m)
                k = f"fb_{m['id']}"
                st.feedback("thumbs", key=k, on_change=anotar_feedback, args=(m["id"], k))

    pregunta = st.chat_input("Escribe tu pregunta sobre reglamentos de pregrado")
    if ej and not pregunta and st.session_state.get("_ultimo_ej") != ej:
        pregunta = ej
    st.session_state["_ultimo_ej"] = ej

    if pregunta:
        st.session_state.msgs.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.status("Leyendo el compilado y verificando citas…", expanded=False) as s:
                historial = []
                for m in st.session_state.msgs[-7:]:
                    if m["role"] == "user":
                        historial.append({"role": "user", "content": m["content"]})
                    else:
                        historial.append({"role": "assistant", "content": json.dumps(m["res"], ensure_ascii=False)})
                historial[-1] = {
                    "role": "user",
                    "content": f"[Año de ingreso indicado: {anio}] {pregunta}",
                }
                res = llamar(modelo, years, historial, FORMATO_CHAT)
                verifs = verificar_todas(res.get("citas") or [], years)
                s.update(label="Listo", state="complete")
            item = {"id": uuid.uuid4().hex[:8], "role": "assistant", "res": res, "verifs": verifs}
            mostrar_respuesta(item)
            k = f"fb_{item['id']}"
            st.feedback("thumbs", key=k, on_change=anotar_feedback, args=(item["id"], k))
        st.session_state.msgs.append(item)
        reg = registro()
        with reg["lock"]:
            reg["items"].append(
                {
                    "id": item["id"],
                    "hora": dt.datetime.now().strftime("%H:%M"),
                    "pregunta": pregunta,
                    "año": anio,
                    "estado": res.get("estado", ""),
                    "citas": len(verifs),
                    "verificadas": sum(1 for v in verifs if v.get("ok")),
                    "modelo": modelo,
                    "feedback": "",
                }
            )

# ---------------- comparar cohortes
with tab_comp:
    st.markdown("#### La misma pregunta, tres cohortes")
    st.caption("La normativa cambia según el año de ingreso. Aquí se ve qué dice cada compilado, lado a lado, con sus citas verificadas.")
    temas = [
        "¿Cuántos semestres puede suspender un estudiante?",
        "¿Cuántas veces puede anular asignaturas un estudiante?",
        "¿Qué plazo tiene un estudiante para justificar una inasistencia a una prueba?",
        "¿Qué porcentaje de créditos se puede convalidar?",
    ]
    c1, c2 = st.columns([3, 1])
    tema = c1.selectbox("Pregunta", temas, accept_new_options=True, key="tema")
    ir = c2.button("Comparar", type="primary", width="stretch", icon=":material/compare_arrows:")
    if ir and tema:
        with st.status("Leyendo los tres compilados…") as s:
            res = llamar(modelo, YEARS, [{"role": "user", "content": tema}], FORMATO_COMPARAR)
            por = res.get("por_año") or []
            verifs = [verificar_todas(e.get("citas") or [], [int(e.get("año", YEARS[0]))]) for e in por]
            s.update(label="Listo", state="complete")
        st.session_state.comp = {"tema": tema, "res": res, "verifs": verifs}
        reg = registro()
        with reg["lock"]:
            reg["items"].append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "hora": dt.datetime.now().strftime("%H:%M"),
                    "pregunta": f"[Comparar] {tema}",
                    "año": "todos",
                    "estado": "cambio" if res.get("cambio") else "sin cambio",
                    "citas": sum(len(v) for v in verifs),
                    "verificadas": sum(1 for vs in verifs for v in vs if v.get("ok")),
                    "modelo": modelo,
                    "feedback": "",
                }
            )
    comp = st.session_state.get("comp")
    if comp:
        res = comp["res"]
        if res.get("estado") == "error":
            st.error(res.get("respuesta"))
        else:
            if res.get("cambio"):
                st.warning(f"**Cambió entre cohortes.** {res.get('que_cambio', '')}", icon=":material/change_circle:")
            else:
                st.success(f"**Sin cambios entre cohortes.** {res.get('que_cambio', '')}", icon=":material/check_circle:")
            cols = st.columns(max(1, len(res.get("por_año") or [])))
            for col, e, vs in zip(cols, res.get("por_año") or [], comp["verifs"]):
                with col.container(border=True):
                    st.markdown(f"##### Ingreso {e.get('año')}")
                    st.markdown(e.get("respuesta", ""))
                    if e.get("citas"):
                        mostrar_citas(e["citas"], vs)

# ---------------- panel
with tab_panel:
    reg = registro()
    with reg["lock"]:
        items = list(reg["items"])
    st.markdown("#### Panel del asistente")
    st.caption("Compartido en vivo entre todas las personas conectadas. Solo guarda la pregunta, nunca quién la hizo.")
    m1, m2, m3, m4, m5 = st.columns(5)
    total_c = sum(i["citas"] for i in items)
    ok_c = sum(i["verificadas"] for i in items)
    m1.metric("Preguntas", len(items))
    m2.metric("Citas verificadas", f"{(100 * ok_c / total_c):.0f}%" if total_c else "—")
    m3.metric("Sin respuesta en documentos", sum(1 for i in items if i["estado"] == "no_esta"))
    m4.metric("Pulgar abajo", sum(1 for i in items if i["feedback"] == "negativo"))
    m5.metric("Gasto del modelo", f"US$ {reg.get('costo', 0.0):.2f}")

    st.markdown("##### Registro de fallas")
    st.caption("Preguntas que los documentos no responden o que alguien marcó como incorrectas. Es la lista de trabajo para quien mantiene los documentos.")
    fallas = [i for i in items if i["estado"] == "no_esta" or i["feedback"] == "negativo" or (i["citas"] and i["verificadas"] < i["citas"])]
    if fallas:
        st.dataframe(pd.DataFrame(fallas)[["hora", "pregunta", "año", "estado", "verificadas", "citas", "feedback"]], hide_index=True, width="stretch")
    else:
        st.info("Sin fallas registradas todavía.")

    st.markdown("##### Todas las preguntas")
    if items:
        st.dataframe(pd.DataFrame(items)[["hora", "pregunta", "año", "estado", "verificadas", "citas", "modelo", "feedback"]].iloc[::-1], hide_index=True, width="stretch")
    else:
        st.info("Aún no hay preguntas.")

    st.markdown("##### Documentos cargados")
    st.dataframe(
        pd.DataFrame(
            [
                {"documento": d["titulo"], "cohorte": y, "páginas": len(d["pages"]), "enlace": d["url"]}
                for y, d in sorted(corpus.items(), reverse=True)
            ]
        ),
        hide_index=True,
        width="stretch",
        column_config={"enlace": st.column_config.LinkColumn("enlace", display_text="Abrir PDF")},
    )
    st.button("Actualizar panel", icon=":material/refresh:")
