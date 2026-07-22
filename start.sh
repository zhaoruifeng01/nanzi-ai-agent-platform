#!/bin/bash
# 一键启动前后端：后端 uvicorn(8001) + 前端 vite(5173)
# 启动前检查端口占用，被占用则 kill；Ctrl+C 停止全部

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BACKEND_PORT=8001
FRONTEND_PORT=5173

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}       一键启动 前后端 (Backend + Frontend)        ${NC}"
echo -e "${BLUE}==================================================${NC}"

# 1. 检查并释放端口（被占用就 kill）
free_port() {
  local port=$1 name=$2 pids
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo -e "${YELLOW}🛑 端口 $port ($name) 被占用，正在 kill: $pids${NC}"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  else
    echo -e "${GREEN}✅ 端口 $port ($name) 空闲${NC}"
  fi
}
free_port $BACKEND_PORT  "后端"
free_port $FRONTEND_PORT "前端"

# 2. 依赖检查
if [ ! -x "venv/bin/python" ]; then
  echo -e "${RED}❌ 未找到 venv/bin/python，请先执行:${NC}"
  echo "    uv venv venv && uv pip install -r requirements.txt --python venv/bin/python"
  exit 1
fi
if [ ! -f "$ROOT/.env" ]; then
  echo -e "${YELLOW}⚠️  未找到 .env，后端可能无法启动（可从 env.example 复制配置）${NC}"
fi
if [ ! -d "frontend/node_modules" ]; then
  echo -e "${YELLOW}📦 frontend/node_modules 不存在，执行 npm install...${NC}"
  (cd frontend && npm install) || { echo -e "${RED}❌ npm install 失败${NC}"; exit 1; }
fi

# 3. 日志目录
mkdir -p "$ROOT/logs"

# 4. 启动后端
echo -e "${YELLOW}🔥 启动后端 (http://localhost:$BACKEND_PORT)...${NC}"
nohup venv/bin/python -m uvicorn app.main:app \
  --host 0.0.0.0 --port $BACKEND_PORT \
  > "$ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID   日志: logs/backend.log"

# 5. 启动前端
echo -e "${YELLOW}🔥 启动前端 (http://localhost:$FRONTEND_PORT)...${NC}"
(cd frontend && nohup npm run dev > "$ROOT/logs/frontend.log" 2>&1) &
FRONTEND_PID=$!
echo "   前端 PID: $FRONTEND_PID   日志: logs/frontend.log"

# 6. 清理：Ctrl+C 或退出时停掉全部（端口兜底 kill，确保释放）
cleanup() {
  echo -e "\n${YELLOW}🛑 正在停止全部服务...${NC}"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  sleep 1
  lsof -ti:$BACKEND_PORT  2>/dev/null | xargs kill -9 2>/dev/null || true
  lsof -ti:$FRONTEND_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
  echo -e "${GREEN}✅ 已停止${NC}"
}
trap cleanup INT TERM EXIT

# 7. 等待端口就绪
wait_port() {
  local port=$1 name=$2 logfile=$3 max=$4 i=0
  while [ $i -lt $max ]; do
    if lsof -ti:"$port" >/dev/null 2>&1; then
      echo -e "${GREEN}✅ $name 就绪: http://localhost:$port${NC}"
      return 0
    fi
    sleep 1; i=$((i+1))
  done
  echo -e "${RED}❌ $name 在 ${max}s 内未就绪，查看日志: logs/$logfile${NC}"
  return 1
}
wait_port $BACKEND_PORT  "后端" "backend.log"  40
wait_port $FRONTEND_PORT "前端" "frontend.log" 40

echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}🚀 启动完成${NC}"
echo -e "  前端:  http://localhost:$FRONTEND_PORT"
echo -e "  后端:  http://localhost:$BACKEND_PORT   (API 文档 /docs)"
echo -e "  日志:  tail -f logs/backend.log logs/frontend.log"
echo -e "${YELLOW}  按 Ctrl+C 停止全部${NC}"
echo -e "${BLUE}==================================================${NC}"

# 8. 前台实时输出日志，Ctrl+C 触发 cleanup 停全部
tail -f "$ROOT/logs/backend.log" "$ROOT/logs/frontend.log"
