# PDIS 个人决策智能助手系统

基于大语言模型的个人决策支持系统，通过多LLM协作流程分析复杂人际场景，生成个性化决策建议。

## 📁 目录结构

```
pdis-simple/
├── main.py                          # PDIS主流程控制器
├── full_reports.json                # 报告存储文件
├── process/                         # 核心流程模块
│   ├── __init__.py                  # 包初始化文件
│   ├── config.py                    # 系统配置文件
│   ├── report_manager.py            # 报告管理器
│   ├── ollama_client.py             # LLM API客户端
│   ├── llm_a_input_decomposer.py    # LLM A：输入拆分器
│   ├── llm_b_condition_checker.py   # LLM B：条件检查器
│   ├── llm_c_profile_generator.py   # LLM C：人物档案生成器
│   ├── llm_d_decision_analyzer.py   # LLM D：决策分析器
│   ├── pdis_pipeline.py             # 主流程控制器（备份）
│   ├── run_pipeline.py              # 运行脚本
│   └── README.md                    # 模块说明文档
├── doc/                             # 项目文档目录
│   ├── 0软件与服务清单.md
│   ├── 1业务梳理与功能清单.md
│   ├── 2产品业务需求文档.md
│   ├── 3概要设计文档.md
│   ├── 4开发总览设计文档.md
│   ├── PDIS 人物性格驱动决策支持系统 - 系统文档.md
│   ├── PDIS 测试流程说明.md
│   ├── 系统架构设计说明书.md
│   └── ...                        # 其他技术文档
├── test/                            # 测试目录
│   ├── test_pdis_simple.py          # PDIS测试脚本
│   ├── test_qdrant_simple.py        # Qdrant向量数据库测试
│   └── qdrant_config.py             # Qdrant配置
└── pdis_bench_results/              # 基准测试结果
```

## 🚀 使用方法

### 1. 直接运行主流程（推荐）
```bash
python main.py
```

### 2. 在项目根目录作为模块使用
```python
from main import PDISPipeline

pipeline = PDISPipeline()
result = pipeline.run_full_pipeline("你的决策场景描述")
```

### 3. 运行process模块
```bash
cd process
python run_pipeline.py
```

### 4. 运行测试脚本
```bash
python test/test_pdis_simple.py
```

## 🔧 模块功能说明

### 核心组件
- **ReportManager** (`process/report_manager.py`): 报告存储与管理，支持JSON格式持久化
- **OllamaClient** (`process/ollama_client.py`): LLM API调用封装，支持流式响应

### LLM功能模块
- **LLM A** (`llm_a_input_decomposer.py`): 输入拆分，识别人物、时间、地点等关键要素
- **LLM B** (`llm_b_condition_checker.py`): 条件检查，验证信息完整性，生成补充提示
- **LLM C** (`llm_c_profile_generator.py`): 人物档案生成，基于九型人格系统分析人物性格
- **LLM D** (`llm_d_decision_analyzer.py`): 决策分析，综合所有信息生成可行性报告

### 主控制器
- **PDISPipeline** (`main.py`): 整合所有模块，协调完整的决策分析流程

## ⚙️ 配置说明

配置文件位于 `process/config.py`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| MODEL_LLM_A | qwen2.5:7b-instruct | 输入拆分模型 |
| MODEL_LLM_B | qwen2.5:7b-instruct | 条件判断模型 |
| MODEL_LLM_C | qwen2.5:7b-instruct | 人物档案模型 |
| MODEL_LLM_D | qwen3:8b | 决策分析模型 |
| STORAGE_FILE | full_reports.json | 报告存储文件 |
| REQUEST_TIMEOUT | 600 | 请求超时时间(秒) |
| OLLAMA_ENDPOINT | http://192.168.1.8:11434/api/generate | Ollama API端点 |

### 九型人格系统
系统使用Enneagram九型人格理论进行人物性格分析：
- **完美型(1)**: 追求完美与正确
- **助人型(2)**: 重视他人认同
- **成就型(3)**: 成就导向
- **浪漫型(4)**: 情感深度与个性
- **观察型(5)**: 知识寻求与超然
- **怀疑型(6)**: 安全寻求与忠诚
- **享乐型(7)**: 享乐寻求与自发
- **领导型(8)**: 果断与控制
- **和平型(9)**: 和谐寻求与和平主义

## ✅ 测试验证

运行测试脚本验证系统功能：
```bash
# PDIS主流程测试
python test/test_pdis_simple.py

# Qdrant向量数据库测试
python test/test_qdrant_simple.py
```

## 📝 注意事项

1. **依赖服务**: 需要运行Ollama服务并下载相应模型（qwen2.5:7b-instruct、qwen3:8b）
2. **网络配置**: 确保OLLAMA_ENDPOINT配置的IP和端口可访问
3. **向量数据库**: 可选Qdrant支持，用于高级检索功能
4. **Python版本**: 建议使用Python 3.8+

## 🎯 系统优势

- ✅ **模块化设计**: 功能模块化，职责清晰，易于维护
- ✅ **多LLM协作**: 4个专用LLM分工协作，各尽其能
- ✅ **人格驱动**: 基于MBTI16型人格理论的人物分析
- ✅ **交互式分析**: 支持信息补充和迭代优化
- ✅ **报告持久化**: 自动保存分析结果到JSON文件
- ✅ **向后兼容**: 原有功能保持完全一致

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
