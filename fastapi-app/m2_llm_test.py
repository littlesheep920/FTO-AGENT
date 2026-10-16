"""M2 LLM 路径测试：真实调用 DeepSeek，验证 fact/planner 走 LLM 而非规则引擎。"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
BASE = "http://127.0.0.1:9093"

env = dict(os.environ)
env["DB_ENGINE"] = "tortoise.backends.sqlite"
env["DB_NAME"] = "data/m2_llm_test.sqlite3"
env["AUTO_CREATE_SCHEMA"] = "1"
# 显式启用 LLM（settings 也会回退到 DEEPSEEK_API_KEY）
env["LLM_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY", "")

db = os.path.join(HERE, "data", "m2_llm_test.sqlite3")
if os.path.exists(db):
    try:
        os.remove(db)
    except OSError:
        pass

proc = subprocess.Popen(
    [VENV_PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "9093"],
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


def req(method, path, data=None, token=None, timeout=90):
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
        "title": "控弯导管 FTO（LLM 路径）",
        "product_description": "一种控弯导管，远端可弯曲段由拉线机构控制弯曲方向，管体材料为聚氨酯，外径3mm",
    }, token=token)
    aid = res[1]["data"]["id"]
    print(f"创建分析 id={aid}")

    r = req("POST", f"/api/fto/analysis/{aid}/run", token=token, timeout=120)
    d = r[1].get("data") or {}
    print(f"run -> code={r[1].get('code')} status={d.get('status')} degraded={d.get('degraded')}")

    r = req("GET", f"/api/fto/analysis/{aid}/facts", token=token)
    facts = r[1]["data"] or []
    print(f"facts 数量={len(facts)}")
    for f in facts:
        print(f"  - [{f['feature_type']}] {f['feature']} = {str(f['value'])[:40]}  unknown={f['is_unknown']}")

    r = req("GET", f"/api/fto/analysis/{aid}/dossier", token=token)
    md = r[1]["data"].get("dossier_markdown", "")
    print(f"\nDossier 摘要段：")
    print("\n".join(md.split("\n")[:8]))

    print("\nM2 LLM TEST DONE")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
