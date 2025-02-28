import socket
import threading
import random
import os
import base64
import re  # Added for regex

MEME_FOLDER = "memes"
EASTER_EGG_HOST = "google.ca"

class MemeProxyServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.memes = self.load_memes()

    def load_memes(self):
        # Same as before
        memes = []
        if os.path.exists(MEME_FOLDER) and os.path.isdir(MEME_FOLDER):
            for file in os.listdir(MEME_FOLDER):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    memes.append(os.path.join(MEME_FOLDER, file))
        return memes

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(5)
            print(f"Proxy server listening on {self.host}:{self.port}")
            while True:
                client_socket, addr = s.accept()
                print(f"Accepted connection from {addr}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.start()

    def handle_client(self, client_socket):
        try:
            request_data = client_socket.recv(4096)
            if not request_data:
                client_socket.close()
                return

            request_str = request_data.decode('latin-1')
            lines = request_str.split('\r\n')
            if not lines:
                client_socket.close()
                return

            first_line = lines[0].split()
            if len(first_line) < 2:
                client_socket.close()
                return
            method, url = first_line[0], first_line[1]

            if method == 'CONNECT':
                client_socket.close()
                return

            host = None
            for line in lines:
                if line.startswith('Host:'):
                    host = line.split(' ')[1].strip()
                    break

            if host == EASTER_EGG_HOST:
                self.send_easter_egg(client_socket)
                client_socket.close()
                return

            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((host, 80))
            target_socket.sendall(request_data)

            response_data = b''
            while True:
                data = target_socket.recv(4096)
                if not data:
                    break
                response_data += data

            processed_data = self.process_response(response_data)
            client_socket.sendall(processed_data)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
            if 'target_socket' in locals():
                target_socket.close()

    def send_easter_egg(self, client_socket):
        if not self.memes:
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>No memes found!</h1>"
            client_socket.send(response.encode())
            return

        meme_path = random.choice(self.memes)
        with open(meme_path, 'rb') as f:
            meme_data = f.read()
        base64_data = base64.b64encode(meme_data).decode('utf-8')
        ext = os.path.splitext(meme_path)[1].lower()
        content_type = "image/jpeg" if ext in ('.jpg', '.jpeg') else "image/png" if ext == '.png' else "image/gif"

        html = f"""
        <html>
            <body style="margin:0; padding:0;">
                <h1 style="text-align:center;">CAPYBARA SUPRISE!!!!</h1>
                <img src="data:{content_type};base64,{base64_data}" style="width:100vw; height:100vh; object-fit: contain;" />
            </body>
        </html>
        """
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html)}\r\n"
            "\r\n"
            f"{html}"
        )
        client_socket.send(response.encode())

    def process_response(self, response_bytes):
        # Same as before until body_str is decoded
        header_end = response_bytes.find(b'\r\n\r\n')
        if header_end == -1:
            return response_bytes

        headers_part = response_bytes[:header_end]
        body_part = response_bytes[header_end+4:]

        content_type = None
        for header_line in headers_part.split(b'\r\n'):
            if header_line.lower().startswith(b'content-type:'):
                content_type = header_line.split(b':')[1].strip().decode()
                break

        if content_type and 'text/html' in content_type:
            try:
                body_str = body_part.decode('utf-8')
            except UnicodeDecodeError:
                return response_bytes

            modified_body_str = self.replace_images_with_regex(body_str)  # Changed method
            modified_body = modified_body_str.encode('utf-8')

            headers = []
            content_length_replaced = False
            for header_line in headers_part.split(b'\r\n'):
                if header_line.lower().startswith(b'content-length:'):
                    headers.append(f"Content-Length: {len(modified_body)}".encode())
                    content_length_replaced = True
                else:
                    headers.append(header_line)
            if not content_length_replaced:
                headers.append(f"Content-Length: {len(modified_body)}".encode())

            new_headers = b'\r\n'.join(headers)
            return new_headers + b'\r\n\r\n' + modified_body
        else:
            return response_bytes

    def replace_images_with_regex(self, html_str):
        # Regex pattern to find <img> tags and their existing src
        pattern = re.compile(
            r'(<img\b)([^>]*?)(\bsrc\s*=\s*["\'])(.*?)(["\'])([^>]*?>)',
            re.IGNORECASE
        )

        def replace_image(match):
            if random.random() < 0.5 and self.memes:
                # Get meme data
                meme_path = random.choice(self.memes)
                with open(meme_path, 'rb') as f:
                    meme_data = f.read()
                base64_data = base64.b64encode(meme_data).decode('utf-8')
                ext = os.path.splitext(meme_path)[1].lower()
                content_type = "image/jpeg" if ext in ('.jpg', '.jpeg') else "image/png" if ext == '.png' else "image/gif"
                # Replace src with base64 meme
                return f'{match.group(1)}{match.group(2)}{match.group(3)}data:{content_type};base64,{base64_data}{match.group(5)}{match.group(6)}'
            else:
                # Keep original image
                return match.group(0)

        # Replace 50% of images using regex
        modified_html = pattern.sub(replace_image, html_str)
        return modified_html

if __name__ == "__main__":
    proxy = MemeProxyServer('127.0.0.1', 8080)
    proxy.start()