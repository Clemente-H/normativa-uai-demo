# Asistente de normativa académica UAI (demo CENIA)

Demo de la Micropráctica 3, programa ConectIA 2026. Responde preguntas sobre los compilados oficiales y públicos de reglamentos de pregrado de la Universidad Adolfo Ibáñez (2023, 2024 y 2025).

- **Citas verificadas sin IA:** el modelo copia una frase literal del reglamento y la app la busca en el texto del PDF oficial. Si la encuentra, la marca en verde, corrige la página si hace falta y enlaza al PDF en esa página.
- **Comparar cohortes:** la misma pregunta respondida para cada año de ingreso, lado a lado.
- **Panel compartido:** preguntas, fallas y documentos cargados. No guarda quién preguntó.

## Correr en local

```bash
cp .env.example .env   # y pega tu clave de OpenRouter
uv run --env-file .env streamlit run app.py
```

## Publicar en Streamlit Community Cloud (gratis)

1. Entrar a https://share.streamlit.io con GitHub y elegir **Create app**.
2. Repositorio: este repo | rama `main` | archivo `app.py`.
3. En **Advanced settings > Secrets** pegar: `OPENROUTER_API_KEY = "sk-or-v1-..."`
4. **Deploy**. En un par de minutos queda el enlace público.

## Datos

`data/compilado_AAAA.json` tiene el texto por página de los compilados publicados por la UAI. Se regeneran con `uv run python build_corpus.py` (requiere los PDF en `../corpus/originales/` y `pdftotext`). Sin datos de estudiantes.
