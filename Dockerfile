# astro-core: cálculo astrológico (AGPL-3.0). Ver LICENSE y NOTICE.md.
FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir -w /wheels -r requirements.txt

FROM python:3.12-slim
# WeasyPrint (PDF) y CairoSVG (PNG) necesitan Pango/Cairo y fuentes con los símbolos astrológicos
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 libcairo2 fonts-dejavu-core fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -r -u 10001 core
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
WORKDIR /app
COPY server.py LICENSE NOTICE.md README.md ./
COPY astro_core ./astro_core
USER core
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)"
CMD ["python", "server.py"]
