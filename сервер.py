#!/usr/bin/env python3
# Локальный голосовой сервер Калькулика.
# Проксирует запросы на fish.audio (голос Miyagi) с 127.0.0.1.
# Запуск: python3 сервер.py
import http.server
import json
import os
import ssl
import urllib.request

PORT = int(os.environ.get('PORT', 8765))
REF = os.environ.get('FISH_REF', '4ce1aea7d39e4679839ce6fc350a7047')
ROOT = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get('FISH_KEY', '').strip()
if not KEY:
    _kf = os.path.join(ROOT, 'fish_key.txt')
    if os.path.exists(_kf):
        with open(_kf) as _f:
            KEY = _f.read().strip()


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.split('?')[0] == '/api/ping':
            b = json.dumps({'ok': True, 'voice': 'miyagi'}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(b)))
            self._cors()
            self.end_headers()
            self.wfile.write(b)
        else:
            super().do_GET()

    def do_POST(self):
        path = self.path.split('?')[0]
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            body = {}
        if path == '/api/voices':
            self.api_voices(body)
            return
        if path == '/api/tts':
            self.api_tts(body)
            return
        self.send_error(404)

    def _fish_resp(self, url, payload):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode() if payload is not None else None,
            method='POST' if payload is not None else 'GET',
            headers={
                'Content-Type': 'application/json' if payload is not None else 'text/plain',
                'Authorization': 'Bearer ' + KEY,
                'model': 's2.1-pro-free',
            },
        )
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                return r.read()
        except Exception:
            with urllib.request.urlopen(req, timeout=30, context=ssl._create_unverified_context()) as r:
                return r.read()

    def _send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self._cors()
        self.end_headers()
        self.wfile.write(b)

    def api_voices(self, body):
        q = str(body.get('q') or '').strip()[:60]
        if not q:
            self._send_json({'items': []})
            return
        try:
            from urllib.parse import quote
            raw = self._fish_resp('https://api.fish.audio/model?title=' + quote(q) + '&page_size=20', None)
            d = json.loads(raw)
        except Exception as e:
            self._send_json({'items': [], 'error': str(e)}, 502)
            return
        items = []
        for it in (d.get('items') or d.get('data') or [])[:20]:
            langs = it.get('languages') or []
            score = 0
            if 'ru' in langs:
                score += 2
            tags = it.get('tags') or []
            if any('female' in str(t).lower() for t in tags):
                score += 1
            items.append((score, {
                'ref': it.get('_id'),
                'title': it.get('title'),
                'author': (it.get('author') or {}).get('nickname') or '',
                'tags': tags[:4],
            }))
        items.sort(key=lambda x: -x[0])
        self._send_json({'items': [i[1] for i in items]})

    def api_tts(self, body):
        try:
            text = str(body.get('text') or '')[:2000]
            speed = max(0.5, min(2.0, float(body.get('speed') or 1)))
            ref = str(body.get('ref') or REF)
            audio = self._fish_resp('https://api.fish.audio/v1/tts', {
                'text': text, 'reference_id': ref, 'format': 'mp3', 'prosody': {'speed': speed},
            })
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Content-Length', str(len(audio)))
            self._cors()
            self.end_headers()
            self.wfile.write(audio)
        except Exception as e:
            msg = str(e).encode()
            self.send_response(502)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(msg)))
            self._cors()
            self.end_headers()
            self.wfile.write(msg)


if __name__ == '__main__':
    # 0.0.0.0 + $PORT — требование Render; локально остаётся 127.0.0.1:8765.
    host = '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1'
    print('Калькулик-сервер слушает http://%s:%d' % (host, PORT), flush=True)
    http.server.ThreadingHTTPServer((host, PORT), H).serve_forever()