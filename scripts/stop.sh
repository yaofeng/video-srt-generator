#!/bin/bash
# 停止视频字幕生成服务的所有进程

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== 停止视频字幕生成服务 =====${NC}"

# 项目根目录（脚本的父目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# 1. 首先尝试正常停止后端服务（在 backend 目录）
echo -e "\n${YELLOW}[1/3]${NC} 尝试正常停止后端服务..."

# 查找并保存 uvicorn 进程 PID
UVICORN_PIDS=$(pgrep -f "uvicorn.*app.main" || true)

if [ -n "$UVICORN_PIDS" ]; then
    echo "发现运行中的 uvicorn 进程: $UVICORN_PIDS"

    # 尝试正常停止
    for PID in $UVICORN_PIDS; do
        echo "发送 SIGTERM 到进程 $PID..."
        kill -TERM "$PID" 2>/dev/null || true
    done

    # 等待最多 5 秒
    echo "等待进程正常退出..."
    TIMEOUT=5
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        if ! pgrep -f "uvicorn.*app.main" > /dev/null; then
            echo -e "${GREEN}后端服务已正常停止${NC}"
            break
        fi
        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done

    # 检查是否还在运行
    if pgrep -f "uvicorn.*app.main" > /dev/null; then
        echo -e "${YELLOW}正常停止超时，使用强制方式...${NC}"
        FORCE_KILL=true
    else
        FORCE_KILL=false
    fi
else
    echo "没有发现运行中的后端服务"
    FORCE_KILL=false
fi

# 2. 如果正常停止失败，使用强制方式
if [ "$FORCE_KILL" = true ]; then
    echo -e "\n${RED}[2/3]${NC} 强制停止后端服务..."

    # 使用 pkill 强制终止
    pkill -9 -f "uvicorn.*app.main" 2>/dev/null || true

    # 再次检查
    if pgrep -f "uvicorn.*app.main" > /dev/null; then
        echo -e "${RED}错误: 无法停止后端服务${NC}"
        echo "请手动执行: pkill -9 -f 'uvicorn.*app.main'"
    else
        echo -e "${GREEN}后端服务已强制停止${NC}"
    fi
else
    echo -e "\n${YELLOW}[2/3]${NC} 跳过强制停止步骤"
fi

# 3. 检查并停止可能占用端口的进程
echo -e "\n${YELLOW}[3/3]${NC} 检查端口占用..."

# 检查 8000 端口（后端默认）
PORT_8000_PID=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$PORT_8000_PID" ]; then
    echo "发现进程 $PORT_8000_PID 占用端口 8000，正在终止..."
    kill -9 "$PORT_8000_PID" 2>/dev/null || true
fi

# 检查 8001 端口（备用）
PORT_8001_PID=$(lsof -ti:8001 2>/dev/null || true)
if [ -n "$PORT_8001_PID" ]; then
    echo "发现进程 $PORT_8001_PID 占用端口 8001，正在终止..."
    kill -9 "$PORT_8001_PID" 2>/dev/null || true
fi

# 检查 5173 端口（前端 Vite）
PORT_5173_PID=$(lsof -ti:5173 2>/dev/null || true)
if [ -n "$PORT_5173_PID" ]; then
    echo "发现进程 $PORT_5173_PID 占用端口 5173，正在终止..."
    kill -9 "$PORT_5173_PID" 2>/dev/null || true
fi

# 检查 3000 端口（前端备用）
PORT_3000_PID=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$PORT_3000_PID" ]; then
    echo "发现进程 $PORT_3000_PID 占用端口 3000，正在终止..."
    kill -9 "$PORT_3000_PID" 2>/dev/null || true
fi

# 4. 最终检查
echo -e "\n${GREEN}===== 最终检查 =====${NC}"

# 检查 Python 进程
PYTHON_COUNT=$(pgrep -f "uvicorn.*app.main" 2>/dev/null | wc -l)
if [ "$PYTHON_COUNT" -gt 0 ]; then
    echo -e "${RED}警告: 仍有 $PYTHON_COUNT 个 Python 后端进程在运行${NC}"
    pgrep -f "uvicorn.*app.main" | while read -r pid; do
        ps -p "$pid" -o pid,cmd --no-headers || true
    done
else
    echo -e "${GREEN}后端服务: 已停止${NC}"
fi

# 检查 Node 进程（前端）
NODE_COUNT=$(pgrep -f "vite.*video-srt-generator-frontend" 2>/dev/null | wc -l)
if [ "$NODE_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}提示: 有 $NODE_COUNT 个前端进程在运行${NC}"
    echo "如需停止前端，请按 Ctrl+C 或执行: pkill -f 'vite.*video-srt-generator-frontend'"
else
    echo -e "${GREEN}前端服务: 未运行${NC}"
fi

echo -e "\n${GREEN}===== 停止完成 =====${NC}"
