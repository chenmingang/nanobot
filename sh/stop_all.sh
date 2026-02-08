#!/bin/bash
# 停止所有 nanobot 相关进程

echo "停止 nanobot 相关进程..."

# 停止监控器
pkill -f "monitor_process.sh" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ 监控器已停止"
else
    echo "ℹ️  监控器未运行"
fi

# 停止 nanobot 网关
pkill -f "nanobot gateway" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ nanobot 网关已停止"
else
    echo "ℹ️  nanobot 网关未运行"
fi

# 清理 PID 文件
rm -f ./logs/nanobot_gateway.pid 2>/dev/null
echo "✅ 清理 PID 文件"

echo "所有进程已停止"