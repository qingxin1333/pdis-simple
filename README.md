# PDIS 个人决策智能助手系统

基于大语言模型的个人决策支持系统，通过多LLM协作流程分析复杂人际场景，生成个性化决策建议。

## 📁 目录结构

```
pdis-simple/
├── main.py                          # PDIS主流程控制器
├── server.py                        # FastAPI Web服务器
├── full_reports.json                # 报告存储文件
├── .env                             # 环境变量配置文件
├── requirements.txt                 # Python依赖包列表
├── process/                         # 核心流程模块
│   ├── __init__.py                  # 包初始化文件
│   ├── config.py                    # 系统配置文件
│   ├── env_loader.py                # 环境变量加载器
│   ├── report_manager.py            # 报告管理器
│   ├── ollama_client.py             # LLM API客户端
│   ├── postgres_store.py            # PostgreSQL数据库存储
│   ├── llm_a_input_decomposer.py    # LLM A：输入拆分器
│   ├── llm_b_condition_checker.py   # LLM B：条件检查器
│   ├── llm_c_profile_generator.py   # LLM C：人物档案生成器
│   ├── llm_d_decision_analyzer.py   # LLM D：决策分析器
│   └── run_pipeline.py              # 运行脚本
├── web/                             # Web界面资源
│   ├── index.html                   # 主页面
│   ├── login.html                   # 登录页面
│   ├── app.js                       # 前端JavaScript
│   └── styles.css                   # 样式文件
├── test/                            # 测试目录
│   ├── test_pdis_simple.py          # PDIS测试脚本
│   ├── test_qdrant_simple.py        # Qdrant向量数据库测试
│   └── qdrant_config.py             # Qdrant配置
├── doc/                             # 项目文档目录
│   ├── 0软件与服务清单.md
│   ├── 1业务梳理与功能清单.md
│   ├── 2产品业务需求文档.md
│   ├── 3概要设计文档.md
│   ├── 4开发总览设计文档.md
│   ├── PDIS技术栈使用流程.md
│   ├── PDIS 人物性格驱动决策支持系统 - 系统文档.md
│   ├── PDIS 测试流程说明.md
│   ├── 系统架构设计说明书.md
│   └── ...                        # 其他技术文档
├── logs/                            # 日志目录
├── pics/                            # 图片资源目录
└── pdis_bench_results/              # 基准测试结果
```

## 🚀 使用方法

### 1. Web界面（推荐）
```bash
# 启动Web服务器
python server.py

# 访问 http://localhost:8000 使用Web界面
# 访问 http://localhost:8000/docs 查看API文档
```

### 2. 命令行运行
```bash
python main.py
```

### 3. 在项目根目录作为模块使用
```python
from main import PDISPipeline

pipeline = PDISPipeline()
result = pipeline.run_full_pipeline("你的决策场景描述")
```

### 4. 运行process模块
```bash
cd process
python run_pipeline.py
```

### 5. 运行测试脚本
```bash
python test/test_pdis_simple.py
```

## 🔧 模块功能说明

### 核心组件
- **ReportManager** (`process/report_manager.py`): 报告存储与管理，支持JSON格式持久化
- **OllamaClient** (`process/ollama_client.py`): LLM API调用封装，支持流式响应
- **PostgresStore** (`process/postgres_store.py`): PostgreSQL数据库存储，支持用户认证和数据持久化
- **WebServer** (`server.py`): FastAPI Web服务器，提供REST API和Web界面

### LLM功能模块
- **LLM A** (`llm_a_input_decomposer.py`): 输入拆分，识别人物、时间、地点等关键要素
- **LLM B** (`llm_b_condition_checker.py`): 条件检查，验证信息完整性，生成补充提示
- **LLM C** (`llm_c_profile_generator.py`): 人物档案生成，基于MBTI 16型人格系统分析人物性格
- **LLM D** (`llm_d_decision_analyzer.py`): 决策分析，综合所有信息生成可行性报告

### 主控制器
- **PDISPipeline** (`main.py`): 整合所有模块，协调完整的决策分析流程

### Web界面
- **前端界面** (`web/`): 现代化Web界面，支持用户注册、登录、对话历史管理
- **API接口**: RESTful API支持用户认证、决策分析、历史记录查询等功能

## ⚙️ 配置说明

### 系统配置
配置文件位于 `process/config.py`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| MODEL_LLM_A | qwen2.5:7b-instruct | 输入拆分模型 |
| MODEL_LLM_B | qwen2.5:7b-instruct | 条件判断模型 |
| MODEL_LLM_C | qwen2.5:7b-instruct | 人物档案模型 |
| MODEL_LLM_D | qwen3:8b | 决策分析模型 |
| MODEL_EMBEDDING | nomic-embed-text | 向量化模型 |
| STORAGE_FILE | full_reports.json | 报告存储文件 |
| REQUEST_TIMEOUT | 600 | 请求超时时间(秒) |
| OLLAMA_ENDPOINT | http://127.0.0.1:11434/api/generate | Ollama API端点 |

