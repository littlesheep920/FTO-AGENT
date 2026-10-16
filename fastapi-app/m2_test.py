"""M2 冒烟测试：自包含起停服务，验证 Agent 编排链路（无 LLM Key → 规则引擎降级）。"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
BASE = "http://127.0.0.1:9092"

env = dict(os.environ)
env["DB_ENGINE"] = "tortoise.backends.sqlite"
env["DB_NAME"] = "data/m2_test.sqlite3"
env["AUTO_CREATE_SCHEMA"] = "1"
env["LLM_API_KEY"] = ""
env.pop("DEEPSEEK_API_KEY", None)  # 确保走规则引擎降级路径

db = os.path.join(HERE, "data", "m2_test.sqlite3")
if os.path.exists(db):
    try:
        os.remove(db)
    except OSError:
        pass

proc = subprocess.Popen(
    [VENV_PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "9092"],
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
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def login(username, password):
    return req("POST", "/api/auth/login", {"username": username, "password": password})[1]["data"]["token"]


try:
    token = login("admin", "admin123")

    # ---- 路径 A：完整流水线（描述含"弯/拉线"，不触发追问）----
    res = req("POST", "/api/fto/analysis", {
        "title": "控弯导管 FTO（完整链路）",
        "product_description": "一种控弯导管，远端可弯曲段由拉线机构控制弯曲方向，管体材料为聚氨酯",
    }, token=token)
    aid = res[1]["data"]["id"]
    print(f"[A] 创建分析 id={aid}")

    r = req("POST", f"/api/fto/analysis/{aid}/run", token=token)
    d = r[1]["data"]
    print(f"[A] run -> code={r[1]['code']} status={d.get('status')} dossier_keys={list(d.get('dossier', {}).keys()) if d.get('dossier') else None}")

    r = req("GET", f"/api/fto/analysis/{aid}/status", token=token)
    print(f"[A] status -> {r[1]['data']}")

    r = req("GET", f"/api/fto/analysis/{aid}/dossier", token=token)
    md = r[1]["data"].get("dossier_markdown", "")
    print(f"[A] dossier markdown 长度={len(md)}，含'执行摘要'={'执行摘要' in md}")

    # 检查 agent_run_log 是否记录了各节点
    r = req("GET", "/api/fto/agent/logs?size=20", token=token)
    nodes = [x["node"] for x in r[1]["data"]["records"] if x.get("analysis_id") == aid]
    print(f"[A] agent_logs 节点序列: {nodes}")

    # ---- 路径 B：触发追问闭环（描述不含"弯/控"）----
    res = req("POST", "/api/fto/analysis", {
        "title": "介入器械 FTO（追问闭环）",
        "product_description": "一种用于血管介入的手术器械",
    }, token=token)
    bid = res[1]["data"]["id"]
    r = req("POST", f"/api/fto/analysis/{bid}/run", token=token)
    print(f"[B] run 原始响应: code={r[1].get('code')} msg={r[1].get('msg')} data={r[1].get('data')}")
    d = r[1].get("data") or {}
    questions = d.get("questions", [])
    print(f"[B] run -> status={d.get('status')} need_clarification={d.get('need_clarification')} questions={questions}")

    if d.get("need_clarification"):
        questions = d.get("questions", [])
        print(f"[B] run -> status={d.get('status')} need_clarification=True questions={questions}")
        # 提交答案：为每个未知项回填
        answers = [{"fact_id": q["fact_id"], "answer": "拉线机构控制弯曲"} for q in questions]
        r = req("POST", f"/api/fto/analysis/{bid}/clarify", {"answers": answers}, token=token)
        d2 = r[1]["data"]
        print(f"[B] clarify -> code={r[1]['code']} status={d2.get('status')} dossier={'dossier' in d2}")
    else:
        print("[B] 未触发追问（意外）")

    print("\nM2 SMOKE DONE")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
