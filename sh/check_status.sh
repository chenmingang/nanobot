#!/bin/bash
# 检查 nanobot 状态

echo "=== nanobot 状态检查 ==="
echo "检查时间: $(date)"

# 检查监控器进程
MONITOR_PID=$(pgrep -f "monitor_process.sh")
if [ -n "$MONITOR_PID" ]; then
    echo "✅ 监控器运行中 (PID: $MONITOR_PID)"
else
    echo "❌ 监控器未运行"
fi

# 检查 nanobot 网关进程
if [ -f ./logs/nanobot_gateway.pid ]; then
    NANOBOT_PID=$(cat ./logs/nanobot_gateway.pid)
    if ps -p $NANOBOT_PID > /dev/null 2>&1; then
        echo "✅ nanobot 网关运行中 (PID: $NANOBOT_PID)"
        echo "   进程启动时间: $(ps -p $NANOBOT_PID -o lstart=)"
        echo "   内存使用: $(ps -p $NANOBOT_PID -o rss=) KB"
    else
        echo "❌ nanobot 网关 PID 文件存在但进程未运行 (PID: $NANOBOT_PID)"
    fi
else
    echo "❌ nanobot 网关未运行 (无 PID 文件)"
fi

# 检查日志文件
echo ""
echo "=== 日志文件 ==="
ls -la ./logs/ 2>/dev/null | grep -E "\.log$|\.pid$" || echo "无日志文件"

# 检查最近日志
echo ""
echo "=== 最近日志内容 ==="
if [ -f ./logs/monitor.log ]; then
    echo "监控器日志 (最后5行):"
    tail -5 ./logs/monitor.log
fi

if [ -f ./logs/nanobot_gateway_$(date +%Y-%m-%d).log ]; then
    echo ""
    echo "nanobot 网关日志 (最后5行):"
    tail -5 ./logs/nanobot_gateway_$(date +%Y-%m-%d).log
fi