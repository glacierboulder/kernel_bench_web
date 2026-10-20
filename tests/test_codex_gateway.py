import http.client
import json
import socket
import tempfile
import unittest
from pathlib import Path

from backend.codex_gateway import CodexGateway


class _Response:
    code=200
    headers={"Content-Type":"text/event-stream"}
    def __init__(self):self.chunks=[b"data: {\"type\":\"response.completed\"}\n\n"]
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def read1(self,_size):return self.chunks.pop(0) if self.chunks else b""


class _Opener:
    def __init__(self):self.requests=[]
    def open(self,request,timeout):
        self.requests.append((request,timeout))
        return _Response()


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self,path):super().__init__("localhost");self.path=path
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.connect(str(self.path))


class CodexGatewayTests(unittest.TestCase):
    def test_proxy_forwards_only_fixed_model_and_enforces_one_cumulative_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);opener=_Opener()
            gateway=CodexGateway(root/"gateway.sock","TEST_WORKER_SECRET","gpt-test",
                                 max_requests=1,max_output_tokens=256,opener=opener)
            gateway.start()
            try:
                connection=_UnixHTTPConnection(root/"gateway.sock")
                body=json.dumps({"model":"gpt-test","stream":True,"max_output_tokens":900})
                connection.request("POST","/v1/responses",body,
                    {"Content-Type":"application/json","Authorization":"Bearer untrusted"})
                response=connection.getresponse()
                self.assertEqual(response.status,200)
                self.assertIn(b"response.completed",response.read())
                connection.close()
                self.assertEqual(gateway.request_count(),1)
                self.assertEqual(len(opener.requests),1)
                upstream_request,_=opener.requests[0]
                self.assertEqual(upstream_request.get_header("Authorization"),"Bearer TEST_WORKER_SECRET")
                self.assertEqual(json.loads(upstream_request.data)["max_output_tokens"],256)
                self.assertNotIn("TEST_WORKER_SECRET",json.dumps(gateway.audit))

                connection=_UnixHTTPConnection(root/"gateway.sock")
                connection.request("POST","/v1/responses",body,{"Content-Type":"application/json"})
                response=connection.getresponse()
                self.assertEqual(response.status,429)
                self.assertIn(b"budget exhausted",response.read())
                connection.close()
                self.assertEqual(gateway.request_count(),1)
                self.assertEqual(len(opener.requests),1)

                connection=_UnixHTTPConnection(root/"gateway.sock")
                connection.request("POST","/v1/chat/completions",body)
                response=connection.getresponse()
                self.assertEqual(response.status,403)
                connection.close()
                self.assertEqual(gateway.request_count(),1)
            finally:
                gateway.close()


if __name__=="__main__":
    unittest.main()
