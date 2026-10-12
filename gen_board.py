#!/usr/bin/env python3
"""从 template.html + data.json + config.json 生成 index.html。
config.json 由 setup 流程生成：creator_userid / owner / site_title / projects（含 kw 归类规则）。
data.json 只追加不重排，保证文档 id（按序号）稳定，前端增量合并才不丢用户归类。
build_seed() 同时供 patrol_server.py 的 /docs 接口复用。
"""
import json, os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

TYPE_MAP = {"在线文档":"文档","在线表格":"表格","智能表格":"智能表","智能文档":"智能文档",
            "脑图":"脑图","PPT":"PPT","汇报":"汇报","收集表":"收集表","流程图":"流程图","?":"其他"}

DEFAULT_CONFIG = {
    "creator_userid": "",
    "owner": "分享者",
    "site_title": "企微文档索引",
    "projects": [],
}

def load_config():
    p = os.path.join(BASE, "config.json")
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(p):
        try: cfg.update(json.load(open(p, encoding="utf-8")))
        except Exception: pass
    return cfg

def build_seed():
    cfg = load_config()
    data_path = os.path.join(BASE, "data.json")
    items = json.load(open(data_path, encoding="utf-8")) if os.path.exists(data_path) else []

    projects = [{"id": p["id"], "title": p["title"], "imp": p.get("imp","中"),
                 "created": p.get("created","")} for p in cfg.get("projects", [])]
    kw_rules = [(p["id"], p.get("kw", [])) for p in cfg.get("projects", [])]

    docs = []
    for i, d in enumerate(items):
        name = d["name"]
        pid = None
        for pjid, kws in kw_rules:
            if any(k in name for k in kws):
                pid = pjid; break
        docs.append({
            "id": f"d{i+1}",
            "name": name,
            "type": TYPE_MAP.get(d["type"], d["type"]),
            "date": (d.get("create_time") or "")[:10],
            "url": d.get("url", ""),
            "pid": pid,
            "hidden": False,
        })

    meta_path = os.path.join(BASE, "patrol_meta.json")
    patrol = {"date": datetime.now().strftime("%Y-%m-%d"), "new_count": 0}
    if os.path.exists(meta_path):
        try: patrol = json.load(open(meta_path, encoding="utf-8"))
        except Exception: pass

    return {
        "docs": docs,
        "projects": projects,
        "lastSync": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "patrol": patrol,
        "owner": cfg.get("owner", "分享者"),
        "site_title": cfg.get("site_title", "企微文档索引"),
    }

def main():
    seed = build_seed()
    html = open(os.path.join(BASE, "template.html"), encoding="utf-8").read()
    html = html.replace("__SEED_JSON__", json.dumps(seed, ensure_ascii=False))
    open(os.path.join(BASE, "index.html"), "w", encoding="utf-8").write(html)
    print(f"gen ok: docs={len(seed['docs'])}")

if __name__ == "__main__":
    main()
