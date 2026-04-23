#!/usr/bin/env bash
set -e

echo "========================================"
echo " WSL AI 环境初始化脚本（Ubuntu 24.04）"
echo "========================================"

# --------- 基础校验 ----------
if ! grep -qi microsoft /proc/version; then
  echo "❌ 当前环境不是 WSL，终止执行"
  exit 1
fi

echo "✅ 检测到 WSL 环境"

# --------- 系统更新 ----------
echo "➡️ 更新系统软件包..."
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  curl wget ca-certificates \
  git \
  python3-pip python3-venv \
  lsb-release gnupg

# --------- DNS 持久化 ----------
echo "➡️ 配置 WSL DNS 持久化..."
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[network]
generateResolvConf = false
EOF

sudo tee /etc/resolv.conf > /dev/null <<'EOF'
nameserver 223.5.5.5
nameserver 8.8.8.8
EOF

# --------- nvm / Node ----------
if [ ! -d "$HOME/.nvm" ]; then
  echo "➡️ 安装 nvm..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

export NVM_DIR="$HOME/.nvm"
source "$NVM_DIR/nvm.sh"

if ! command -v node >/dev/null; then
  echo "➡️ 安装 Node.js LTS..."
  nvm install --lts
fi

echo "✅ Node 版本: $(node -v)"

# --------- Docker 校验 ----------
echo "➡️ 检查 Docker..."
if ! command -v docker >/dev/null; then
  echo "❌ 未检测到 docker，请确认 Docker Desktop 已安装并开启 WSL Integration"
  exit 1
fi

docker info >/dev/null || {
  echo "❌ Docker 未正常运行，请启动 Docker Desktop"
  exit 1
}

echo "✅ Docker 正常"

# --------- 项目目录 ----------
PROJECT_DIR="$HOME/my-ai-project"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# --------- docker-compose ----------
if [ ! -f docker-compose.yml ]; then
  echo "➡️ 生成 docker-compose.yml..."
  cat > docker-compose.yml <<'EOF'
version: "3.8"

services:
  postgres:
    image: ankane/pgvector:latest
    container_name: ai_postgres
    restart: always
    environment:
      POSTGRES_PASSWORD: james_5070ti
    ports:
      - "5432:5432"
    volumes:
      - ./postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    container_name: ai_qdrant
    restart: always
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
EOF
fi

# --------- 启动容器 ----------
echo "➡️ 启动 Docker Compose..."
docker compose up -d

# --------- 完成 ----------
echo "========================================"
echo "🎉 初始化完成"
echo "📂 项目目录: $PROJECT_DIR"
echo "📦 运行中的容器:"
docker ps
echo
echo "👉 下一步建议："
echo "1. docker exec -it ai_postgres psql -U postgres"
echo "2. CREATE EXTENSION vector;"
echo "3. 测试 Ollama / Qdrant 连接"
echo "========================================"
