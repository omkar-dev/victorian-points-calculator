#!/usr/bin/env python3
"""Serve the site for tests on http://localhost:8765 with caching turned off.

Velocity's Chrome keeps its profile between runs, so a plain http.server
would let it reuse yesterday's site.js. Run from the repo root:
    python3 tests/velocity/serve.py
"""
import functools
import http.server
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    handler = functools.partial(NoCache, directory=str(ROOT))
    http.server.ThreadingHTTPServer(("127.0.0.1", 8765), handler).serve_forever()
