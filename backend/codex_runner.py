"""Sandbox-local HTTP-to-Unix bridge and Codex child process launcher."""
from __future__ import annotations

import argparse
from http.client import HTTPConnection
import http.server
import json
import socket
import socketserver
import subprocess
import sys
import threading


class UnixHTTPConnection(HTTPConnection):
    def __init__(self,path:str):
        super().__init__("localhost")
        self.unix_path=path

    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.connect(self.unix_path)


def main()->int:
    if "--" not in sys.argv:
        raise SystemExit("missing Codex command separator")
    separator=sys.argv.index("--")
    parser=argparse.ArgumentParser()
    parser.add_argument("--socket",required=True)
    parser.add_argument("--port",required=True,type=int)
    options=parser.parse_args(sys.argv[1:separator])
    command=sys.argv[separator+1:]
    if not command:
        raise SystemExit("missing Codex command")

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version="HTTP/1.0"
        def log_message(self,*_):pass

        def _reject(self,status:int,message:str):
            body=json.dumps({"error":{"message":message,"type":"local_proxy"}}).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers();self.wfile.write(body)

        def do_GET(self):self._reject(403,"endpoint denied")
        def do_CONNECT(self):self._reject(403,"tunnel denied")

        def do_POST(self):
            if self.path!="/v1/responses":
                self._reject(403,"endpoint denied");return
            try:length=int(self.headers.get("Content-Length","0"))
            except ValueError:
                self._reject(400,"invalid content length");return
            if not 0<length<=8*1024**2:
                self._reject(413,"request size limit");return
            body=self.rfile.read(length)
            connection=UnixHTTPConnection(options.socket)
            try:
                connection.request("POST",self.path,body,
                    {"Content-Type":"application/json","Content-Length":str(len(body)),
                     "Connection":"close"})
                response=connection.getresponse()
                self.send_response(response.status)
                self.send_header("Content-Type",response.getheader("Content-Type","application/json"))
                self.end_headers()
                while True:
                    chunk=response.read1(16384)
                    if not chunk:break
                    self.wfile.write(chunk);self.wfile.flush()
            except OSError:
                self._reject(502,"supervisor gateway unavailable")
            finally:
                connection.close()

    class Server(socketserver.ThreadingMixIn,http.server.HTTPServer):
        daemon_threads=True
        allow_reuse_address=False

    server=Server(("127.0.0.1",options.port),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    prompt=sys.stdin.buffer.read()
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,bufsize=0)
    assert process.stdin and process.stdout and process.stderr
    process.stdin.write(prompt);process.stdin.close()

    def forward(source,destination):
        while True:
            chunk=source.read(65536)
            if not chunk:break
            destination.write(chunk);destination.flush()

    stdout_thread=threading.Thread(target=forward,args=(process.stdout,sys.stdout.buffer),daemon=True)
    stderr_thread=threading.Thread(target=forward,args=(process.stderr,sys.stderr.buffer),daemon=True)
    stdout_thread.start();stderr_thread.start()
    code=process.wait()
    stdout_thread.join();stderr_thread.join()
    server.shutdown();server.server_close()
    return code


if __name__=="__main__":
    raise SystemExit(main())
