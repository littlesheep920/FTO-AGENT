"""M4 测试：完整分析链（LLM 比对）——检索→权要解析→特征比对→风险定级。"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
BASE = "http://127.0.0.1:9096"

env = dict(os.environ)
env["DB_ENGINE"] = "tortoise.backends.sqlite"
env["DB_NAME"] = "data/m4_test.sqlite3"
env["AUTO_CREATE_SCHEMA"] = "1"
env["LLM_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY", "")
env["PATENT_SOURCES"] = "mock"

db = os.path.join(HERE, "data", "m4_test.sqlite3")
if os.path.exists(db):
    try:
        os.remove(db)
    except OSError:
        pass

proc = subprocess.Popen(
    [VENV_PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "9096"],
    cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
for _ in range(40):
    try:
        urllib.request.urlopen(BASE + "/", timeout=1)
        break
    except Exception:
        time.sleep(0.5)


def req(method, path, data=None, token=None, timeout=180):
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


try:
    tok = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})[1]["data"]["token"]
    res = req("POST", "/api/fto/analysis", {
        "title": "控弯导管 FTO（M4 完整分析链）",
        "product_description": "一种控弯导管，远端可弯曲段由拉线机构控制弯曲方向，管体材料为聚氨酯",
    }, token=tok)
    aid = res[1]["data"]["id"]

    r = req("POST", f"/api/fto/analysis/{aid}/run", token=tok, timeout=300)
    d = r[1].get("data") or {}
    if d.get("need_clarification"):
        questions = d.get("questions", [])
        print(f"触发追问: {[q['question'] for q in questions]}")
        answers = [{"fact_id": q["fact_id"], "answer": "未明确（弯曲角度由拉线行程控制，外径2.7mm）"} for q in questions]
        r = req("POST", f"/api/fto/analysis/{aid}/clarify", {"answers": answers}, token=tok, timeout=300)
        d = r[1].get("data") or {}
    print(f"run -> code={r[1].get('code')} status={d.get('status')} degraded={d.get('degraded')}")

    r = req("GET", f"/api/fto/analysis/{aid}/status", token=tok)
    print(f"status -> {r[1]['data']}")

    r = req("GET", f"/api/fto/analysis/{aid}/dossier", token=tok)
    md = r[1]["data"].get("dossier_markdown", "")
    rs = r[1]["data"].get("risk_summary")
    print(f"\n风险分级 -> {rs}")
    print(f"执行摘要: {r[1]['data'].get('executive_summary')[:120]}")
    print("\n--- Dossier 第 4/5/6 板块 ---")
    in_section = False
    for line in md.split("\n"):
        if line.startswith("## 4") or line.startswith("## 5") or line.startswith("## 6"):
            in_section = True
            print(line)
            continue
        if line.startswith("## 7"):
            in_section = False
        if in_section and (line.startswith("|") or line.startswith("-")):
            print(line)

    print("\nM4 TEST DONE")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
