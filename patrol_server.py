#!/usr/bin/env python3
"""本地巡检与数据服务：向「企微文档索引」页面提供本机数据与实时巡检能力。
端点：
  GET  /health  健康检查
  GET  /docs    返回当前本机的文档种子数据（页面启动时优先读取，实现「谁打开看谁的数据」）
  POST /patrol  实时执行企微巡检并（可选）推送远程
仅监听 127.0.0.1。浏览器从 https 页面调用需要 Access-Control-Allow-Private-Network 头。
"""
import json, os, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8931
PY = sys.executable
GIT_ENV = dict(os.environ, PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + os.environ.get("PATH",""))

sys.path.insert(0, BASE)
import gen_board  # noqa: E402  复用 build_seed()

def run_patrol():
    t0 = time.time()
    data_path = os.path.join(BASE, "data.json")
    try:
        before = {d.get("url") for d in json.load(open(data_path, encoding="utf-8"))} \
                 if os.path.exists(data_path) else set()
        r = subprocess.run([PY, os.path.join(BASE, "patrol.py")],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            return {"ok": False, "error": "巡检脚本执行失败: " + (r.stderr or r.stdout or "")[-200:]}
        summary = json.loads(r.stdout.strip().splitlines()[-1])
        after = json.load(open(data_path, encoding="utf-8")) if os.path.exists(data_path) else []
        new_docs = [d for d in after if d.get("url") not in before]

        pushed = False
        if os.path.isdir(os.path.join(BASE, ".git")):
            subprocess.run(["git", "add", "-A"], cwd=BASE, capture_output=True, env=GIT_ENV)
            c = subprocess.run(["git", "-c", "user.name=docs-ledger",
                                "-c", "user.email=docs-ledger@local",
                                "commit", "-m", "手动巡检更新"],
                               cwd=BASE, capture_output=True, text=True, env=GIT_ENV)
            if c.returncode == 0:
                p = subprocess.run(["git", "push"], cwd=BASE,
                                   capture_output=True, text=True, timeout=120, env=GIT_ENV)
                pushed = (p.returncode == 0)

        return {"ok": True, "new_count": summary.get("new_count", 0),
                "new_docs": new_docs, "pushed": pushed,
                "seed": gen_board.build_seed(),
                "elapsed": round(time.time() - t0, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):  self._route()
    def do_POST(self): self._route()

    def _route(self):
        if self.path.startswith("/health"):
            self._json(200, {"ok": True, "service": "wecom-docs-ledger"})
        elif self.path.startswith("/docs"):
            try:
                self._json(200, gen_board.build_seed())
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)[:200]})
        elif self.path.startswith("/patrol"):
            self._json(200, run_patrol())
        else:
            self._json(404, {"ok": False, "error": "not found"})

if __name__ == "__main__":
    print(f"docs ledger server on http://127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
