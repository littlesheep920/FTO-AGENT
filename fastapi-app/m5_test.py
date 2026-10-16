"""M5 测试：Claim 前序修复 + Markdown/PDF 导出。"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
BASE = "http://127.0.0.1:9098"

env = dict(os.environ)
env["DB_ENGINE"] = "tortoise.backends.sqlite"
env["DB_NAME"] = "data/m5_test.sqlite3"
env["AUTO_CREATE_SCHEMA"] = "1"
env["LLM_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY", "")
env["PATENT_SOURCES"] = "mock"

db = os.path.join(HERE, "data", "m5_test.sqlite3")
if os.path.exists(db):
    try:
        os.remove(db)
    except OSError:
        pass

proc = subprocess.Popen(
    [VENV_PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "9098"],
    cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
for _ in range(40):
    try:
        urllib.request.urlopen(BASE + "/", timeout=1)
        break
    except Exception:
        time.sleep(0.5)


def req(method, path, data=None, token=None, timeout=300):
    body = json.dumps(data, ensure_ascii=True).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("token", token)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def req_json(method, path, data=None, token=None, timeout=300):
    status, _, body = req(method, path, data, token, timeout)
    return status, json.loads(body.decode()) if body else {}


try:
    req_json("POST", "/api/auth/register", {"username": "tester", "password": "123456"})
    tok = req_json("POST", "/api/auth/login", {"username": "tester", "password": "123456"})[1]["data"]["token"]
    aid = req_json("POST", "/api/fto/analysis", {
        "title": "控弯导管 FTO（M5 导出测试）",
        "product_description": "一种控弯导管，远端可弯曲段由拉线机构控制弯曲方向，管体材料为聚氨酯，外径2.7mm，弯曲角度0-180度，拉线为单根不锈钢牵引丝",
    }, token=tok)[1]["data"]["id"]

    d = req_json("POST", f"/api/fto/analysis/{aid}/run", token=tok)[1].get("data") or {}
    if d.get("need_clarification"):
        answers = [{"fact_id": q["fact_id"], "answer": "未明确（按常规设计）"} for q in d.get("questions", [])]
        d = req_json("POST", f"/api/fto/analysis/{aid}/clarify", {"answers": answers}, token=tok)[1].get("data") or {}
    print(f"run -> status={d.get('status')} degraded={d.get('degraded')}")

    r = req_json("GET", f"/api/fto/analysis/{aid}/dossier", token=tok)
    md = r[1]["data"].get("dossier_markdown", "")
    print(f"\n① Claim 前序修复检查：")
    print(f"  含'包括：'前序={'包括：' in md}")
    # 打印前 4 条 claim chart 要素
    for line in md.split("\n"):
        if line.startswith("| CN") and "权要" in line:
            print(f"  {line[:80]}")
            if "权要1 | 管体" in line or ("权要1" in line and "，包括" not in line):
                pass
    print(f"\n② 检索策略数据源：")
    for line in md.split("\n"):
        if "数据源" in line or "命中源" in line:
            print(f"  {line}")

    # Markdown 导出
    status, headers, body = req("GET", f"/api/fto/analysis/{aid}/export/markdown", token=tok)
    print(f"\n③ Markdown 导出: HTTP {status}, Content-Disposition={headers.get('Content-Disposition','')[:40]}, 长度={len(body)}")

    # PDF 导出
    status, headers, body = req("GET", f"/api/fto/analysis/{aid}/export/pdf", token=tok)
    is_pdf = body[:5] == b"%PDF-"
    print(f"④ PDF 导出: HTTP {status}, is_pdf={is_pdf}, 大小={len(body)} 字节, Content-Type={headers.get('Content-Type','')}")

    print("\nM5 TEST DONE")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
