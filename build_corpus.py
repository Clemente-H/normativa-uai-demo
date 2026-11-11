"""Extrae el texto de los compilados (una entrada por página del PDF) a data/compilado_AAAA.json.

Uso: uv run python build_corpus.py
Requiere pdftotext (poppler). Solo se corre en local; la app usa los JSON ya generados.
"""
import json
import subprocess
from pathlib import Path

ORIGINALES = Path(__file__).parent.parent / "corpus" / "originales"
DATA = Path(__file__).parent / "data"

URLS = {
    2025: "https://uai.cdn7pm.net/documentos/reglamentos-academicos-2025.pdf",
    2024: "https://alumno.uai.cl/assets/uploads/2024/04/reglamentos-uai-2024.pdf",
    2023: "https://alumno.uai.cl/assets/uploads/2023/01/reglamentos-uai-2023.pdf",
    2022: "https://alumno.uai.cl/assets/uploads/2022/01/reglamento_2022.pdf",
    2021: "https://alumno.uai.cl/assets/uploads/sites/3/2021/09/reglamentos-2021.pdf",
    2020: "https://alumno.uai.cl/assets/uploads/sites/3/2020/03/reglamentos-2020.pdf",
    2019: "https://alumno.uai.cl/assets/uploads/sites/2/2019/01/reglamentos-2019-vf.pdf",
    2018: "https://alumno.uai.cl/assets/uploads/sites/2/2018/05/reglamento_2018.pdf",
}


def main() -> None:
    DATA.mkdir(exist_ok=True)
    for year, url in URLS.items():
        pdf = ORIGINALES / f"compilado_reglamentos_pregrado_{year}.pdf"
        raw = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        pages = raw.split("\f")
        if pages and not pages[-1].strip():
            pages = pages[:-1]
        out = {
            "year": year,
            "titulo": f"Reglamentos académicos de pregrado UAI, compilado {year}",
            "url": url,
            "pages": [{"page": i + 1, "text": t.strip()} for i, t in enumerate(pages)],
        }
        (DATA / f"compilado_{year}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(year, len(pages), "páginas", sum(len(p["text"]) for p in out["pages"]), "caracteres")


if __name__ == "__main__":
    main()
