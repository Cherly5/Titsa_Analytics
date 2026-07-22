from http.server import HTTPServer, SimpleHTTPRequestHandler

from config import MAPBOX_ACCESS_TOKEN, WS_HOST, WS_PORT


class ConfigHandler(SimpleHTTPRequestHandler):
    """Handler que inyecta configuración en el HTML"""

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return None

        if self.path == '/' or self.path == '/index.html':
            html_path = './index.html'

            try:
                with open(html_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                config_script = f'''
                <script>
                    window.CONFIG = {{
                        MAPBOX_ACCESS_TOKEN: '{MAPBOX_ACCESS_TOKEN}',
                        WS_URL: 'ws://{WS_HOST}:{WS_PORT}'
                    }};
                    console.log('Injected Configuration:', window.CONFIG);
                    console.log('Token:', window.CONFIG.MAPBOX_ACCESS_TOKEN.substring(0, 30) + '...');
                </script>
                '''

                if '<body>' in content:
                    content = content.replace('<body>', f'<body>{config_script}')
                else:
                    content = config_script + content

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                return None

            except Exception as exception:
                print(f"Error: {exception}")
                self.send_error(500, f"Internal Error: {exception}")
                return None

        return super().do_GET()


if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('localhost', port), ConfigHandler)
    print(f" Http Server in http://localhost:{port}")
    print(f" Token Mapbox: {'Checked' if MAPBOX_ACCESS_TOKEN else 'Not checked'}")
    print(f" WebSocket URL: ws://{WS_HOST}:{WS_PORT}")
    print(" Ctrl+C to stop execution\n")
    server.serve_forever()