import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import logging

logger = logging.getLogger(__name__)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Baby Alert Bot is running!')
        
    def log_message(self, format, *args):
        # Override to avoid cluttering logs with HTTP requests
        return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    logger.info(f"Starting web server on port {port}")
    server.serve_forever()

def start_server_thread():
    thread = Thread(target=run_server)
    thread.daemon = True
    thread.start()
    logger.info("Web server thread started") 