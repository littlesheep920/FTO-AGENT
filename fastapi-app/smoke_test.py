"""临时冒烟测试 v3：自包含（Python 起停服务 + urllib 打接口）。"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
BASE = "http://127.0.0.1:9091"

env = dict(os.environ)
env["DB_ENGINE"] = "tortoise.backends.sqlite"
env["DB_NAME"] = "data/smoke_test.sqlite3"
env["AUTO_CREATE_SCHEMA"] = "1"

db = os.path.join(HERE, "data", "smoke_test.sqlite3")
if os.path.exists(db):
    try:
        os.remove(db)
    except OSError:
        pass

proc = subprocess.Popen(
    [VENV_PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "9091"],
    cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

ready = False
for _ in range(40):
    try:
        urllib.request.urlopen(BASE + "/", timeout=1)
        ready = True
        break
    except Exception:
        time.sleep(0.5)
if not ready:
    print("SERVER NOT READY")
    proc.terminate()
    sys.exit(1)


def req(method, path, data=None, token=None):
    body = json.dumps(data, ensure_ascii=True).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("token", token)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def show(label, res):
    status, body = res
    code = body.get("code") if isinstance(body, dict) else None
    data = body.get("data") if isinstance(body, dict) else None
    keys = list(data.keys()) if isinstance(data, dict) else None
    print(f"[{label}] HTTP {status} code={code} msg={body.get('msg') if isinstance(body, dict) else body} data_keys={keys}")


try:
    show("root", req("GET", "/"))
    res = req("POST", "/api/auth/register", {"username": "tester", "password": "123456", "nickname": "测试用户"})
    show("register", res)
    token = (res[1].get("data") or {}).get("token")
    if not token:
        res = req("POST", "/api/auth/login", {"username": "tester", "password": "123456"})
        show("login", res)
        token = (res[1].get("data") or {}).get("token")
    print("token:", (token or "")[:24] + "...")

    show("user/info", req("GET", "/api/user/info", token=token))
    res = req("POST", "/api/fto/analysis", {"title": "控弯导管 FTO 测试", "product_description": "一种控弯导管，远端可弯曲段由拉线机构控制弯曲方向"}, token=token)
    show("create-analysis", res)
    show("analysis/list", req("GET", "/api/fto/analysis/list", token=token))
    aid = (res[1].get("data") or {}).get("id")
    show("analysis/detail", req("GET", f"/api/fto/analysis/{aid}", token=token))
    show("run-stub", req("POST", f"/api/fto/analysis/{aid}/run", token=token))

    admin_token = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})[1]["data"]["token"]
    show("admin/prompt", req("GET", "/api/fto/prompt", token=admin_token))
    show("admin/llm-config", req("GET", "/api/fto/llm/config", token=admin_token))
    show("admin/agent-logs", req("GET", "/api/fto/agent/logs", token=admin_token))
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

print("SMOKE DONE")
