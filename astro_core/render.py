# astro-core · conversión de documentos
# Copyright (C) 2026 Lafon Blanco SRL
#
# Este programa es software libre bajo la GNU Affero General Public License, versión 3. Se distribuye SIN GARANTÍA.
"""HTML -> PDF (WeasyPrint) y SVG -> PNG (CairoSVG).

Los documentos los arma quien llama; acá solo se convierten. No se descarga nada de internet:
cualquier recurso externo (imágenes, hojas de estilo, fuentes remotas) se rechaza, y el contenido
tiene que venir autocontenido.
"""


def _no_fetch(url, *args, **kwargs):
    raise ValueError('recursos externos no permitidos')


def pdf(html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=html, url_fetcher=_no_fetch).write_pdf()


def png(svg: str, width: int = 1200) -> bytes:
    import cairosvg
    if not 100 <= width <= 4000:
        raise ValueError('ancho fuera de rango')
    # unsafe=False (por defecto): CairoSVG no sigue enlaces externos ni entidades
    return cairosvg.svg2png(bytestring=svg.encode('utf-8'), output_width=width, background_color='white')
