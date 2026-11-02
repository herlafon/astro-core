# astro-core

Cálculo de cartas natales y tránsitos sobre [Swiss Ephemeris](https://www.astro.com/swisseph/). Es el motor de
cálculo de *Tu Brujita* (tubrujita.com.ar), publicado como programa independiente bajo **GNU AGPL v3**.

Recibe la fecha de nacimiento en UTC y las coordenadas, y devuelve posiciones de planetas, ángulos, casas (Placidus por
defecto) y aspectos. No guarda datos de nadie: calcula y responde.

## Usar
```
pip install -r requirements.txt
python server.py                       # escucha en :8000
curl -s localhost:8000/natal -d '{"birth_utc":"1980-11-11 23:00:00","lat":-34.92126,"lon":-57.95442,"time_known":true}'
```
Por consola: `echo '{...}' | python -m astro_core.chart`.

También convierte documentos (no guarda nada): `POST /pdf` `{"html": "..."}` → PDF (WeasyPrint) y `POST /png` `{"svg": "...", "width": 1200}` → PNG (CairoSVG). Sin acceso a recursos externos: el HTML tiene que venir autocontenido.

Variables: `PORT` (8000), `ASTRO_CORE_KEY` (si existe, los POST exigen `X-Core-Key`), `ASTRO_CORE_SOURCE_URL`.
Docker: `docker build -t astro-core . && docker run --rm -p 127.0.0.1:8000:8000 astro-core`.

## Licencia
GNU Affero General Public License v3 o posterior (ver `LICENSE` y `NOTICE.md`). Si la modificás y la ofrecés como servicio
por red, tenés que ofrecer tu código fuente a quienes lo usan.
