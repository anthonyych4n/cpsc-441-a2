import socket
import threading
import random
import os
import base64

MEME_FOLDER = "memes"
EASTER_EGG_HOST = "google.ca"
BUFFER_SIZE = 4096

class MemeProxyServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.memes = self.load_memes()

    def load_memes(self):
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
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        target_socket = None
        try:
            # Set timeout to prevent hanging
            client_socket.settimeout(10)
            
            request_data = b''
            while True:
                chunk = client_socket.recv(BUFFER_SIZE)
                if not chunk:
                    break
                request_data += chunk
                if len(chunk) < BUFFER_SIZE:
                    break

            if not request_data:
                return

            request_str = request_data.decode('latin-1', errors='ignore')
            host = self.extract_host(request_str)

            if host == EASTER_EGG_HOST:
                self.send_easter_egg(client_socket)
                return

            if b'CONNECT' in request_data:
                client_socket.close()
                return

            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(10)  # Add timeout
            target_socket.connect((host, 80))
            
            # Send request in chunks
            total_sent = 0
            while total_sent < len(request_data):
                sent = target_socket.send(request_data[total_sent:])
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent

            # Receive response
            response = self.receive_full_response(target_socket)
            modified_response = self.process_response(response, request_str)
            
            # Send response in chunks with error handling
            try:
                total_sent = 0
                while total_sent < len(modified_response):
                    sent = client_socket.send(modified_response[total_sent:])
                    if sent == 0:
                        raise RuntimeError("Client connection closed")
                    total_sent += sent
            except (ConnectionResetError, BrokenPipeError):
                print("Client closed connection prematurely")

        except socket.timeout:
            print("Connection timed out")
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            try:
                if target_socket:
                    target_socket.shutdown(socket.SHUT_RDWR)
                    target_socket.close()
            except OSError:
                pass
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except OSError:
                pass

    def receive_full_response(self, sock):
        response = b''
        try:
            while True:
                chunk = sock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                response += chunk
                # Check for end of headers
                if b'\r\n\r\n' in response:
                    headers, _, body = response.partition(b'\r\n\r\n')
                    content_length = self.get_content_length(headers)
                    if content_length is not None:
                        while len(body) < content_length:
                            body += sock.recv(BUFFER_SIZE)
                        response = headers + b'\r\n\r\n' + body
                        break
        except socket.timeout:
            print("Timeout while receiving response")
        return response

    def get_content_length(self, headers):
        for line in headers.split(b'\r\n'):
            if line.lower().startswith(b'content-length:'):
                try:
                    return int(line.split(b':')[1].strip())
                except ValueError:
                    return None
        return None

    def process_response(self, response_bytes, request_str):
        headers, _, body = response_bytes.partition(b'\r\n\r\n')
        content_type = self.get_header_value(headers, b'Content-Type')

        # Handle HTML responses
        if content_type and b'text/html' in content_type:
            try:
                charset = self.detect_charset(headers)
                html = body.decode(charset, errors='replace')
                modified_html = self.replace_html_images(html)
                modified_body = modified_html.encode(charset)
                headers = self.update_content_length(headers, len(modified_body))
                return headers + b'\r\n\r\n' + modified_body
            except Exception as e:
                print(f"HTML processing error: {str(e)}")
                return response_bytes

        # Handle image responses
        if content_type and content_type.startswith(b'image/'):
            if random.random() < 0.5 and self.memes:
                return self.replace_image_response(headers)

        return response_bytes

    def replace_html_images(self, html):
        new_html = []
        i = 0
        while i < len(html):
            img_start = html.find('<img', i)
            if img_start == -1:
                new_html.append(html[i:])
                break
            
            new_html.append(html[i:img_start])
            tag_end = html.find('>', img_start)
            
            if tag_end == -1:
                new_html.append(html[img_start:])
                break
                
            full_tag = html[img_start:tag_end+1]
            modified_tag = self.process_img_tag(full_tag)
            new_html.append(modified_tag)
            i = tag_end + 1
            
        return ''.join(new_html)

    def process_img_tag(self, tag):
        if random.random() >= 0.5 or not self.memes:
            return tag

        src_index = tag.lower().find(' src=')
        if src_index == -1:
            return tag

        return self.inject_meme_src(tag, src_index)

    def inject_meme_src(self, tag, src_index):
        meme_path = random.choice(self.memes)
        with open(meme_path, 'rb') as f:
            meme_data = f.read()
        base64_data = base64.b64encode(meme_data).decode('utf-8')
        ext = os.path.splitext(meme_path)[1].lower()
        content_type = "image/jpeg" if ext in ('.jpg', '.jpeg') else "image/png"
        
        new_src = f'src="data:{content_type};base64,{base64_data}"'
        return tag[:src_index] + new_src + tag[src_index + len(new_src):]

    def replace_image_response(self, original_headers):
        try:
            meme_path = random.choice(self.memes)
            with open(meme_path, 'rb') as f:
                meme_data = f.read()
            
            content_type = b'image/jpeg' if meme_path.lower().endswith(('.jpg', '.jpeg')) else \
                            b'image/png' if meme_path.lower().endswith('.png') else \
                            b'image/gif'

            new_headers = []
            for line in original_headers.split(b'\r\n'):
                if line.startswith(b'Content-Type:'):
                    new_headers.append(b'Content-Type: ' + content_type)
                elif line.startswith(b'Content-Length:'):
                    new_headers.append(b'Content-Length: ' + str(len(meme_data)).encode())
                else:
                    new_headers.append(line)
            
            return b'\r\n'.join(new_headers) + b'\r\n\r\n' + meme_data
        except Exception as e:
            print(f"Image replacement failed: {str(e)}")
            return original_headers + b'\r\n\r\n'

    # Keep Easter egg function unchanged
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
                <h1 style="text-align:center; margin-top:20px;">Capybara Suprise!</h1>
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

    # Helper methods
    def extract_host(self, request_str):
        for line in request_str.split('\r\n'):
            if line.startswith('Host:'):
                return line.split(' ')[1].strip()
        return None

    def get_header_value(self, headers, target):
        for line in headers.split(b'\r\n'):
            if line.lower().startswith(target.lower() + b':'):
                return line.split(b':')[1].strip()
        return None

    def detect_charset(self, headers):
        content_type = self.get_header_value(headers, b'Content-Type')
        if content_type:
            parts = content_type.decode().split('charset=')
            if len(parts) > 1:
                return parts[-1].strip().lower()
        return 'utf-8'

    def update_content_length(self, headers, new_length):
        new_headers = []
        found = False
        for line in headers.split(b'\r\n'):
            if line.lower().startswith(b'content-length:'):
                new_headers.append(f"Content-Length: {new_length}".encode())
                found = True
            else:
                new_headers.append(line)
        if not found:
            new_headers.append(f"Content-Length: {new_length}".encode())
        return b'\r\n'.join(new_headers)

if __name__ == "__main__":
    proxy = MemeProxyServer('127.0.0.1', 8080)
    proxy.start()