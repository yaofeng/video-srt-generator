#!/bin/bash

# 视频字幕生成系统 - 启动脚本
# 一键启动后端服务

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录的父目录（项目根目录）
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
STATIC_DIR="$BACKEND_DIR/static"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}视频字幕生成系统 - 启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查后端目录是否存在
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}错误: 后端目录不存在: $BACKEND_DIR${NC}"
    exit 1
fi

# 检查静态文件是否存在（前端是否已构建）
if [ ! -d "$STATIC_DIR" ] || [ -z "$(ls -A $STATIC_DIR 2>/dev/null)" ]; then
    echo -e "${YELLOW}警告: 未检测到前端构建产物${NC}"
    echo -e "${YELLOW}是否需要先构建前端？(y/n)${NC}"
    read -r response

    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}正在构建前端...${NC}"
        bash "$PROJECT_ROOT/scripts/build.sh"
        echo ""
    else
        echo -e "${YELLOW}跳过构建，仅启动后端服务...${NC}"
    fi
fi

# 检查虚拟环境
echo -e "${YELLOW}检查 Python 环境...${NC}"
cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
    echo -e "${RED}错误: 未找到虚拟环境 .venv${NC}"
    echo -e "${YELLOW}请先创建虚拟环境: python -m venv .venv${NC}"
    exit 1
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source .venv/bin/activate

# 检查依赖是否安装
echo -e "${YELLOW}检查依赖...${NC}"
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}依赖未安装，正在安装...${NC}"
    pip install -e .
fi

# 检查端口是否被占用
PORT=${PORT:-8000}
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}错误: 端口 $PORT 已被占用${NC}"
    echo -e "${YELLOW}请检查是否有其他服务正在运行，或设置不同的端口: PORT=8001 bash scripts/start.sh${NC}"
    exit 1
fi

# 启动服务
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}启动后端服务...${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}服务地址: http://localhost:$PORT${NC}"
echo -e "${GREEN}API 文档: http://localhost:$PORT/docs${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""

# 启动 FastAPI 服务器
uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
