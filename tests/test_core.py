# astro-core: pruebas. Correr con: python -m unittest discover -s tests
import json
import os
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from astro_core import chart, transits  # noqa: E402
import server  # noqa: E402

CASE = {'birth_utc': '1980-11-11 23:00:00', 'lat': -34.92126, 'lon': -57.95442, 'time_known': True}


class Core(unittest.TestCase):
    def test_natal(self):
        c = chart.compute(dict(CASE))
        self.assertEqual(c['planets'][0]['key'], 'sun')
        self.assertEqual(c['planets'][0]['sign'], 'scorpio')
        self.assertEqual(c['angles']['asc']['sign'], 'taurus')
        self.assertEqual(len(c['houses']), 12)

    def test_transits(self):
        t = transits.compute({'natal': chart.compute(dict(CASE)), 'start_local': '2026-10-30', 'days': 3, 'offset_min': -180})
        self.assertEqual(t['days'], 3)

    def test_http(self):
        server.KEY = 'k' * 40
        srv = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:%d' % srv.server_address[1]

        def post(path, body, key=None):
            h = {'Content-Type': 'application/json'}
            if key:
                h['X-Core-Key'] = key
            try:
                r = urllib.request.urlopen(urllib.request.Request(base + path, json.dumps(body).encode(), h))
                return r.status, json.load(r)
            except urllib.error.HTTPError as e:
                return e.code, None

        self.assertEqual(post('/natal', CASE)[0], 401)
        s, j = post('/natal', CASE, 'k' * 40)
        self.assertEqual((s, j['angles']['asc']['sign']), (200, 'taurus'))
        self.assertEqual(post('/natal', {'x': 1}, 'k' * 40)[0], 400)
        self.assertIn('github.com', json.load(urllib.request.urlopen(base + '/source'))['source'])
        self.assertIn('Affero', urllib.request.urlopen(base + '/').read().decode())
        srv.shutdown()


if __name__ == '__main__':
    unittest.main()
