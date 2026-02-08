#!/bin/bash
# nanobot 进程监控脚本
# 自动检测并重启 nanobot 进程

# 配置
PROCESS_NAME="nanobot_gateway"
LOG_DIR="./logs"
PID_FILE="${LOG_DIR}/${PROCESS_NAME}.pid"
MONITOR_LOG="${LOG_DIR}/monitor.log"
CHECK_INTERVAL=30  # 检查间隔（秒）

# 创建日志目录
mkdir -p ${LOG_DIR}

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${MONITOR_LOG}
}

# 检查进程是否运行
check_process() {
    if [ -f ${PID_FILE} ] && ps -p $(cat ${PID_FILE}) > /dev/null 2>&1; then
        return 0  # 进程运行中
    else
        return 1  # 进程未运行
    fi
}

# 启动进程
start_process() {
    log "启动 ${PROCESS_NAME}..."
    nohup /usr/local/bin/nanobot gateway > ${LOG_DIR}/${PROCESS_NAME}_$(date +%Y-%m-%d).log 2>&1 &
    echo $! > ${PID_FILE}
    sleep 3
    
    if check_process; then
        log "${PROCESS_NAME} 启动成功 (PID: $(cat ${PID_FILE}))"
        return 0
    else
        log "${PROCESS_NAME} 启动失败"
        rm -f ${PID_FILE}
        return 1
    fi
}

# 停止进程
stop_process() {
    if check_process; then
        log "停止 ${PROCESS_NAME} (PID: $(cat ${PID_FILE}))..."
        kill $(cat ${PID_FILE}) > /dev/null 2>&1
        sleep 3
        
        # 强制停止
        if check_process; then
            log "强制停止 ${PROCESS_NAME}..."
            kill -9 $(cat ${PID_FILE}) > /dev/null 2>&1
        fi
        
        rm -f ${PID_FILE}
        log "${PROCESS_NAME} 已停止"
    fi
}

# 重启进程
restart_process() {
    log "重启 ${PROCESS_NAME}..."
    stop_process
    sleep 2
    start_process
}

# 主监控循环
log "启动 nanobot 进程监控器..."
log "检查间隔: ${CHECK_INTERVAL}秒"

# 首次启动
if ! check_process; then
    start_process
fi

# 监控循环
while true; do
    if ! check_process; then
        log "检测到 ${PROCESS_NAME} 进程已停止，正在重启..."
        start_process
    fi
    
    sleep ${CHECK_INTERVAL}
done