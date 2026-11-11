"""Extrae la matriz trámite x quién decide de cada compilado (2018-2025) y verifica las citas contra el texto.

La IA propone (un modelo lee el compilado completo); la verificación es literal, sin IA.
Uso (desde demo_app/): uv run --env-file .env python -I tools/extraer_atribuciones.py
Salida: data/atribuciones.json
"""
import json
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI
from rapidfuzz import fuzz

RAIZ = Path(__file__).resolve().parents[1]
TEXTO = RAIZ.parent / "corpus" / "texto"
SALIDA = RAIZ / "data" / "atribuciones.json"
MODELO = os.environ.get("MODELO_EXTRACCION", "anthropic/claude-sonnet-5.5")
AÑOS = list(range(2018, 2026))

TRAMITES = [
    ("cambio_licenciatura", "Cambio de licenciatura o programa"),
    ("cambio_sede", "Cambio de sede (Santiago / Viña del Mar)"),
    ("suspension", "Suspensión temporal de estudios"),
    ("suspension_adicional", "Suspensiones adicionales al máximo permitido (excepcionales)"),
    ("anulacion", "Anulación de asignaturas o de semestre"),
    ("reincorporacion", "Reincorporación después de una suspensión o abandono"),
    ("eliminacion_reconsideracion", "Reconsideración o apelación de una eliminación académica"),
    ("justificacion", "Justificación de inasistencia a una evaluación"),
    ("recorreccion", "Solicitud de recorrección de una evaluación"),
    ("convalidacion", "Convalidación de asignaturas cursadas en otra institución"),
    ("homologacion", "Homologación de asignaturas"),
    ("sancion_honor", "Resolver infracciones graves al Código de Honor"),
]

CARGOS = [
    "Decano/a de Pregrado",
    "Director/a de Pregrado",
    "Comisión de Gracia",
    "Secretaría Académica de Pregrado",
    "Profesor/a del curso",
    "Decano/a de Facultad o Escuela",
    "Tribunal o Comité de Honor",
    "Otro",
]

PROMPT = """Lees el compilado oficial de reglamentos de pregrado de la Universidad Adolfo Ibáñez para la promoción de ingreso {año}.
Para cada trámite de la lista, identifica en el texto QUIÉN decide, aprueba o resuelve, ANTE QUIÉN se presenta, el plazo y el artículo.

Trámites (usa exactamente estos id):
{tramites}

Cargos normalizados (campo "decide" y "recibe" deben ser uno de estos, o null si el texto no lo dice):
{cargos}
Si el texto menciona dos cargos alternativos que deciden (por ejemplo "el Decano o el Director"), usa "decide": el primero y "decide_alt": el segundo. Si el cargo es "Otro", escribe el nombre literal en "cargo_literal".

Reglas:
- Usa solo el texto. Si el trámite no aparece, deja decide en null y explica en "nota".
- "cita" debe ser una frase COPIADA LITERALMENTE del texto (12 a 40 palabras) que contenga el cargo que decide.
- "pagina" es el número del marcador "=== PÁGINA N ===" donde está la cita.
- "plazo": breve (por ejemplo "10 días hábiles antes del semestre"), o null.
- "condicion": requisito principal en menos de 15 palabras, o null.

Devuelve SOLO un JSON válido: {{"año": {año}, "items": [{{"id": "...", "decide": "...", "decide_alt": null, "cargo_literal": null, "recibe": null, "plazo": null, "condicion": null, "reglamento": "...", "articulo": "Artículo N", "pagina": 0, "cita": "...", "nota": null}}]}}

TEXTO DEL COMPILADO:
{texto}"""


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).lower()
    t = re.sub(r"-\s*\n\s*", "", t)
    t = re.sub(r"[\"“”«»']", "", t)
    return re.sub(r"\s+", " ", t).strip()


def paginas(año: int) -> dict[int, str]:
    raw = (TEXTO / f"compilado_reglamentos_pregrado_{año}.txt").read_text(encoding="utf-8")
    partes = re.split(r"=== PÁGINA (\d+) ===", raw)
    return {int(partes[i]): partes[i + 1] for i in range(1, len(partes), 2)}


def extraer(año: int) -> dict:
    pags = paginas(año)
    texto = "\n".join(f"=== PÁGINA {n} ===\n{t}" for n, t in pags.items())
    prompt = PROMPT.format(
        año=año,
        tramites="\n".join(f"- {i}: {d}" for i, d in TRAMITES),
        cargos="\n".join(f"- {c}" for c in CARGOS),
        texto=texto,
    )
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    r = client.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=9000,
        extra_body={"reasoning": {"effort": "low"}, "usage": {"include": True}},
    )
    txt = re.sub(r"```(?:json)?", "", r.choices[0].message.content or "")
    data, _ = json.JSONDecoder(strict=False).raw_decode(txt[txt.find("{"):])
    costo = (r.usage.model_extra or {}).get("cost", 0)

    norm = {n: normalizar(t) for n, t in pags.items()}
    for it in data["items"]:
        q = normalizar(it.get("cita") or "")
        it["verificada"], it["pagina_real"], it["score"] = False, None, 0
        if len(q) < 15:
            continue
        orden = [it.get("pagina")] + [n for n in norm if n != it.get("pagina")]
        for n in orden:
            if n not in norm:
                continue
            s = fuzz.partial_ratio(q, norm[n])
            if s > it["score"]:
                it["score"], it["pagina_real"] = round(s), n
            if s >= 85:
                break
        it["verificada"] = it["score"] >= 85
    print(año, "ok", f"US$ {costo:.3f}", sum(i["verificada"] for i in data["items"]), "/", len(data["items"]), "citas verificadas", file=sys.stderr)
    return data


def main() -> None:
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(extraer, AÑOS))
    out = {"tramites": [{"id": i, "nombre": d} for i, d in TRAMITES], "cargos": CARGOS, "por_año": {str(r["año"]): r["items"] for r in res}}
    SALIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("escrito", SALIDA, file=sys.stderr)


if __name__ == "__main__":
    main()
