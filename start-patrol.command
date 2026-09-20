#!/bin/zsh
# 企微文档管理台 · 本地巡检服务启动器
# 双击运行一次即可：启动服务 + 注册开机自启
DIR="/Users/yy/WorkBuddy/2026-09-20-09-33-17/wecom-docs-board"
PY="/Users/yy/.workbuddy/binaries/python/versions/3.13.12/bin/python3"

pkill -f patrol_server.py 2>/dev/null
nohup "$PY" "$DIR/patrol_server.py" >> /tmp/wecom-patrol.log 2>&1 &

# 注册开机自启（在 Terminal/Finder 中运行才有权限）
launchctl bootstrap gui/$(id -u) /Users/yy/Library/LaunchAgents/com.yy.wecom-docs-patrol.plist 2>/dev/null \
  && echo "已注册开机自启" || echo "开机自启注册失败（不影响本次使用）"

sleep 1
curl -s http://127.0.0.1:8931/health > /dev/null \
  && echo "巡检服务已启动：http://127.0.0.1:8931 （本窗口可以关闭）" \
  || echo "启动失败，请把 /tmp/wecom-patrol.log 发给笔记侠排查"
