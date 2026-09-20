#!/usr/bin/env python3
"""本地巡检服务：接收页面「巡检更新」按钮的调用，实时执行企微巡检并推送 GitHub。
仅监听 127.0.0.1，只暴露 /health 和 /patrol 两个端点。
浏览器从 https 页面调本服务需要 Access-Control-Allow-Private-Network 头（PNA 预检）。
"""
import json, os, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8931
PY = "/Users/yy/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
GIT_ENV = dict(os.environ, PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + os.environ.get("PATH",""))

def run_patrol():
    t0 = time.time()
    data_path = os.path.join(BASE, "data.json")
    try:
        before = {d.get("url") for d in json.load(open(data_path, encoding="utf-8"))}
        r = subprocess.run([PY, os.path.join(BASE, "patrol.py")],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            return {"ok": False, "error": "巡检脚本执行失败: " + (r.stderr or "")[-200:]}
        summary = json.loads(r.stdout.strip().splitlines()[-1])
        after = json.load(open(data_path, encoding="utf-8"))
        new_docs = [d for d in after if d.get("url") not in before]

        pushed = False
        subprocess.run(["git", "add", "-A"], cwd=BASE, capture_output=True, env=GIT_ENV)
        c = subprocess.run(["git", "-c", "user.name=500-AI",
                            "-c", "user.email=500-AI@users.noreply.github.com",
                            "commit", "-m", "手动巡检更新"],
                           cwd=BASE, capture_output=True, text=True, env=GIT_ENV)
        if c.returncode == 0:
            p = subprocess.run(["git", "push"], cwd=BASE,
                               capture_output=True, text=True, timeout=120, env=GIT_ENV)
            pushed = (p.returncode == 0)

        return {"ok": True, "new_count": summary.get("new_count", 0),
                "new_docs": new_docs, "pushed": pushed,
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
            self._json(200, {"ok": True, "service": "wecom-docs-patrol"})
        elif self.path.startswith("/patrol"):
            self._json(200, run_patrol())
        else:
            self._json(404, {"ok": False, "error": "not found"})

if __name__ == "__main__":
    print(f"patrol server on http://127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
