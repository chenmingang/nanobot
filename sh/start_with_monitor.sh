#!/bin/bash
# 启动 nanobot 并运行监控器

# 停止现有的监控器和 nanobot
echo "停止现有进程..."
pkill -f "monitor_process.sh" 2>/dev/null
pkill -f "nanobot gateway" 2>/dev/null

# 清理旧的 PID 文件
rm -f ./logs/nanobot_gateway.pid 2>/dev/null

# 启动监控器（在后台运行）
echo "启动进程监控器..."
nohup ./monitor_process.sh > ./logs/monitor_start.log 2>&1 &

# 等待并检查状态
sleep 5

echo "检查进程状态..."
if [ -f ./logs/nanobot_gateway.pid ] && ps -p $(cat ./logs/nanobot_gateway.pid) > /dev/null 2>&1; then
    echo "✅ nanobot 已启动 (PID: $(cat ./logs/nanobot_gateway.pid))"
    echo "📊 监控器日志: ./logs/monitor.log"
    echo "📄 nanobot 日志: ./logs/nanobot_gateway_$(date +%Y-%m-%d).log"
else
    echo "❌ nanobot 启动失败，请检查日志"
    echo "查看监控器日志: tail -f ./logs/monitor_start.log"
    echo "查看 nanobot 日志: ls -la ./logs/"
fi
