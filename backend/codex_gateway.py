"""Fixed OpenAI Responses proxy for isolated Codex runs.

The host worker owns the real API key. The sandbox reaches this server through
one mounted Unix socket; only ``/v1/responses`` and one configured model are
forwarded, and every request consumes the same per-run cumulative budget.
"""
from __future__ import annotations

import http.server
import json
from pathlib import Path
import socket
import socketserver
import threading
import urllib.error
import urllib.request

from .model_gateway import NoRedirect, configured_proxies


UPSTREAM="https://api.openai.com/v1/responses"
MAX_REQUEST_BYTES=8*1024**2


class _UnixHTTPServer(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
    daemon_threads=True


class CodexGateway:
    def __init__(self,path:Path|str,api_key:str,model:str,*,max_requests:int,
                 max_output_tokens:int=4096,opener=None):
        if not isinstance(api_key,str) or not api_key:
            raise ValueError("OpenAI API key is unavailable to the trusted worker")
        if not isinstance(model,str) or not model or len(model)>120:
            raise ValueError("Codex model is not configured")
        if not isinstance(max_requests,int) or max_requests<1:
            raise ValueError("Codex request budget must be positive")
        if not isinstance(max_output_tokens,int) or not 1<=max_output_tokens<=32768:
            raise ValueError("Codex output-token budget is invalid")
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path.unlink(missing_ok=True)
        self.api_key=api_key
        self.model=model
        self.max_requests=max_requests
        self.max_output_tokens=max_output_tokens
        self.requests=0
        self.lock=threading.Lock()
        self.audit=[]
        self.active_sockets=set()
        self.closed=False
        self.opener=opener or urllib.request.build_opener(
            urllib.request.ProxyHandler(configured_proxies()),NoRedirect())
        gateway=self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version="HTTP/1.0"
            def log_message(self,*_):
                pass

            def _reject(self,status:int,message:str):
                body=json.dumps({"error":{"message":message,"type":"gateway_policy"}}).encode()
                self.send_response(status)
                self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self._reject(403,"endpoint denied")

            def do_CONNECT(self):
                self._reject(403,"tunnel denied")

            def do_POST(self):
                if self.path!="/v1/responses":
                    self._reject(403,"endpoint denied")
                    return
                try:
                    length=int(self.headers.get("Content-Length","0"))
                    if not 0<length<=MAX_REQUEST_BYTES:
                        raise ValueError("request size limit")
                    value=json.loads(self.rfile.read(length))
                    if not isinstance(value,dict) or value.get("model")!=gateway.model:
                        raise ValueError("model denied")
                    if value.get("stream") is not True:
                        raise ValueError("streaming responses are required")
                    maximum=value.get("max_output_tokens",gateway.max_output_tokens)
                    if not isinstance(maximum,int) or maximum<1:
                        raise ValueError("invalid output budget")
                    value["max_output_tokens"]=min(maximum,gateway.max_output_tokens)
                    with gateway.lock:
                        if gateway.closed:
                            self._reject(503,"gateway closed")
                            return
                        if gateway.requests>=gateway.max_requests:
                            self._reject(429,"cumulative model request budget exhausted")
                            return
                        gateway.requests+=1
                        number=gateway.requests
                except (ValueError,TypeError,UnicodeError,json.JSONDecodeError):
                    self._reject(403,"request rejected by gateway policy")
                    return

                body=json.dumps(value,separators=(",",":")).encode()
                request=urllib.request.Request(UPSTREAM,body,
                    {"Content-Type":"application/json","Accept":"text/event-stream",
                     "Authorization":"Bearer "+gateway.api_key},method="POST")
                record={"request":number,"model":gateway.model,"input_bytes":length,
                        "max_output_tokens":value["max_output_tokens"]}
                gateway.audit.append(record)
                try:
                    upstream=gateway.opener.open(request,timeout=180)
                except urllib.error.HTTPError as error:
                    upstream=error
                except Exception as error:
                    record["error_type"]=type(error).__name__
                    self._reject(502,"model transport failed")
                    return
                outbound=getattr(getattr(getattr(upstream,"fp",None),"raw",None),"_sock",None)
                if outbound:
                    with gateway.lock:
                        gateway.active_sockets.add(outbound)
                with upstream:
                    record["http_status"]=upstream.code
                    self.send_response(upstream.code)
                    self.send_header("Content-Type",upstream.headers.get("Content-Type","application/json"))
                    self.end_headers()
                    try:
                        while True:
                            chunk=upstream.read1(16384)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            self.wfile.flush()
                    except (OSError,ValueError):
                        record["client_disconnected"]=True
                    finally:
                        if outbound:
                            with gateway.lock:
                                gateway.active_sockets.discard(outbound)

        self.server=_UnixHTTPServer(str(self.path),Handler)
        self.path.chmod(0o600)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        with self.lock:
            self.closed=True
            active=list(self.active_sockets)
        for sock in active:
            try:sock.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        self.server.shutdown()
        self.server.server_close()
        self.path.unlink(missing_ok=True)

    def request_count(self)->int:
        with self.lock:
            return self.requests
