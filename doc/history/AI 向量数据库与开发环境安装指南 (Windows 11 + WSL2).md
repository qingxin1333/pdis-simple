## 概览（你将得到什么）

1. 在 Windows 上用 **WSL2 (Ubuntu 24.04)** 构建开发环境。
2. 在 WSL 内安装并使用 Docker（通过 Docker Desktop 的 WSL2 后端）。
3. 配置 Node.js / Python / Git / VS Code Remote - WSL。
4. 使用 Docker Compose 快速拉起 PostgreSQL（含 pgvector）与 Qdrant。
5. GPU 驱动与 `nvidia-smi` 验证（用于本地 AI 推理）。
6. 网络/代理（VPN）配置建议与常用故障排查命令。
7. 与 Windows 上的 Ollama 互通的关键步骤（包括环境变量）。

------

# 先决条件（在开始前检查）

- Windows 10（2004+）或 Windows 11（推荐最新）。
- 管理员权限的 PowerShell。
- 能访问互联网（安装期间强烈建议开启系统级 VPN/TUN 模式，见 **网络/代理** 一节）。
- 已安装或准备用于本机的 VPN/代理（如果在中国大陆，很多步骤需要翻墙或使用国内镜像源）。

------

# 总体推荐执行顺序（遵循此顺序可以最少出错）

1. 检查 Windows 与 WSL 支持（`winver` 或确认 Windows 版本）。
2. 在管理员 PowerShell 中安装 WSL2 + 指定 Ubuntu 24.04：`wsl --install -d Ubuntu-24.04`。
3. 启动 Ubuntu，设置用户名/密码。
4. 在 Ubuntu 中做基础配置（`apt update`、DNS 持久化、镜像源替换（可选））。
5. 在 Windows 上安装 Docker Desktop，启用 WSL2 后端并打开 WSL Integration（Ubuntu-24.04）。
6. 在 Windows 上安装 VS Code，并安装 `Remote - WSL` 插件（推荐在有 VPN 时下载）。
7. 在 WSL 中安装 nvm/node、Python 工具链与 git。
8. 配置 Docker 代理（如果需要）并验证 `docker pull hello-world`。
9. 创建项目目录、docker-compose（Postgres+pgvector + Qdrant）并 `docker compose up -d`。
10. 验证数据库、连接与 Ollama 跨系统访问。

下面把每一步展开成可复制粘贴的操作命令与说明。

------

# 详细步骤与命令（可直接复制执行）

## 1) 在 Windows 上安装 / 检查 WSL2

以**管理员**打开 PowerShell，然后：

```
# 安装 WSL + 指定 Ubuntu 24.04
wsl --install -d Ubuntu-24.04

# 如果提示需要更新 WSL 内核，先运行：
wsl --update

# 列出已安装的 distro 及版本
wsl -l -v
```

**常见问题**

- 如果 `wsl --install` 失败，可尝试 `wsl --install -d Ubuntu-24.04 --web-download` 或先 `wsl --update`。
- 安装完成后系统会要求重启并在首次进入 Ubuntu 时设置用户名/密码。

------

## 2) 进入 Ubuntu，基础更新与持久 DNS 配置

进入 WSL（Ubuntu）后先更新：

```
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget ca-certificates lsb-release gnupg
```

> **持久化 DNS（避免临时修改被覆盖）**

```
# 禁止 WSL 自动生成 /etc/resolv.conf
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[network]
generateResolvConf = false
EOF

# 退出 WSL（在 Windows PowerShell 运行）
# wsl --shutdown

# 重新打开 Ubuntu，写入固定 resolv.conf（示例使用阿里/谷歌 DNS）
sudo tee /etc/resolv.conf > /dev/null <<'EOF'
nameserver 223.5.5.5
nameserver 8.8.8.8
EOF
```

**备注**：直接 `echo ... | sudo tee /etc/resolv.conf` 可以临时生效，但 WSL 重启后可能被覆盖，所以上述 `wsl.conf` 方法是持久化做法。

------

## 3) （可选）替换 apt 源为国内镜像（Ubuntu 24.04）

如果你不使用系统级 VPN，推荐替换为国内镜像以加速包下载（**慎重执行，按需**）：

```
# 仅示例（确保你确实是 24.04，并备份原文件）
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
sudo sed -i 's|http://archive.ubuntu.com/ubuntu/|https://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources
sudo sed -i 's|http://security.ubuntu.com/ubuntu/|https://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources
sudo apt update
```

------

## 4) 验证 GPU（若你期望利用本地 GPU）

在 WSL 中运行：

```
nvidia-smi
```

输出应显示 GPU 型号（例如 RTX 5070 Ti）与 driver/CUDA 信息。若报错，检查 Windows 上 NVIDIA 驱动是否已安装并且支持 WSL。

