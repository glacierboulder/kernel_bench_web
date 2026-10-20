"""Runs INSIDE the network namespace. TCP loopback -> fixed mounted Unix socket."""
import os
import socket
import socketserver
import subprocess
import sys
import threading

class Bridge(socketserver.BaseRequestHandler):
    def handle(self):
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.connect('/gateway/api.sock')
        def copy(source, dest):
            try:
                while True:
                    data = source.recv(65536)
                    if not data:
                        break
                    dest.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    dest.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
        thread = threading.Thread(target=copy, args=(self.request, upstream), daemon=True)
        thread.start()
        copy(upstream, self.request)
        upstream.close()

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == '__main__':
    host=os.environ.get('BENCH_GATEWAY_HOST','127.0.0.1')
    port=int(os.environ.get('BENCH_GATEWAY_PORT','18991'))
    server = Server((host,port), Bridge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    # No inherited host secrets exist: env is built by bwrap --clearenv.
    raise SystemExit(subprocess.call(sys.argv[1:]))
