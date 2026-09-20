#!/usr/bin/env python3
"""每日巡检：用 wecom-cli 按高频关键词聚合搜索 yy 创建的企微文档，
与 data.json 比对，新文档追加到末尾（不重排，保证 id 稳定），再重新生成 index.html。
输出一行 JSON 摘要供自动化读取。企微接口 keywords 必填，无法空查全量，只能聚合逼近。
"""
import json, os, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data.json")
CREATOR = "wokSFfCgAAuljY1JMO4dg5NUwzJhDB_w"  # 授权人 yasminwu

KEYWORDS = ["周报","意图","评测","还款","免审","GEO","方案","分析","知识库","Agent",
            "客服","设计","名单","skill","Skill","数据","运营","规则","人群","看板",
            "复盘","会议","纪要","需求","产品","统计","信用卡","query","文档","测试",
            "监控","上线","接入","内测","优惠","额度","外宣","公众号","推文","AI",
            "PPT","汇报","演示","收集","流程"]

RAW_TYPE = {"doc":"在线文档","sheet":"在线表格","smartsheet":"智能表格",
            "smartpage":"智能文档","mind":"脑图","pdf":"PDF",
            "ppt":"PPT","journal":"汇报","collect":"收集表","flow":"流程图"}

def search(kw, created_after=None):
    params = {"keywords":[kw],"creator_userids":[CREATOR],
              "sort_by":"create_time","limit":30}
    if created_after:
        params["created_after"] = created_after  # 只查上次巡检之后新建的
    try:
        r = subprocess.run(
            ["wecom-cli","doc","search","--json",
             json.dumps(params, ensure_ascii=False)],
            capture_output=True, text=True, timeout=45)
        return json.loads(r.stdout).get("docs", [])
    except Exception:
        return []  # 超时或解析失败的 keyword 跳过，不中断整轮巡检

def main():
    from datetime import datetime
    meta_path = os.path.join(BASE, "patrol_meta.json")
    last_run = None
    if os.path.exists(meta_path):
        try: last_run = json.load(open(meta_path, encoding="utf-8")).get("last_run")
        except Exception: pass

    found = {}
    for kw in KEYWORDS:
        for d in search(kw, created_after=last_run):
            u = d.get("url")
            if u:
                found[u] = d

    items = json.load(open(DATA, encoding="utf-8"))
    known = {d.get("url") for d in items}
    new_docs = []
    for u, d in found.items():
        if u not in known:
            items.append({
                "create_time": d.get("create_time",""),
                "type": RAW_TYPE.get(d.get("doc_type",""), "其他"),
                "name": d.get("doc_name","(无名)"),
                "url": u,
            })
            new_docs.append(d.get("doc_name","(无名)"))

    if new_docs:
        json.dump(items, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

    # 每次都写巡检元数据（含本次时间窗）并重新生成页面
    now = datetime.now()
    meta = {"date": now.strftime("%Y-%m-%d"), "new_count": len(new_docs),
            "last_run": now.strftime("%Y-%m-%d %H:%M:%S"), "window_from": last_run}
    json.dump(meta, open(meta_path,"w",encoding="utf-8"), ensure_ascii=False)
    subprocess.run([sys.executable, os.path.join(BASE,"gen_board.py")], check=True)

    print(json.dumps({"scanned": len(found), "total": len(items),
                      "new_count": len(new_docs), "new_names": new_docs},
                     ensure_ascii=False))

if __name__ == "__main__":
    main()
