import http.server
import socketserver
import json
import asyncio
import urllib.parse
from functools import partial
from conductor import investigate

PORT = 8080
IP = "172.16.244.154"

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def add_cors_headers(self):
        """Add CORS headers to the response"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """Handle OPTIONS request for CORS preflight"""
        self.send_response(200)
        self.add_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests with query parameters"""
        try:
            # Parse the URL path and query parameters
            if self.path.startswith('/responses'):
                # Parse query parameters
                query_components = urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query)
                query_dict = dict(query_components)
                
                # Extract specific parameters
                question = query_dict.get('question', '')
                topic = query_dict.get('topic', '')
                time_frame = query_dict.get('time_frame', 'week')
                
                # Create data dictionary to pass to investigate
                data = {
                    "question": question,
                    "topic": topic,
                    "time_frame": time_frame
                }
                
                # Create a new event loop for this request
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the async function in the event loop
                response = loop.run_until_complete(investigate(data))
                loop.close()
                
                # Send the response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.add_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            else:
                # For other paths, use the default handler
                super().do_GET()
        except Exception as e:
            self.send_response(500)
            self.add_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())
    
    def do_POST(self):
        """Handle POST requests with JSON body"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            
            # Create a new event loop for this request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async function in the event loop
            response = loop.run_until_complete(investigate(data))
            loop.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.add_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except json.JSONDecodeError:
            self.send_response(400)
            self.add_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Invalid JSON"
            }).encode())
        except Exception as e:
            self.send_response(500)
            self.add_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())

# Modify the TCP server to use ThreadingMixIn for better handling of concurrent requests
class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    # Use the threaded server instead of the basic TCPServer
    with ThreadedHTTPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()