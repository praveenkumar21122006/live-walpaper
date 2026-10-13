"""CSBS LAN sync server — offline-proof one-button sync. No installs, Python only.

Run:  double-click START-SYNC-SERVER-PY.bat   (or: python sync-server.py)
Then: open the printed http:// address on every desktop.
Press SYNC ALL SCREENS on this PC: every screen restarts together.
"""
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8080
subs = []
lock = threading.Lock()


class H(BaseHTTPRequestHandler):
    server_version = 'CSBS/1.0'

    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body):
        raw = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(raw)

    def serve_file(self, name, ctype):
        p = os.path.join(ROOT, name)
        if not os.path.isfile(p):
            return self._send(404, 'text/plain', 'missing ' + name)
        with open(p, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ('/', '/index.html'):
            return self.serve_file('index.html', 'text/html; charset=utf-8')
        if u.path == '/csbs-fire-animation.html':
            return self.serve_file('csbs-fire-animation.html', 'text/html; charset=utf-8')
        if u.path == '/mqtt.min.js':
            return self.serve_file('mqtt.min.js', 'application/javascript')
        if u.path == '/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with lock:
                subs.append(self.wfile)
            try:
                self.wfile.write(b': connected\n\n')
                self.wfile.flush()
                while True:
                    time.sleep(25)
                    self.wfile.write(b': ping\n\n')
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                with lock:
                    if self.wfile in subs:
                        subs.remove(self.wfile)
            return
        if u.path == '/count':
            with lock:
                n = len(subs)
            return self._send(200, 'application/json', json.dumps({'n': n}))
        return self._send(404, 'text/plain', 'not found')

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == '/sync':
            try:
                ln = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                ln = 0
            msg = self.rfile.read(ln) if ln > 0 else b''
            if not msg:
                msg = json.dumps({'epoch': time.time() + 1}).encode('utf-8')
            with lock:
                targets = list(subs)
            dead = []
            for w in targets:
                try:
                    w.write(b'data: ' + msg + b'\n\n')
                    w.flush()
                except Exception:
                    dead.append(w)
            if dead:
                with lock:
                    for w in dead:
                        if w in subs:
                            subs.remove(w)
            return self._send(200, 'application/json',
                              json.dumps({'ok': True, 'screens': len(targets)}))
        return self._send(404, 'text/plain', 'not found')


def lan_ips():
    out = []
    try:
        for fam, _, _, _, addr in socket.getaddrinfo(socket.gethostname(), None):
            if fam == socket.AF_INET and not addr[0].startswith('127.'):
                if addr[0] not in out:
                    out.append(addr[0])
    except Exception:
        pass
    return out or ['<this-PC-IP>']


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('0.0.0.0', PORT), H)
    print('')
    print('  CSBS Fire Animation - LAN Sync Server running (works with NO internet).')
    print('')
    for ip in lan_ips():
        print('  Open on EVERY desktop:  http://%s:%d' % (ip, PORT))
    print('')
    print('  Press SYNC ALL SCREENS on this PC. Ctrl+C to stop.')
    print('')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
