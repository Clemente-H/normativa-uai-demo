"""Normativa académica UAI | tablero + asistente (demo CENIA, Micropráctica 3).

El tablero es un componente HTML (ui/). El chat le manda la pregunta a Python, Python consulta el modelo
con el compilado de la promoción elegida más la matriz "quién decide qué" 2018-2025, verifica cada cita
contra el texto del PDF sin IA y devuelve la respuesta con el foco que mueve el tablero.

Secretos o variables: OPENROUTER_API_KEY (obligatoria), APP_PASSWORD (por defecto uaipassword1234),
MODELO (por defecto deepseek/deepseek-v4.1-flash), MAX_CALLS (por defecto 600).
"""
from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st
from openai import OpenAI
from rapidfuzz import fuzz

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"
UI = RAIZ / "ui"
UMBRAL = 85  # similitud mínima (0-100) para dar una cita por verificada
HALLAZGO_POR_TRAMITE = {"convalidacion": "h2", "justificacion": "h6"}

st.set_page_config(page_title="Normativa UAI", page_icon=":material/gavel:", layout="wide", initial_sidebar_state="collapsed")


def secreto(nombre: str, defecto: str | None = None) -> str | None:
    v = os.environ.get(nombre)
    if v:
        return v
    try:
        return st.secrets.get(nombre, defecto)
    except Exception:  # noqa: BLE001  (sin secrets.toml en local)
        return defecto


MODELO = secreto("MODELO", "deepseek/deepseek-v4.1-flash")
MAX_CALLS = int(secreto("MAX_CALLS", "600"))
CLAVE_APP = secreto("APP_PASSWORD", "uaipassword1234")


# ---------------------------------------------------------------- datos y estado compartido
def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).lower()
    t = re.sub(r"-\s*\n\s*", "", t)
    t = re.sub(r"[\"“”«»']", "", t)
    return re.sub(r"\s+", " ", t).strip()


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
def cargar_tablero() -> dict:
    return json.loads((DATA / "tablero.json").read_text(encoding="utf-8"))


@st.cache_resource
def matriz_texto() -> str:
    t = cargar_tablero()
    nombres = {x["id"]: x["nombre"] for x in t["tramites"]}
    lineas = ["TABLA VERIFICADA: QUIÉN DECIDE CADA TRÁMITE, POR PROMOCIÓN DE INGRESO (2018 a 2025)"]
    for y in sorted(t["por_año"]):
        for it in t["por_año"][y]:
            alt = f" o {it['decide_alt']}" if it.get("decide_alt") else ""
            lineas.append(
                f"{y} | {it['id']} ({nombres[it['id']]}) | decide: {it.get('decide') or 'No indicado'}{alt} | "
                f"{it.get('reglamento') or ''}, {it.get('articulo') or ''}, p. {it.get('pagina_real') or it.get('pagina')} | "
                f'frase: "{it.get("cita") or ""}"'
            )
    return "\n".join(lineas)


@st.cache_resource
def registro() -> dict:
    """Estado compartido entre todas las sesiones."""
    return {"lock": threading.Lock(), "calls": 0, "costo": 0.0, "preguntas": 0, "sin_respuesta": 0}


# ---------------------------------------------------------------- modelo
INSTRUCCIONES = """Eres el asistente de normativa académica de pregrado de la Universidad Adolfo Ibáñez para docentes y personal administrativo de la Escuela de Comunicaciones y Periodismo.
Responde usando SOLO los documentos entregados: el compilado de reglamentos de la promoción indicada y una tabla verificada de quién decide cada trámite en cada promoción (2018 a 2025). Sin conocimiento externo.
Reglas:
- Máximo 4 líneas. Claro y cordial. Usa **negrita** para el dato central.
- Cada afirmación normativa va respaldada por una cita LITERAL copiada del documento (8 a 40 palabras, sin cambiar ni una palabra), con su año y página según los marcadores "=== Compilado AAAA | Página N ===" o según la tabla.
- El año que aparece como "visible en el tablero" NO lo indicó el usuario. Si la pregunta no menciona un año de ingreso ni una promoción, y la tabla muestra que la respuesta cambia entre promociones, NO respondas para un solo año: usa estado "falta_año", resume en una o dos líneas cómo cambió (qué años, qué cargo) con citas de la tabla, y pregunta el año de ingreso. Si la pregunta sí menciona un año, responde para ese año.
- Nombra cargos o unidades, nunca personas. Si piden el nombre de quien ocupa un cargo, di que no está en los documentos.
- Si te piden confirmar algo que el documento contradice, corrígelo (estado "contradiccion").
- Si la información no está, dilo (estado "no_esta") y sugiere a qué unidad derivar.
"""

