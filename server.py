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
        
        html_content = b'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Baby Alert Bot</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }
                h1 { color: #0066cc; }
                .container { max-width: 800px; margin: 0 auto; }
                .info { background-color: #f0f8ff; padding: 15px; border-radius: 5px; }
                .link { margin-top: 20px; }
                .link a { background-color: #0066cc; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; }
                .link a:hover { background-color: #004c99; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Baby Alert Bot is running!</h1>
                <div class="info">
                    <p>This is the web server for the Baby Alert Telegram bot.</p>
                    <p>The bot is actively monitoring and is ready to track your baby's activities.</p>
                </div>
                <h2>Quick Bottle Feature</h2>
                <p>You can create shortcuts on your phone's home screen to quickly start a bottle feeding:</p>
                <ol>
                    <li>Open your Telegram bot using: <code>https://t.me/your_bot_username?start=quick_bottle</code></li>
                    <li>Or use the <code>/quick_bottle</code> command in chat</li>
                </ol>
                <p><strong>First Time Setup:</strong></p>
                <ol>
                    <li>The first time you use the quick bottle feature, it will ask you to select which baby to feed if you have multiple babies</li>
                    <li>If you only have one baby registered, it will automatically select that baby</li>
                    <li>After a baby is selected, the bottle feeding will start immediately</li>
                </ol>
                <p><strong>Ending the Feeding:</strong></p>
                <ol>
                    <li>To end the feeding, tap the "Done Feeding" button or type <code>/done</code> in the chat</li>
                    <li>For bottle feedings, you'll be asked to input the amount after ending</li>
                </ol>
                <p><strong>Android Instructions:</strong></p>
                <ol>
                    <li>Create a home screen shortcut pointing to <code>https://t.me/your_bot_username?start=quick_bottle</code></li>
                    <li>Use any shortcut creator app to make this link accessible from your home screen</li>
                </ol>
                <p><strong>iOS Instructions:</strong></p>
                <ol>
                    <li>Open Safari and go to <code>https://t.me/your_bot_username?start=quick_bottle</code></li>
                    <li>Tap the Share button and select "Add to Home Screen"</li>
                </ol>
            </div>
        </body>
        </html>
        '''
        self.wfile.write(html_content)
        logger.info(f"Handled GET request from {self.client_address[0]} for path: {self.path}")
    
    def do_HEAD(self):
        """Handle HEAD requests - this is what UptimeRobot uses for monitoring"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        logger.info(f"Handled HEAD request from {self.client_address[0]} for path: {self.path}")
        
    def log_message(self, format, *args):
        # Override to avoid cluttering logs with HTTP requests
        return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    logger.info(f"Starting web server on port {port}")
    logger.info(f"Health check URL: http://0.0.0.0:{port}/")
    server.serve_forever()

def start_server_thread():
    thread = Thread(target=run_server)
    thread.daemon = True
    thread.start()
    logger.info("Web server thread started") 