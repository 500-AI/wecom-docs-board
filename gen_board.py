#!/usr/bin/env python3
"""从 template.html + data.json 生成 index.html。
data.json 只追加不重排，保证文档 id（按序号）稳定，前端增量合并才不丢用户归类。
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
items = json.load(open(os.path.join(BASE, "data.json"), encoding="utf-8"))

type_map = {"在线文档":"文档","在线表格":"表格","智能表格":"智能表","智能文档":"智能文档","脑图":"脑图","PPT":"PPT","汇报":"汇报","收集表":"收集表","流程图":"流程图","?":"其他"}

docs = []
for i, d in enumerate(items):
    docs.append({
        "id": f"d{i+1}",
        "name": d["name"],
        "type": type_map.get(d["type"], d["type"]),
        "date": (d.get("create_time") or "")[:10],
        "url": d.get("url", ""),
        "pid": None,
        "hidden": False,
    })

# 项目结构由前端 localStorage 维护；种子仅在首次打开时生效
projects_seed = [
    {"id":"p1","title":"免审批运营","imp":"中","created":"2026-09-20"},
    {"id":"p2","title":"GEO 优化与品牌外宣","imp":"高","created":"2026-09-20"},
    {"id":"p3","title":"智能客服 Agent 与知识库","imp":"高","created":"2026-09-20"},
    {"id":"p4","title":"微信 AI 接入与内测","imp":"高","created":"2026-09-20"},
    {"id":"p5","title":"精细化运营与免费额度","imp":"中","created":"2026-09-20"},
    {"id":"p6","title":"会议纪要与周报","imp":"低","created":"2026-09-20"},
]
# 首访自动归类关键词（仅种子阶段用）
kw = {
    "p1":["免审"],
    "p2":["GEO","Geo","外宣","品牌","公众号","推文","可见","排版","图文"],
    "p3":["评测","知识库","Agent","agent","skill","Skill","SKILL","意图","query","客服","脑暴","需求整理"],
    "p4":["微信AI","微信 AI","内测","上线","接入","监控","小程序","握手","AI入口","AI 接入","AI进展","AI需求","AI搜索","GUI"],
    "p5":["免费额度","运营","优惠","名单","投放","人群","图笑","发卡"],
    "p6":["会议","周报","纪要","同步","主持","团建","TownHall","交流","分享","思考"],
}
for d in docs:
    for p in projects_seed:
        if any(k in d["name"] for k in kw[p["id"]]):
            d["pid"] = p["id"]; break

from datetime import datetime
meta_path = os.path.join(BASE, "patrol_meta.json")
patrol = {"date": datetime.now().strftime("%Y-%m-%d"), "new_count": 0}
if os.path.exists(meta_path):
    try: patrol = json.load(open(meta_path, encoding="utf-8"))
    except Exception: pass

seed = {"docs": docs, "projects": projects_seed,
        "lastSync": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "patrol": patrol}

html = open(os.path.join(BASE, "template.html"), encoding="utf-8").read()
html = html.replace("__SEED_JSON__", json.dumps(seed, ensure_ascii=False))
open(os.path.join(BASE, "index.html"), "w", encoding="utf-8").write(html)
print(f"gen ok: docs={len(docs)}")
