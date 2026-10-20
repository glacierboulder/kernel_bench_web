"""A per-run Unix socket gateway. Only fixed DeepSeek Messages is reachable.
Real credentials stay in this host process. No HTTP CONNECT, URLs, or redirects.
"""
import http.server
import json
from pathlib import Path
import socket
import socketserver
import threading
import urllib.error
import urllib.request
import os
from .settings import SETTINGS

from .dsh_config import output_token_limit

UPSTREAM = 'https://api.deepseek.com/anthropic/v1/messages'


def classify_gateway_failure(audit, request_limit=None, agent_outcome=None):
    """Classify a failed model call from gateway evidence, not CLI wording alone.

    Older audit files contain only forwarded requests. For those files, a CLI
    AUTH/403 at an exhausted local cap is reported as an inference, never as a
    directly observed gateway rejection.
    """
    if not isinstance(audit, list) or not audit:
        return None
    last = audit[-1] if isinstance(audit[-1], dict) else {}
    source = last.get('source')
    if source == 'local_policy':
        reason = last.get('reason', 'unspecified')
        failure_kind = ('local_request_budget_exhausted'
                        if reason == 'request_budget_exhausted'
                        else 'local_gateway_policy_rejected')
        return {
            'failure_kind': failure_kind,
            'source': source,
            'reason': reason,
            'used': last.get('used'),
            'limit': last.get('limit'),
            'evidence_level': 'direct',
        }
    # The legacy audit schema recorded entries only after forwarding, so an
    # HTTP status on an untagged record is also direct upstream evidence.
    status = last.get('http_status')
    if (source in ('upstream', None) and isinstance(status, int)
            and status >= 400):
        return {
            'failure_kind': f'upstream_http_{status}',
            'source': 'upstream',
            'reason': last.get('reason') or f'upstream_http_{status}',
            'http_status': status,
            'used': last.get('used'),
            'limit': last.get('limit'),
            'evidence_level': 'direct',
        }

    # Pre-schema-upgrade runs did not audit locally rejected requests. Infer
    # the likely cap only when all saved requests were forwarded, the cap was
    # reached, and DSH reported the exact AUTH/403 outcome.
    if (request_limit and len(audit) >= request_limit
            and all(isinstance(item, dict) and 'source' not in item
                    and isinstance(item.get('http_status'), int)
                    and 200 <= item['http_status'] < 400 for item in audit)
            and isinstance(agent_outcome, dict)
            and agent_outcome.get('kind') == 'error'
            and isinstance(agent_outcome.get('error'), dict)
            and agent_outcome['error'].get('code') == 'AUTH'
            and agent_outcome['error'].get('status') == 403):
        return {
            'failure_kind': 'local_request_budget_exhausted',
            'source': 'inferred_local_policy',
            'reason': 'legacy_audit_at_limit_with_cli_auth_403_and_no_failed_upstream_record',
            'used': len(audit),
            'limit': request_limit,
            'evidence_level': 'inferred',
        }
    return None


def gateway_forwarded_request_count(audit):
    """Count requests admitted to the provider; local denials are not calls."""
    if not isinstance(audit, list):
        return 0
    if any(isinstance(item, dict) and 'source' in item for item in audit):
        return sum(1 for item in audit
                   if isinstance(item, dict) and item.get('source') == 'upstream')
    # Legacy audit schema recorded only requests sent upstream.
    return len(audit)

def configured_proxies(environ=None, config=None):
    """Resolve proxy URLs from environment first, then the deployment JSON."""
    environ=os.environ if environ is None else environ
    config=SETTINGS.config.get('proxies',{}) if config is None else config
    values={}
    for scheme in ('http','https'):
        configured=(environ.get(f'{scheme}_proxy') or environ.get(f'{scheme.upper()}_PROXY'))
        if not configured:
            candidate=config.get(scheme) if isinstance(config,dict) else None
            configured=candidate if isinstance(candidate,str) and candidate.lower()!='environment' else None
        if configured:
            values[scheme]=configured
    return values

class UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