------

## 5) 在 Windows 安装 Docker Desktop 并启用 WSL2 后端

- 从 Docker 官网下载并安装 Docker Desktop（安装时选择使用 WSL2 后端）。
- 启动 Docker Desktop → Settings → General → 勾选 **Use the WSL 2 based engine**。
- Settings → Resources → WSL Integration → 打开 **Enable integration with my default WSL distro** 并开启 `Ubuntu-24.04`。
- 如果你需要 Docker 走代理（拉镜像慢或需要翻墙），在 Docker Desktop → Settings → Proxies 中填写本地代理地址（例如 `http://127.0.0.1:7890`），然后点击 **Apply & Restart**。

------

## 6) 在 WSL 中测试 Docker 与拉取镜像

在 Ubuntu 终端执行：

```
# 检查 docker 是否可用
docker --version
docker info

# 测试拉取
docker pull hello-world
docker run --rm hello-world
```

若 `docker pull` 超时，说明 Docker 需要代理或 VPN；回到 Docker Desktop 设置检查 Proxy 或启用系统级 VPN（TUN 模式）。

------

## 7) 安装 Node.js（通过 nvm）、Python 与 Git（在 WSL）

在 WSL 中执行：

```
# Git
sudo apt install -y git

# Python & pip & venv
sudo apt install -y python3-pip python3-venv

# nvm 安装（注意：网络可能需要代理/VPN）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# 让当前 shell 读取 nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install --lts       # 安装 LTS（例如 v22）
```

如果 `curl` 访问 GitHub 很慢，请在有 VPN/TUN 时运行或使用国内镜像。

------

## 8) 安装 VS Code 与 Remote - WSL 插件（在 Windows）

- 在 Windows 上安装 VS Code。
- 从扩展市场安装：`Remote - WSL`、`Python`（Microsoft）、`Docker`、`SQLTools` + `SQLTools PostgreSQL Driver`（推荐）等。

> 插件市场访问较慢时建议开启 VPN 下载插件。安装后从 VS Code 点击左下角 `><` 连接到 WSL。

------

## 9) 在 WSL 中准备 Docker Compose 并部署 PostgreSQL (含 pgvector) 与 Qdrant

建议在 home 下建工程目录并写 `docker-compose.yml`：

```
cd ~
mkdir -p my-ai-project && cd my-ai-project
cat > docker-compose.yml <<'EOF'
version: "3.8"
services:
  db:
    image: ankane/pgvector:latest
    container_name: ai_postgres
    restart: always
    environment:
      - POSTGRES_PASSWORD=james_5070ti
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

# 启动
docker compose up -d

# 查看容器状态
docker ps
```

**验证 PostgreSQL 已包含 vector 扩展**
 （在容器中或通过 psql 连接后执行）：

```
-- 以容器内 psql 为例：
docker exec -it ai_postgres psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT * FROM pg_extension WHERE extname='vector';"
```

或在 WSL 中安装 `psycopg2-binary` 与 `pgvector`（客户端）：

```
sudo apt install -y python3-pip
pip install psycopg2-binary pgvector --break-system-packages
python3 -c "import psycopg2, pgvector; print('AI 驱动连接成功！')"
```

------

## 10) 与 Windows 上 Ollama 的互通（关键点）

问题：Ollama（在 Windows 上运行）默认只监听本机，有时 WSL/容器请求被拒。解决方法是让 Ollama 监听所有接口并重启 Ollama。

在 Windows（以管理员身份）设置环境变量（用户变量也可）：

```
# 在 PowerShell（管理员）中运行：永久设置用户变量
setx OLLAMA_HOST 0.0.0.0
```

然后**彻底退出 Ollama**（托盘图标退出）并重新启动 Ollama。

在 WSL 中测试：

```
curl --connect-timeout 5 http://host.docker.internal:11434/api/tags
# 或使用 host.docker.internal:11434 来访问 Windows 上的 service
```

如果你用的是 `localhost` 无法访问，可尝试 `host.docker.internal`。若仍无法访问，确认防火墙是否阻止、或 Ollama 是否绑定了特定端口。

------

## 11) 常用验证命令清单（便于快速排错）

```
# WSL 状态（在 Windows PowerShell）
wsl -l -v
wsl --status

# 在 WSL
uname -a
nvidia-smi
docker --version
docker info
docker ps
docker-compose version   # 如果使用 docker-compose 二进制
curl -I https://www.google.com  # 测试网络连通性
```

------

# 网络 / VPN / 代理 说明（实务建议）

