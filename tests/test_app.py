import json
import os
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
from app.server import Handler

class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path):
        try:
            response = urlopen(self.base + path, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_health(self):
        self.assertEqual(self.get('/healthz'), (200, {'status': 'ok'}))

    def test_release_identity(self):
        with patch.dict(os.environ, {'APP_REVISION': 'abc123'}):
            self.assertEqual(self.get('/')[1]['revision'], 'abc123')

    def test_readiness_failure_does_not_kill_liveness(self):
        with patch.dict(os.environ, {'FAIL_READINESS': 'true'}):
            self.assertEqual(self.get('/readyz')[0], 503)
            self.assertEqual(self.get('/healthz')[0], 200)

    def test_readiness_success(self):
        with patch.dict(os.environ, {'FAIL_READINESS': 'false'}):
            self.assertEqual(self.get('/readyz')[0], 200)

    def test_unknown_route(self):
        self.assertEqual(self.get('/missing')[0], 404)
