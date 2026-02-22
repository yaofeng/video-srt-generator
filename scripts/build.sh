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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
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

# 保存当前目录
ORIGINAL_DIR="$(pwd)"

# 进入前端目录
echo -e "${YELLOW}[1/3] 进入前端目录...${NC}"
cd "$FRONTEND_DIR"

# 检查 package.json 是否存在
if [ ! -f "package.json" ]; then
    echo -e "${RED}错误: 找不到 package.json 文件${NC}"
    cd "$ORIGINAL_DIR"
    exit 1
fi

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}未检测到 node_modules，正在安装依赖...${NC}"
    bun install || npm install || {
        echo -e "${RED}依赖安装失败${NC}"
        cd "$ORIGINAL_DIR"
        exit 1
    }
fi

# 构建前端
echo -e "${YELLOW}[2/3] 构建前端应用...${NC}"
bun run build || npm run build || {
    echo -e "${RED}前端构建失败${NC}"
    cd "$ORIGINAL_DIR"
    exit 1
}

# 检查构建产物
if [ ! -d "dist" ]; then
    echo -e "${RED}错误: 构建失败，dist 目录不存在${NC}"
    cd "$ORIGINAL_DIR"
    exit 1
fi

echo -e "${GREEN}前端构建完成！${NC}"

# 清理旧的静态文件
echo -e "${YELLOW}[3/3] 复制构建产物到后端静态目录...${NC}"
echo -e "${YELLOW}清理旧的静态文件...${NC}"
# 删除并重新创建静态目录，确保完全清空
rm -rf "$STATIC_DIR"
mkdir -p "$STATIC_DIR"

# 复制构建产物
echo -e "${YELLOW}正在复制文件...${NC}"
# 复制 dist 目录的内容到 static 目录（注意 dist/ 后面的斜杠和点号）
cp -r dist/. "$STATIC_DIR/"

# 验证复制结果
if [ -f "$STATIC_DIR/index.html" ]; then
    echo -e "${GREEN}静态文件复制完成！${NC}"
else
    echo -e "${RED}错误: 静态文件复制失败${NC}"
    cd "$ORIGINAL_DIR"
    exit 1
fi

# 返回原始目录
cd "$ORIGINAL_DIR"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}构建成功完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "前端构建产物已复制到: ${STATIC_DIR}"
echo -e "可以使用 'bash scripts/start.sh' 启动服务"
echo ""
