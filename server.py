# astro-core · cálculo astrológico sobre Swiss Ephemeris
# Copyright (C) 2026 Lafon Blanco SRL
#
# Este programa es software libre bajo la GNU Affero General Public License, versión 3. Se distribuye SIN GARANTÍA.
# Ver LICENSE. Usa Swiss Ephemeris (c) Astrodienst AG (AGPL-3.0). Ver NOTICE.md.
"""Servidor HTTP mínimo (solo biblioteca estándar).

  GET  /          texto con la licencia y el enlace al código fuente (AGPL-3.0, sección 13)
  GET  /health    {"ok": true}
  GET  /source    {"source": "<url del repositorio>", "license": "AGPL-3.0-or-later"}
  POST /natal     JSON de chart.compute  -> carta natal
  POST /transits  JSON de transits.compute -> tránsitos

Si ASTRO_CORE_KEY está definida, los POST exigen la cabecera X-Core-Key con ese valor.
No publicar este puerto a internet: está pensado para la red interna de Docker.
"""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from astro_core import chart, transits

SOURCE_URL = os.environ.get('ASTRO_CORE_SOURCE_URL', 'https://github.com/herlafon/astro-core')
KEY = os.environ.get('ASTRO_CORE_KEY', '')
MAX_BODY = 262144  # los tránsitos reciben la carta natal completa

INFO = (
    'astro-core: cálculo astrológico sobre Swiss Ephemeris (c) Astrodienst AG.\n'
    'Software libre bajo la GNU Affero General Public License v3.\n'
    'Código fuente: ' + SOURCE_URL + '\n'
)


class Handler(BaseHTTPRequestHandler):
    server_version = 'astro-core'

    def log_message(self, fmt, *args):  # sin datos de personas en los logs
        sys.stderr.write('%s %s\n' % (self.command, self.path))

    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        data = body.encode('utf-8') if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            return self._send(200, INFO, 'text/plain; charset=utf-8')
        if self.path == '/health':
            return self._send(200, {'ok': True})
        if self.path == '/source':
            return self._send(200, {'source': SOURCE_URL, 'license': 'AGPL-3.0-or-later'})
        self._send(404, {'error': 'not_found'})

    def do_POST(self):
        if self.path not in ('/natal', '/transits'):
            return self._send(404, {'error': 'not_found'})
        if KEY and not hmac.compare_digest(self.headers.get('X-Core-Key', ''), KEY):
            return self._send(401, {'error': 'unauthorized'})
        try:
            n = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            n = -1
        if n <= 0 or n > MAX_BODY:
            return self._send(400, {'error': 'bad_length'})
        try:
            inp = json.loads(self.rfile.read(n))
            out = chart.compute(inp) if self.path == '/natal' else transits.compute(inp)
        except (ValueError, KeyError, TypeError) as e:
            return self._send(400, {'error': 'bad_input', 'detail': type(e).__name__})
        except Exception as e:  # no se filtran detalles internos
            sys.stderr.write('error: %s\n' % type(e).__name__)
            return self._send(500, {'error': 'internal_error'})
        self._send(200, out)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
