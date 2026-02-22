#!/bin/bash

# 视频字幕生成系统 - 构建脚本
# 用于构建前端并将构建产物复制到后端静态文件目录

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录的父目录（项目根目录）
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
STATIC_DIR="$BACKEND_DIR/static"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}视频字幕生成系统 - 构建脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查前端目录是否存在
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}错误: 前端目录不存在: $FRONTEND_DIR${NC}"
    exit 1
fi

# 检查后端目录是否存在
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}错误: 后端目录不存在: $BACKEND_DIR${NC}"
    exit 1
fi

# 进入前端目录
echo -e "${YELLOW}[1/3] 进入前端目录...${NC}"
cd "$FRONTEND_DIR"

# 检查 package.json 是否存在
if [ ! -f "package.json" ]; then
    echo -e "${RED}错误: 找不到 package.json 文件${NC}"
    exit 1
fi

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}未检测到 node_modules，正在安装依赖...${NC}"
    bun install || npm install
fi

# 构建前端
echo -e "${YELLOW}[2/3] 构建前端应用...${NC}"
bun run build || npm run build

# 检查构建产物
if [ ! -d "dist" ]; then
    echo -e "${RED}错误: 构建失败，dist 目录不存在${NC}"
    exit 1
fi

echo -e "${GREEN}前端构建完成！${NC}"

# 清理旧的静态文件
echo -e "${YELLOW}[3/3] 复制构建产物到后端静态目录...${NC}"
if [ -d "$STATIC_DIR" ]; then
    echo -e "${YELLOW}清理旧的静态文件...${NC}"
    rm -rf "$STATIC_DIR"/*
else
    echo -e "${YELLOW}创建静态文件目录...${NC}"
    mkdir -p "$STATIC_DIR"
fi

# 复制构建产物
cp -r dist/* "$STATIC_DIR/"

echo -e "${GREEN}静态文件复制完成！${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}构建成功完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "前端构建产物已复制到: ${STATIC_DIR}"
echo -e "可以使用 'bash scripts/start.sh' 启动服务"
echo ""
