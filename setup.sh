#!/bin/zsh
# 企微文档索引 · 一键接入
# 用法：curl -fsSL https://500-ai.github.io/wecom-docs-board/setup.sh | zsh
# 做什么：装 wecom-cli → 企微扫码授权 → 拉你的文档 → 起本地数据服务 → 刷新页面即你自己的目录
set -e

HUB="https://500-ai.github.io/wecom-docs-board"
DIR="$HOME/wecom-docs-ledger"
PY="/Users/yy/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
command -v python3 >/dev/null && PY="$(command -v python3)"
# 优先用 python3.11+ 
if ! "$PY" -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" 2>/dev/null; then
  PY="$(command -v python3)"
fi

echo "企微文档索引 · 一键接入"
echo "------------------------------"

# 1. Node / wecom-cli
if ! command -v node >/dev/null; then
  echo "未检测到 Node.js，请先安装：https://nodejs.org"
  exit 1
fi
if ! command -v wecom-cli >/dev/null; then
  echo "安装 wecom-cli ..."
  npm install -g @wecom/cli
fi
echo "wecom-cli: $(wecom-cli --version 2>/dev/null | head -1)"

# 2. 企微授权（未授权则弹出二维码）
if [ "$(wecom-cli auth show --status 2>/dev/null)" != "authorized" ]; then
  echo "请用企业微信扫码完成授权："
  wecom-cli auth init --noninteractive
fi

# 3. 下载服务文件
mkdir -p "$DIR"
for f in patrol.py gen_board.py patrol_server.py template.html; do
  curl -fsSL "$HUB/$f" -o "$DIR/$f"
done

# 4. 解析身份，写 config.json
WHOAMI=$(wecom-cli identity whoami 2>/dev/null || true)
"$PY" - "$WHOAMI" "$DIR" << 'PYEOF'
import json, re, sys
raw, d = sys.argv[1], sys.argv[2]
m = re.search(r"授权真人用户身份：\s*名字：(\S+).*?ID：(wo[\w-]+)", raw, re.S)
cfg = {"creator_userid": m.group(2) if m else "",
       "owner": m.group(1) if m else "我",
       "site_title": "企微文档索引", "projects": []}
json.dump(cfg, open(d + "/config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("身份:", cfg["owner"])
PYEOF

# 5. 首次全量巡检（约 1-3 分钟）
echo "首次拉取你创建的企微文档（约 1-3 分钟）..."
cd "$DIR" && "$PY" patrol.py

# 6. 启动本地数据服务
pkill -f patrol_server.py 2>/dev/null || true
nohup "$PY" "$DIR/patrol_server.py" >> /tmp/wecom-docs-ledger.log 2>&1 &
sleep 1
if curl -s http://127.0.0.1:8931/health >/dev/null; then
  echo "------------------------------"
  echo "完成。刷新页面，顶部提示条消失、显示的就是你自己的企微文档目录。"
  echo "页面地址：$HUB"
else
  echo "服务启动失败，请把 /tmp/wecom-docs-ledger.log 发给分享者排查"
fi
