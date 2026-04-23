# PDIS 个人决策智能助手系统

## 📁 目录结构

```
process/
├── __init__.py                  # 包初始化文件
├── config.py                    # 系统配置文件
├── report_manager.py           # 报告管理器
├── ollama_client.py            # LLM客户端
├── llm_a_input_decomposer.py   # LLM A：输入拆分器
├── llm_b_condition_checker.py  # LLM B：条件检查器
├── llm_c_profile_generator.py  # LLM C：人物档案生成器
├── llm_d_decision_analyzer.py  # LLM D：决策分析器
├── pdis_pipeline.py            # 主流程控制器
└── run_pipeline.py             # 运行脚本（解决相对导入问题）
```

## 🚀 使用方法

### 1. 直接运行模块化版本
```bash
cd process
python run_pipeline.py
```

### 2. 在项目根目录使用
```python
from process import PDISPipeline

pipeline = PDISPipeline()
result = pipeline.run_full_pipeline()
```

### 3. 使用原有文件（功能保持不变）
```bash
python test_pdis_llmc.py
```

## 🔧 模块功能说明

### 核心组件
- **ReportManager**: 报告存储与管理
- **OllamaClient**: LLM API调用封装

### LLM功能模块
- **LLM A**: 输入拆分，识别人物、时间、地点等关键要素
- **LLM B**: 条件检查，验证信息完整性
- **LLM C**: 人物档案生成，基于九型人格系统
- **LLM D**: 决策分析，生成可行性报告

### 主控制器
- **PDISPipeline**: 协调所有模块，执行完整流程

## ⚙️ 配置说明

配置文件位于 `process/config.py`：
- 模型配置（MODEL_LLM_A, MODEL_LLM_B等）
- 系统参数（超时时间、存储文件等）
- 九型人格系统说明

## ✅ 测试验证

运行验证脚本确认模块化拆分成功：
```bash
python verify_modularization.py
```

## 📝 注意事项

1. **相对导入问题**：直接在process目录下运行模块文件会出现导入错误，建议使用 `run_pipeline.py`
2. **兼容性**：原有 `test_pdis_llmc.py` 文件功能保持完全一致
3. **依赖**：需要运行Ollama服务并下载相应模型

## 🎯 优势

- ✅ 功能模块化，职责清晰
- ✅ 易于维护和扩展
- ✅ 保持向后兼容
- ✅ 支持独立测试各组件