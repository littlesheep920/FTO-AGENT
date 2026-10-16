"""M3 测试：mock 数据源跑通完整流水线（检索 → 家族 → 法律状态 → Dossier）。"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
BASE = "http://127.0.0.1:9094"

env = dict(os.environ)
env["DB_ENGINE"] = "tortoise.backends.sqlite"
env["DB_NAME"] = "data/m3_test.sqlite3"
env["AUTO_CREATE_SCHEMA"] = "1"
env["LLM_API_KEY"] = ""
env.pop("DEEPSEEK_API_KEY", None)
env["PATENT_SOURCES"] = "mock"   # 演示源

db = os.path.join(HERE, "data", "m3_test.sqlite3")
if os.path.exists(db):
    try:
        os.remove(db)
    except OSError:
        pass

proc = subprocess.Popen(
    [VENV_PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "9094"],
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


def req(method, path, data=None, token=None, timeout=60):
    body = json.dumps(data, ensure_ascii=True).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("token", token)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def login(u, p):
    return req("POST", "/api/auth/login", {"username": u, "password": p})[1]["data"]["token"]


try:
    token = login("admin", "admin123")
    res = req("POST", "/api/fto/analysis", {
        "title": "控弯导管 FTO（M3 mock 检索）",
        "product_description": "一种控弯导管，远端可弯曲段由拉线机构控制弯曲方向，管体材料为聚氨酯",
    }, token=token)
    aid = res[1]["data"]["id"]

    r = req("POST", f"/api/fto/analysis/{aid}/run", token=token)
    d = r[1].get("data") or {}
    print(f"run -> code={r[1].get('code')} status={d.get('status')} degraded={d.get('degraded')}")

    r = req("GET", f"/api/fto/analysis/{aid}/status", token=token)
    print(f"status -> {r[1]['data']}")

    r = req("GET", f"/api/fto/analysis/{aid}/dossier", token=token)
    md = r[1]["data"].get("dossier_markdown", "")
    rs = r[1]["data"].get("risk_summary")
    print(f"risk_summary -> {rs}")
    print(f"dossier 含演示标记={'演示数据' in md}，含示例专利={'CN115000001A' in md}")
    # 统计专利表格行数
    import re
    rows = re.findall(r"^\| CN\d", md, re.M)
    print(f"专利清单行数={len(rows)}")
    print("\n--- Dossier 第 3 板块（专利清单）---")
    for line in md.split("\n"):
        if line.startswith("| CN") or line.startswith("| 专利号") or line.startswith("| ---") or "演示数据" in line:
            print(line)

    print("\nM3 SMOKE DONE")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