FORMATO = """Devuelve SOLO un objeto JSON válido, sin texto adicional:
{"estado": "respondida" | "parcial" | "falta_año" | "no_esta" | "contradiccion",
 "respuesta": "texto breve con **negritas**",
 "citas": [{"año": 2025, "reglamento": "nombre del reglamento", "articulo": "Artículo 47", "pagina": 15, "cita": "texto literal"}],
 "derivar_a": "cargo o unidad",
 "foco": {"tramite": "uno de estos id o null: TRAMITES", "año": 2025}}"""


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


def llamar(year: int, mensajes: list[dict]) -> dict:
    reg = registro()
    with reg["lock"]:
        if reg["calls"] >= MAX_CALLS:
            return {"estado": "error", "respuesta": "Se alcanzó el tope de consultas de la demo.", "citas": []}
        reg["calls"] += 1
    d = cargar_corpus()[year]
    docs = f"<<<DOCUMENTO: {d['titulo']} (aplica a quienes ingresaron en {year})>>>\n" + "\n\n".join(
        f"=== Compilado {year} | Página {p['page']} ===\n{p['text']}" for p in d["pages"]
    )
    ids = ", ".join(x["id"] for x in cargar_tablero()["tramites"])
    system = [
        {"type": "text", "text": INSTRUCCIONES},
        {"type": "text", "text": matriz_texto()},
        {"type": "text", "text": docs, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": FORMATO.replace("TRAMITES", ids)},
    ]
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=secreto("OPENROUTER_API_KEY"))
    try:
        r = client.chat.completions.create(
            model=MODELO,
            messages=[{"role": "system", "content": system}, *mensajes],
            temperature=0,
            max_tokens=4000,
            extra_headers={"X-Title": "Demo normativa UAI"},
            extra_body={"reasoning": {"effort": "low"}, "usage": {"include": True}},
        )
        texto = r.choices[0].message.content or ""
        costo = (getattr(r, "usage", None) and (r.usage.model_extra or {}).get("cost")) or 0
        with reg["lock"]:
            reg["costo"] += float(costo)
    except Exception as e:  # noqa: BLE001
        return {"estado": "error", "respuesta": f"No pude consultar el modelo ({type(e).__name__}). Intenta de nuevo.", "citas": []}
    return parsear(texto)


# ---------------------------------------------------------------- verificación de citas (sin IA)
def verificar(cita: dict, year: int) -> dict:
    corpus = cargar_corpus()
    q = normalizar(str(cita.get("cita", "")))
    try:
        y = int(cita.get("año") or year)
    except (TypeError, ValueError):
        y = year
    if y not in corpus:
        y = year
    if len(q) < 15:
        return {"ok": False, "año": y, "pagina": cita.get("pagina")}
    try:
        pag = int(cita.get("pagina"))
    except (TypeError, ValueError):
        pag = -1
    pags = corpus[y]["pages"]
    mejor = (0, None)
    for p in sorted(pags, key=lambda p: p["page"] != pag):
        s = fuzz.partial_ratio(q, p["norm"])
        if s > mejor[0]:
            mejor = (s, p["page"])
        if s >= UMBRAL:
            break
    return {"ok": mejor[0] >= UMBRAL, "año": y, "pagina": mejor[1] if mejor[0] >= UMBRAL else pag}


