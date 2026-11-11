# Normativa académica UAI | tablero + asistente (demo CENIA)

Demo de la Micropráctica 3, programa ConectIA 2026, Grupo 15. Usa solo los compilados oficiales y públicos de reglamentos de pregrado de la Universidad Adolfo Ibáñez (2018 a 2025). Prototipo, no es un sitio oficial UAI.

- **Quién decide qué:** grafo de cargos y trámites por promoción, con animación entre años.
- **La norma en el tiempo:** matriz trámite por año, coloreada por el cargo que decide.
- **Hallazgos del auditor** y **biblioteca de documentos** con su vigencia.
- **Chat que mueve el tablero:** responde con el compilado de la promoción y la matriz 2018-2025; cada cita se busca en el texto del PDF sin IA y se marca como verificada.

## Publicar en Streamlit Community Cloud (gratis)

1. https://share.streamlit.io, entrar con GitHub, **Create app**.
2. Repositorio `Clemente-H/normativa-uai-demo`, rama `main`, archivo `app.py`.
3. **Advanced settings > Secrets**:
   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-..."
   APP_PASSWORD = "uaipassword1234"
   ```
4. **Deploy**.

## Correr en local

```bash
cp .env.example .env   # pegar la clave de OpenRouter
uv run --env-file .env streamlit run app.py
```

## Estructura

- `app.py`: puerta con clave, componente del tablero, llamada al modelo y verificación de citas.
- `ui/`: CSS, HTML y JS del tablero (generados desde `maqueta/plantilla.html` con `uv run python maqueta/armar.py`).
- `maqueta/index.html`: la misma interfaz como archivo suelto, con respuestas pregrabadas.
- `data/`: texto por página de los compilados 2018 a 2025, matriz `atribuciones.json` y datos del tablero.
- `tools/extraer_atribuciones.py`: extrae la matriz con un modelo y verifica las citas.

Modelo por defecto: `deepseek/deepseek-v4.1-flash` (cerca de 1 centavo de dólar por consulta). Se cambia con el secreto `MODELO`.
