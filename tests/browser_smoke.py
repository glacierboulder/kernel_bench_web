"""Optional Firefox UI smoke against a running, configured service."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from backend.settings import SETTINGS


def api_json(base_url: str, path: str, payload: dict | None = None) -> dict:
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    request=Request(base_url.rstrip("/")+path,data=data,
                    headers={"Content-Type":"application/json"} if data is not None else {})
    with urlopen(request,timeout=10) as response:
        return json.loads(response.read())


def main() -> int:
    browser_value = os.environ.get("BENCH_BROWSER", "firefox")
    browser = (str(Path(browser_value).expanduser()) if os.sep in browser_value
               else shutil.which(browser_value))
    if not browser or not Path(browser).is_file():
        print("SKIP: set BENCH_BROWSER or install Firefox to run the browser smoke")
        return 0

    base_url = os.environ.get("BENCH_BROWSER_URL") or (
        f"http://{SETTINGS.host}:{SETTINGS.port}"
    )
    if urlsplit(base_url).scheme not in {"http", "https"}:
        raise ValueError("BENCH_BROWSER_URL must be an HTTP(S) URL")

    with tempfile.TemporaryDirectory(prefix="bench-browser-") as directory:
        profile = Path(directory)
        with socket.socket() as free:
            free.bind(("127.0.0.1", 0))
            port = free.getsockname()[1]
        (profile / "user.js").write_text(
            f'user_pref("marionette.port",{port});\n'
            'user_pref("marionette.host","127.0.0.1");\n',
            encoding="utf-8",
        )
        with (profile / "browser.log").open("w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                [browser, "--headless", "--no-remote", "--marionette", "--profile", str(profile)],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            try:
                for _ in range(100):
                    try:
                        connection = socket.create_connection(("127.0.0.1", port), timeout=2)
                        break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError("Firefox control unavailable: " + (profile / "browser.log").read_text()[-1000:])

                connection.settimeout(30)
                buffer = b""

                def receive():
                    nonlocal buffer
                    while b":" not in buffer:
                        buffer += connection.recv(4096)
                    size, buffer = buffer.split(b":", 1)
                    length = int(size)
                    while len(buffer) < length:
                        buffer += connection.recv(65536)
                    data, buffer = buffer[:length], buffer[length:]
                    return json.loads(data)

                receive()
                sequence = 0

                def call(name, params=None):
                    nonlocal sequence
                    sequence += 1
                    body = json.dumps([0, sequence, name, params or {}]).encode()
                    connection.sendall(str(len(body)).encode() + b":" + body)
                    response = receive()
                    if response[2]:
                        raise RuntimeError(str(response[2]))
                    return response[3]

                call("WebDriver:NewSession", {"capabilities": {}})
                call("WebDriver:Navigate", {"url": base_url.rstrip("/") + "/#overview"})
                for _ in range(50):
                    value = call("WebDriver:ExecuteScript", {
                        "script": "return document.querySelector('#main')?.innerText || '';",
                        "args": [],
                    })["value"]
                    if "让每一次实验" in value:
                        break
                    if "连接工作台" in value:
                        raise RuntimeError("The configured service did not return its API state")
                    time.sleep(.1)
                else:
                    raise AssertionError("Overview page did not render")

                call("WebDriver:Navigate", {"url": base_url.rstrip("/") + "/#tasks"})
                for _ in range(50):
                    value = call("WebDriver:ExecuteScript", {
                        "script": "return document.querySelector('#main')?.innerText || '';",
                        "args": [],
                    })["value"]
                    if "题目与问题组" in value:
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError("Task catalog page did not render")

                filtered = call("WebDriver:ExecuteScript", {
                    "script": "const x=document.querySelector('#search'); x.value='occt-544'; "
                              "x.dispatchEvent(new Event('input',{bubbles:true})); "
                              "return document.querySelectorAll('#task-cards .card').length;",
                    "args": [],
                })["value"]
                if not isinstance(filtered, int) or filtered < 1:
                    raise AssertionError("Task catalog search interaction did not filter results")

                call("WebDriver:Navigate", {"url": base_url.rstrip("/") + "/#agents"})
                for _ in range(50):
                    value = call("WebDriver:ExecuteScript", {
                        "script": "return document.querySelector('#main')?.innerText || '';",
                        "args": [],
                    })["value"]
                    if "Agent 配置" in value and "Codex 已接入 worker" in value:
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError("Agent page did not show the Codex live/credential boundary")

                state=api_json(base_url,"/api/state")
                if not state.get("tasks") or not state.get("agents"):
                    raise AssertionError("Isolated browser fixture has no task or agent")
                task,agent=state["tasks"][0],state["agents"][0]
                demo=api_json(base_url,"/api/runs",{"task_id":task["id"],"task_version":task["version"],
                    "agent_id":agent["id"],"mode":"demo","note":"temporary browser smoke"})
                call("WebDriver:Navigate", {"url":base_url.rstrip("/")+"/?browser-smoke="+demo["id"]+"#run/"+demo["id"]})
                order=None
                for _ in range(50):
                    order=call("WebDriver:ExecuteScript", {
                    "script":"const m=document.querySelector('#main'); "
                             "const s=[...m.querySelectorAll('.notice')].find(x=>x.textContent.includes('演示记录')); "
                             "const c=[...m.querySelectorAll('section.panel')].find(x=>x.querySelector('h2')?.textContent.includes('逐 issue 检查矩阵')); "
                             "return {status:!!s,matrix:!!c,adjacent:!!s&&!!c&&s.nextElementSibling===c, "
                             "next:s?.nextElementSibling?.outerHTML.slice(0,240)||null, "
                             "statusParent:s?.parentElement?.tagName||null,matrixParent:c?.parentElement?.tagName||null, "
                             "statusBeforeMatrix:!!s&&!!c&&!!(s.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)};",
                    "args":[],
                    })["value"]
                    if order.get("status") and order.get("matrix"):
                        break
                    time.sleep(.1)
                if not order.get("adjacent"):
                    raise AssertionError("Run-detail checkpoint matrix ordering mismatch: "+json.dumps(order,ensure_ascii=False))
                call("Marionette:Quit", {"flags": ["eForceQuit"]})
                connection.close()
                print("Firefox rendered overview, task search, Codex configuration boundary, and run-detail checkpoint ordering")
                return 0
            finally:
                if proc.poll() is None:
                    proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