class Gateway:
    def __init__(self, path, key, model, max_requests=60, max_output_tokens=None):
        self.path, self.key, self.model = Path(path), key, model
        self.max_output_tokens = output_token_limit(max_output_tokens)
        self.max_requests, self.requests = max_requests, 0
        self.lock = threading.Lock()
        self.audit = []
        self.active_sockets = set()
        self.closed = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler(configured_proxies()), NoRedirect())
        gateway = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.0'
            def log_message(self, *_):
                pass

            def reject(self, status, reason):
                with gateway.lock:
                    gateway.audit.append({
                        'source': 'local_policy', 'reason': reason,
                        'used': gateway.requests, 'limit': gateway.max_requests,
                        'http_status': status,
                    })
                body = json.dumps({'type': 'gateway_policy_error', 'reason': reason}).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self.reject(403, 'endpoint_denied')

            def do_CONNECT(self):
                self.reject(403, 'tunnel_denied')

            def do_POST(self):
                if self.path not in ('/anthropic/v1/messages', '/v1/messages'):
                    self.reject(403, 'endpoint_denied')
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 8 * 1024**2:
                        self.reject(413, 'request_size_invalid')
                        return
                    try:
                        value = json.loads(self.rfile.read(length))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        self.reject(400, 'invalid_json')
                        return
                    if not isinstance(value, dict):
                        self.reject(400, 'invalid_request')
                        return
                    if value.get('model') != gateway.model:
                        self.reject(403, 'model_denied')
                        return
                    if not isinstance(value.get('messages'), list):
                        self.reject(400, 'invalid_messages')
                        return
                    maximum = value.get('max_tokens', gateway.max_output_tokens)
                    if not isinstance(maximum, int) or maximum < 1:
                        self.reject(400, 'invalid_output_budget')
                        return
                    value['max_tokens'] = min(maximum, gateway.max_output_tokens)
                except (ValueError, TypeError):
                    self.reject(400, 'invalid_request')
                    return
                with gateway.lock:
                    if gateway.closed:
                        rejected = 'gateway_closed'
                        number = None
                    elif gateway.requests >= gateway.max_requests:
                        rejected = 'request_budget_exhausted'
                        number = None
                    else:
                        rejected = None
                        gateway.requests += 1
                        number = gateway.requests
                        record = {'request': number, 'source': 'upstream', 'reason': None,
                                  'used': number, 'limit': gateway.max_requests,
                                  'model': gateway.model, 'input_bytes': length,
                                  'max_tokens': value['max_tokens']}
                        gateway.audit.append(record)
                if rejected:
                    self.reject(503 if rejected == 'gateway_closed' else 429, rejected)
                    return
                headers = {'Content-Type': 'application/json', 'x-api-key': gateway.key,
                           'anthropic-version': '2023-06-01', 'Accept': 'text/event-stream'}
                for name in ['anthropic-beta', 'x-deepseek-harness-session-id', 'x-deepseek-harness-compact']:
                    if self.headers.get(name):
                        headers[name] = self.headers[name]
                req = urllib.request.Request(UPSTREAM, json.dumps(value).encode(), headers, method='POST')
                try:
                    upstream = gateway.opener.open(req, timeout=180)
                except urllib.error.HTTPError as error:
                    upstream = error
                except Exception as error:
                    record['reason'] = 'upstream_transport_error'
                    record['error_type'] = type(error).__name__
                    self.send_error(502, 'model transport failed')
                    return
                outbound_socket = getattr(getattr(getattr(upstream, 'fp', None), 'raw', None), '_sock', None)
                if outbound_socket:
                    with gateway.lock:
                        gateway.active_sockets.add(outbound_socket)
                with upstream:
                    record['http_status'] = upstream.code
                    if not 200 <= upstream.code < 300:
                        record['reason'] = f'upstream_http_{upstream.code}'
                    self.send_response(upstream.code)
                    self.send_header('Content-Type', upstream.headers.get('Content-Type', 'application/json'))
                    self.end_headers()
                    try:
                        while True:
                            chunk = upstream.read1(16384)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            self.wfile.flush()
                    except (OSError, ValueError):
                        record['client_disconnected'] = True
                    finally:
                        if outbound_socket:
                            with gateway.lock:
                                gateway.active_sockets.discard(outbound_socket)

        self.server = UnixHTTPServer(str(self.path), Handler)
        self.path.chmod(0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        with self.lock:
            self.closed = True
            sockets = list(self.active_sockets)
        for item in sockets:
            try:
                item.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.server.shutdown()
        self.server.server_close()
        self.path.unlink(missing_ok=True)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