### 环境变量配置
在项目根目录的 `.env` 文件中配置：

| 环境变量 | 示例值 | 说明 |
|----------|--------|------|
| DATABASE_URL | postgresql://postgres:password@localhost:5432/pdis | PostgreSQL数据库连接字符串 |
| PDIS_DEFAULT_USER_EMAIL | local@pdis | 默认用户邮箱（本地模式） |
| PDIS_DEFAULT_USER_DISPLAY_NAME | Local User | 默认用户显示名称 |

### MBTI 16型人格系统
系统使用MBTI (Myers-Briggs Type Indicator) 16型人格理论进行人物性格分析：

**四个维度：**
- **E/I (外向/内向)**: 能量来源
- **S/N (感觉/直觉)**: 信息处理方式
- **T/F (思考/情感)**: 决策方式
- **J/P (判断/感知)**: 生活方式

**16种人格类型：**
- **ISTJ**: 务实主义者 - 严肃、安静，依靠事实和记忆
- **ISFJ**: 守护者 - 安静、友好、有责任感
- **INFJ**: 提倡者 - 寻求意义、有洞察力
- **INTJ**: 建筑师 - 有原创思维、果断
- **ISTP**: 鉴赏家 - 冷静、灵活、分析性强
- **ISFP**: 探险家 - 安静、友好、敏感
- **INFP**: 调停者 - 忠诚、理想主义、适应性强
- **INTP**: 逻辑学家 - 逻辑性强、创新、好奇
- **ESTP**: 企业家 - 精力充沛、感知敏锐
- **ESFP**: 表演者 - 自发、精力充沛、热情
- **ENFP**: 竞选者 - 热情、有创造力、社交能力强
- **ENTP**: 辩论家 - 聪明、好奇、创新
- **ESTJ**: 总经理 - 务实、现实、果断
- **ESFJ**: 执政官 - 有责任心、合作意识强
- **ENFJ**: 主人公 - 有魅力、鼓舞人心
- **ENTJ**: 指挥官 - 大胆、有想象力、意志坚强

## ✅ 测试验证

运行测试脚本验证系统功能：
```bash
# PDIS主流程测试
python test/test_pdis_simple.py

# Qdrant向量数据库测试
python test/test_qdrant_simple.py
```

## 📝 注意事项

1. **依赖服务**: 需要运行Ollama服务并下载相应模型（qwen2.5:7b-instruct、qwen3:8b、nomic-embed-text）
2. **网络配置**: 确保OLLAMA_ENDPOINT配置的IP和端口可访问
3. **数据库配置**: 
   - PostgreSQL数据库（可选，用于Web界面用户认证和数据持久化）
   - 如不配置DATABASE_URL，系统将使用本地JSON文件存储
4. **向量数据库**: 可选Qdrant支持，用于高级检索功能
5. **Python版本**: 建议使用Python 3.8+

### 数据库设置
如需使用完整Web功能，请配置PostgreSQL数据库：

```bash
# 安装PostgreSQL（Ubuntu/Debian）
sudo apt-get install postgresql postgresql-contrib

# 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE pdis;
CREATE USER pdis_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pdis TO pdis_user;
\q

# 更新.env文件中的DATABASE_URL
DATABASE_URL=postgresql://pdis_user:your_password@localhost:5432/pdis
```

## 🎯 系统优势

- ✅ **模块化设计**: 功能模块化，职责清晰，易于维护
- ✅ **多LLM协作**: 4个专用LLM分工协作，各尽其能
- ✅ **人格驱动**: 基于MBTI 16型人格理论的人物分析
- ✅ **Web界面**: 现代化Web界面，支持用户认证和历史管理
- ✅ **数据库支持**: PostgreSQL数据库存储，支持多用户和数据持久化
- ✅ **交互式分析**: 支持信息补充和迭代优化
- ✅ **报告持久化**: 自动保存分析结果到JSON文件和数据库
- ✅ **RESTful API**: 完整的API接口，支持第三方集成
- ✅ **向后兼容**: 原有功能保持完全一致

## 📦 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 依赖包说明：
# - requests: HTTP请求库
# - psycopg2-binary: PostgreSQL数据库驱动
# - fastapi: Web框架
# - uvicorn: ASGI服务器
# - pydantic: 数据验证和序列化
```

## 📚 相关文档

详细设计文档位于 `doc/` 目录：
- 业务需求文档
- 系统架构设计
- 开发总览文档
- 测试流程说明
- 环境安装指南

---

**版本**: 1.0.0  
**作者**: PDIS Team