- WSL2 与宿主机网络隔离：**最稳妥**的方法是使用系统级 VPN（TUN 模式），让 WSL 自动走虚拟网卡。
- 如果使用 Docker Desktop 的代理：在 Docker Desktop → Settings → Proxies 填写 `http://127.0.0.1:<端口>` 并 Apply & Restart。常见端口：Clash（7890/7897）、v2rayN（10809）等。
- 测试网络：在 WSL 执行 `curl -I https://www.google.com`；若返回 200 则说明网络 OK。
- 对于 `apt`、`nvm`、`curl` 下载等操作，若无 VPN 请换用国内镜像源（apt 的镜像、pip -i mirror 等）。

------

# 我在整理时做了哪些“删减 / 修改 / 补充”？

1. **删除的冗余内容**：重复的 `wsl --install` 教程段落、重复的 Docker Proxy 步骤说明、以及多处内容重复的“概念性”文字（保留最关键的命令与注意事项）。
2. **合并的部分**：把散落在文档各处的 `nvm`/Node、Python、VS Code 插件、Docker Compose 等内容按执行顺序合并成一套可执行步骤。
3. **补充的内容**：添加了 DNS 持久化的正确做法（`/etc/wsl.conf`）、Docker WSL Integration 验证步骤、Postgres `CREATE EXTENSION` 验证命令、Ollama 的 `setx OLLAMA_HOST` Windows 环境变量设置说明、以及全面的验证命令清单。
4. **修正的地方**：把可能被覆盖的 `resolv.conf` 临时修改提示改为持久化方案，并补充了在没有 VPN 时的国内镜像替代建议。

（以上变动目的：把“可执行”与“可复现”放在第一位，减少读取与执行时的认知负担。）

------

# 额外建议与安全提示

- **凭证管理**：示例 `POSTGRES_PASSWORD=james_5070ti` 仅为示范，实际使用生产密码或密钥时请使用环境变量管理或 secret 管理工具。
- **端口暴露**：上面 `ports` 示例会把数据库和 qdrant 映射到宿主机，请在实际或生产环境中按需限制访问（防火墙 / 仅本地绑定 / reverse proxy）。
- **备份**：为 `postgres_data`、`qdrant_storage` 做定期备份。
- **权限**：`setx` 设置 OLLAMA_HOST 时请注意只在可信网络使用 0.0.0.0；若在公共网络下请改为更严格的绑定或使用认证与防火墙策略。

------

如果你愿意，我可以：

- 生成一个**一键执行的 shell 脚本**（用于 WSL 的配置 + 一键 `docker compose up -d`），或
- 根据你的实际 VPN 软件（比如 Clash / v2rayN / Sing-box）把 Docker Desktop 的 Proxy 配置写成具体的示例值。

要我直接把脚本和 `docker-compose.yml` 放进同一个压缩包并提供下载吗？





## 方式二：在 Windows 创建，再“放进” WSL（可行，但要注意）

### 你可以这样做：

#### 1️⃣ 在 Windows 创建文件

比如：

```
D:\scripts\wsl_init_ai_env.sh
```

#### 2️⃣ 在 WSL 中访问 Windows 盘

WSL 会自动挂载 Windows 盘：

```
cd /mnt/d/scripts
```

#### 3️⃣ 复制到 WSL 的 Linux 文件系统

⚠️ **关键一步**

```
cp wsl_init_ai_env.sh ~/
cd ~
```

#### 4️⃣ 修复换行符（非常关键）

如果你在 Windows 编辑过：

```
sudo apt install -y dos2unix
dos2unix wsl_init_ai_env.sh
```

#### 5️⃣ 再执行

```
chmod +x wsl_init_ai_env.sh
./wsl_init_ai_env.sh
```



# 三、你现在应该怎么做（一步不多，一步不少）

### ✔ 如果你现在还没装 WSL

```
wsl --install -d Ubuntu-24.04
```

### ✔ 如果你已经进了 Ubuntu

**直接在 WSL 里做：**

```
cd ~
nano wsl_init_ai_env.sh
# 粘贴脚本
chmod +x wsl_init_ai_env.sh
./wsl_init_ai_env.sh
```

------

# 四、我帮你再“校验一次认知”（很重要）

你现在脑子里的模型应该是：

```
Windows
 ├─ Docker Desktop（真正跑 docker daemon）
 ├─ Ollama（GPU）
 ├─ Clash（代理）
 │
 └─ WSL2 Ubuntu
     ├─ 执行 .sh
     ├─ docker compose up -d
     ├─ Postgres / Qdrant
     └─ 代码 & 开发
```

只要你**按这个模型做**，后面所有问题都会变成“可预期问题”，而不是玄学。

------

如果你愿意，下一步我可以直接帮你做三件更“工程化”的事之一：

1️⃣ 把脚本拆成 **install.sh / up.sh / down.sh**
 2️⃣ 给你加 **GPU 容器 + CUDA 校验**
 3️⃣ 写一个 **healthcheck + 自动自检脚本**

