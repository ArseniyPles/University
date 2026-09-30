import http.client
import threading
import unittest

import app


class HTTPIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.ExpenseTrackerHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read()
        conn.close()
        return response.status, response.getheader("Content-Type", ""), body

    def test_health_endpoint(self):
        status, content_type, body = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", content_type)
        self.assertIn(b'"status": "ok"', body)

    def test_index_serves_html(self):
        status, content_type, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Expense Tracker", body.decode("utf-8"))

    def test_data_endpoint_returns_structured_payload(self):
        status, content_type, body = self.request("/api/data?year=2026&month=9")
        self.assertEqual(status, 200)
        self.assertIn("application/json", content_type)
        text = body.decode("utf-8")
        self.assertIn('"expenses"', text)
        self.assertIn('"analysis"', text)
        self.assertIn('"budget"', text)


if __name__ == "__main__":
    unittest.main()
