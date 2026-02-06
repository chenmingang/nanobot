#!/bin/bash
# nanobot gateway 后台启动脚本
# 功能：后台运行、按天切割日志、支持启动/停止/重启/状态查询

# ===================== 配置项（可根据需要修改）=====================
# 1. 日志目录（当前目录下的logs文件夹，无需修改）
LOG_DIR="./logs"
# 2. nanobot 执行命令（根据你的环境选择，三选一即可）
# 方式1：用指定Python3.12版本（最稳妥，避免环境冲突）
NANOBOT_CMD="python3.12 -m nanobot gateway"
# 方式2：用全局python软链接（你之前配置的，简洁版）
# NANOBOT_CMD="python -m nanobot gateway"
# 方式3：若创建了nanobot全局软链接（极简版）
# NANOBOT_CMD="nanobot gateway"
# 3. 进程标识（用于区分进程，无需修改）
PROCESS_NAME="nanobot_gateway"
# ==================================================================

# 创建日志目录（不存在则自动创建）
mkdir -p ${LOG_DIR}

# 日志文件名：按天命名，格式如 nanobot_gateway_2026-02-06.log
LOG_FILE="${LOG_DIR}/${PROCESS_NAME}_$(date +%Y-%m-%d).log"
# 进程PID文件（记录后台进程ID，用于停止/重启）
PID_FILE="${LOG_DIR}/${PROCESS_NAME}.pid"

# 定义函数：启动服务
start() {
    # 检查是否已运行
    if [ -f ${PID_FILE} ] && ps -p $(cat ${PID_FILE}) > /dev/null 2>&1; then
        echo -e "\033[33m[警告] ${PROCESS_NAME} 已在运行中（PID: $(cat ${PID_FILE})）\033[0m"
        return 1
    fi

    # 后台启动进程，输出日志到按天命名的文件
    echo -e "\033[32m[信息] 正在启动 ${PROCESS_NAME}...\033[0m"
    nohup ${NANOBOT_CMD} > ${LOG_FILE} 2>&1 &
    # 记录进程PID
    echo $! > ${PID_FILE}

    # 验证启动是否成功
    sleep 2
    if ps -p $(cat ${PID_FILE}) > /dev/null 2>&1; then
        echo -e "\033[32m[成功] ${PROCESS_NAME} 启动成功（PID: $(cat ${PID_FILE})），日志文件：${LOG_FILE}\033[0m"
    else
        echo -e "\033[31m[错误] ${PROCESS_NAME} 启动失败，请查看日志：${LOG_FILE}\033[0m"
        rm -f ${PID_FILE}
        return 1
    fi
}

# 定义函数：停止服务
stop() {
    # 检查是否运行
    if [ ! -f ${PID_FILE} ] || ! ps -p $(cat ${PID_FILE}) > /dev/null 2>&1; then
        echo -e "\033[33m[警告] ${PROCESS_NAME} 未运行\033[0m"
        return 1
    fi

    # 停止进程
    echo -e "\033[32m[信息] 正在停止 ${PROCESS_NAME}（PID: $(cat ${PID_FILE})）...\033[0m"
    kill $(cat ${PID_FILE}) > /dev/null 2>&1
    sleep 3

    # 强制杀死（若未正常停止）
    if ps -p $(cat ${PID_FILE}) > /dev/null 2>&1; then
        echo -e "\033[33m[信息] 强制停止 ${PROCESS_NAME}...\033[0m"
        kill -9 $(cat ${PID_FILE}) > /dev/null 2>&1
    fi

    # 删除PID文件
    rm -f ${PID_FILE}
    echo -e "\033[32m[成功] ${PROCESS_NAME} 已停止\033[0m"
}

# 定义函数：查看状态
status() {
    if [ -f ${PID_FILE} ] && ps -p $(cat ${PID_FILE}) > /dev/null 2>&1; then
        echo -e "\033[32m[信息] ${PROCESS_NAME} 正在运行（PID: $(cat ${PID_FILE})），日志文件：${LOG_FILE}\033[0m"
    else
        echo -e "\033[31m[信息] ${PROCESS_NAME} 未运行\033[0m"
        return 1
    fi
}

# 定义函数：重启服务
restart() {
    stop
    sleep 2
    start
}

# 脚本入口：根据参数执行对应功能
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo -e "\033[31m[用法] $0 {start|stop|restart|status}\033[0m"
        echo -e "示例："
        echo -e "  启动：$0 start"
        echo -e "  停止：$0 stop"
        echo -e "  重启：$0 restart"
        echo -e "  查看状态：$0 status"
        exit 1
        ;;
esac

exit 0