import http.client
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
import urllib.error
from backend.model_gateway import (Gateway, UPSTREAM, classify_gateway_failure,
                                  configured_proxies, gateway_forwarded_request_count)

class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__('localhost')
        self.path=path
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.connect(str(self.path))

class Response(io.BytesIO):
    code=200
    headers={'Content-Type':'text/event-stream'}

class Opener:
    def __init__(self):
        self.requests=[]
    def open(self,request,timeout):
        self.requests.append(request)
        return Response(b'event: done\ndata: {}\n\n')

class ForbiddenOpener:
    def open(self,request,timeout):
        raise urllib.error.HTTPError(request.full_url,403,'forbidden',
                                     {'Content-Type':'application/json'},
                                     io.BytesIO(b'{"error":"forbidden"}'))

class GatewayTests(unittest.TestCase):
    def test_proxy_configuration_prefers_environment_without_logging(self):
        env={"https_proxy":"http://env-proxy.invalid:9000"}
        config={"http":"http://config-proxy.invalid:8000","https":"environment"}
        self.assertEqual(configured_proxies(env,config),{
            "http":"http://config-proxy.invalid:8000","https":"http://env-proxy.invalid:9000"})
        self.assertEqual(configured_proxies({},config),{"http":"http://config-proxy.invalid:8000"})

    def test_fixed_endpoint_model_and_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway=Gateway(Path(directory)/'api.sock','secret-not-for-agent','allowed',max_requests=1,max_output_tokens=32768)
            gateway.opener=Opener();gateway.start()
            def post(path,value):
                connection=UnixConnection(gateway.path)
                connection.request('POST',path,json.dumps(value),{'Content-Type':'application/json'})
                result=connection.getresponse();data=result.read();connection.close()
                return result.status,data
            try:
                self.assertEqual(post('/proxy?url=https://example.org',{})[0],403)
                self.assertEqual(post('/anthropic/v1/messages',{'model':'wrong','messages':[]})[0],403)
                self.assertEqual(gateway.audit[0]['reason'],'endpoint_denied')
                self.assertEqual(gateway.audit[1]['reason'],'model_denied')
                value={'model':'allowed','messages':[],'max_tokens':99999}
                self.assertEqual(post('/anthropic/v1/messages',value)[0],200)
                request=gateway.opener.requests[0]
                self.assertEqual(request.full_url,UPSTREAM)
                self.assertEqual(json.loads(request.data)['max_tokens'],32768)
                self.assertEqual(request.get_header('X-api-key'),'secret-not-for-agent')
                status,body=post('/anthropic/v1/messages',value)
                self.assertEqual(status,429)
                self.assertEqual(json.loads(body)['reason'],'request_budget_exhausted')
                self.assertEqual(gateway.audit[-1],{
                    'source':'local_policy','reason':'request_budget_exhausted',
                    'used':1,'limit':1,'http_status':429})
                self.assertEqual(classify_gateway_failure(gateway.audit)['failure_kind'],
                                 'local_request_budget_exhausted')
                self.assertEqual(gateway_forwarded_request_count(gateway.audit),1)
                self.assertNotIn('secret-not-for-agent',json.dumps(gateway.audit))
            finally:
                gateway.close()

    def test_upstream_403_is_not_misclassified_as_local_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway=Gateway(Path(directory)/'api.sock','key','allowed',max_requests=2)
            gateway.opener=ForbiddenOpener();gateway.start()
            try:
                connection=UnixConnection(gateway.path)
                connection.request('POST','/anthropic/v1/messages',
                    json.dumps({'model':'allowed','messages':[]}),
                    {'Content-Type':'application/json'})
                response=connection.getresponse();self.assertEqual(response.status,403)
                response.read();connection.close()
                self.assertEqual(gateway.audit[-1]['source'],'upstream')
                self.assertEqual(gateway.audit[-1]['reason'],'upstream_http_403')
                self.assertEqual(gateway.audit[-1]['used'],1)
                self.assertEqual(gateway.audit[-1]['limit'],2)
                classification=classify_gateway_failure(gateway.audit)
                self.assertEqual(classification['failure_kind'],'upstream_http_403')
                self.assertEqual(classification['source'],'upstream')
            finally:
                gateway.close()

    def test_legacy_auth_at_cap_is_labeled_as_an_inference(self):
        audit=[{'request':n,'http_status':200} for n in range(1,4)]
        outcome={'kind':'error','error':{'code':'AUTH','status':403}}
        classification=classify_gateway_failure(audit,request_limit=3,agent_outcome=outcome)
        self.assertEqual(classification['failure_kind'],'local_request_budget_exhausted')
        self.assertEqual(classification['source'],'inferred_local_policy')
        self.assertEqual(classification['evidence_level'],'inferred')
        self.assertEqual(classification['used'],3)
        self.assertEqual(classification['limit'],3)
        self.assertIsNone(classify_gateway_failure(audit,request_limit=4,agent_outcome=outcome))
        self.assertEqual(gateway_forwarded_request_count(audit),3)
        upstream_failure=classify_gateway_failure(
            [{'request':1,'http_status':403}],request_limit=1,agent_outcome=outcome)
        self.assertEqual(upstream_failure['source'],'upstream')
        self.assertEqual(upstream_failure['failure_kind'],'upstream_http_403')