def responder(pregunta: str, year: int, historial: list[dict]) -> dict:
    msgs = [*historial[-4:], {"role": "user", "content": f"[Promoción visible en el tablero, no indicada por el usuario: {year}] {pregunta}"}]
    r = llamar(year, msgs)
    citas = r.get("citas") or []
    with ThreadPoolExecutor() as ex:
        verifs = list(ex.map(lambda c: verificar(c, year), citas))
    citas_out = [
        {
            "año": v["año"],
            "reglamento": c.get("reglamento", ""),
            "articulo": c.get("articulo", ""),
            "pagina": v["pagina"],
            "pagina_real": v["pagina"],
            "cita": c.get("cita", ""),
            "verificada": v["ok"],
        }
        for c, v in zip(citas, verifs)
    ]
    estado = r.get("estado", "parcial")
    foco = r.get("foco") or {}
    tram = foco.get("tramite") if foco.get("tramite") in {x["id"] for x in cargar_tablero()["tramites"]} else None
    foco_out = None
    if tram:
        foco_out = {"tramite": tram}
        try:
            fy = int(foco.get("año") or year)
            if 2018 <= fy <= 2025:
                foco_out["año"] = fy
        except (TypeError, ValueError):
            pass
        if estado == "falta_año":
            foco_out.update({"vista": "tiempo", "play": True})
            foco_out.pop("año", None)
        elif tram in HALLAZGO_POR_TRAMITE:
            foco_out["hallazgo"] = HALLAZGO_POR_TRAMITE[tram]
    reg = registro()
    with reg["lock"]:
        reg["preguntas"] += 1
        if estado == "no_esta":
            reg["sin_respuesta"] += 1
    return {
        "estado": estado if estado != "error" else "no_esta",
        "texto": r.get("respuesta", ""),
        "citas": citas_out,
        "derivar": r.get("derivar_a") or "",
        "foco": foco_out,
        "live": True,
    }


# ---------------------------------------------------------------- puerta de entrada
OCULTAR_STREAMLIT = """<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer, #MainMenu { display:none !important; }
.block-container, [data-testid="stMainBlockContainer"] { padding:0 !important; max-width:100% !important; }
[data-testid="stAppViewContainer"], .stApp { background:#F3F5F8; }
</style>"""

LOGIN_CSS = """<style>
[data-testid="stMainBlockContainer"] { max-width:420px !important; margin:12vh auto 0; padding:0 16px !important; }
.login-mark { width:54px; height:54px; border-radius:14px; background:#009FE3; color:#fff; display:grid; place-items:center; font:800 18px Inter, sans-serif; margin-bottom:18px; box-shadow:0 8px 24px rgba(0,159,227,.35); }
.login h1 { font:800 26px Inter, sans-serif; color:#15171A; margin:0 0 6px; letter-spacing:-.02em; }
.login p { font:400 15px Inter, sans-serif; color:#616365; margin:0 0 22px; }
[data-testid="stForm"] { border:1px solid #E2E6EB !important; background:#fff; border-radius:16px; padding:22px !important; box-shadow:0 6px 24px rgba(21,23,26,.06); }
.stButton button, [data-testid="stFormSubmitButton"] button { background:#009FE3 !important; color:#fff !important; border:0 !important; border-radius:10px !important; font-weight:700 !important; width:100%; }
</style>"""


def puerta() -> bool:
    if st.session_state.get("ok"):
        return True
    st.markdown(OCULTAR_STREAMLIT + LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="login"><div class="login-mark">UAI</div><h1>Normativa académica</h1>'
        "<p>Prototipo del Grupo 15 ConectIA | demo CENIA. Ingresa la clave que te compartieron.</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("login"):
        clave = st.text_input("Clave", type="password", placeholder="Clave de acceso")
        if st.form_submit_button("Entrar"):
            if clave.strip() == CLAVE_APP:
                st.session_state.ok = True
                st.rerun()
            st.error("Clave incorrecta.")
    return False


# ---------------------------------------------------------------- app
if not puerta():
    st.stop()

st.markdown(OCULTAR_STREAMLIT, unsafe_allow_html=True)

tablero = st.components.v2.component(
    "tablero_normativa",
    html=(UI / "tablero.html").read_text(encoding="utf-8"),
    css=(UI / "tablero.css").read_text(encoding="utf-8"),
    js=(UI / "tablero.js").read_text(encoding="utf-8"),
)

reg = registro()
res = tablero(
    data={
        "base": cargar_tablero(),
        "respuesta": st.session_state.get("ultima"),
        "stats": {"sin_respuesta": reg["sin_respuesta"], "preguntas": reg["preguntas"]},
    },
    key="tablero",
    on_pregunta_change=lambda: None,
)

p = getattr(res, "pregunta", None)
if p and p.get("id") != st.session_state.get("procesada"):
    st.session_state.procesada = p["id"]
    hist = st.session_state.setdefault("historial", [])
    out = responder(p["q"], int(p.get("año") or 2025), hist)
    out["id"] = p["id"]
    hist += [{"role": "user", "content": p["q"]}, {"role": "assistant", "content": out["texto"]}]
    st.session_state.ultima = out
    st.rerun()
