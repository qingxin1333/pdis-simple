# Personal Decision Intelligence System - 系统文档

个人决策小秘书



## **1. 系统概述**

PDIS（Personality-Driven Decision Support）是一个基于大语言模型的决策支持系统，通过分析用户输入中的人物性格特征，生成针对性的决策建议。系统采用**四阶段工作流**，结合九型人格理论和RAG（检索增强生成）策略，实现从输入分析到决策建议的全流程自动化。

------

## **2. 核心流程**

### **2.1 四阶段工作流**



### **2.2 关键流程说明**

1. **LLM A：输入拆分**
   - 提取所有人物角色
   - 识别时间信息（如"本周三"）
   - 生成场景摘要（1-2句）
   - *示例输出*：`{"identified_persons": [{"mention": "老板", "person_key": "CEO", ...}]}`
2. **LLM C：人物档案生成**
   - 基于九型人格理论分析人物性格
   - 生成结构化档案（含`personality_original`中文术语）
   - *关键修复*：强制中文输入输出中文术语（如`leadership` → `领导型`）
3. **LLM B：条件判断**
   - 检查必要信息是否完整：
     - 时间信息
     - 位置信息
     - 人物档案完整性
   - 生成补充问题（如"请补充具体时间"）
4. **LLM D：决策分析**
   - 融合历史报告摘要（RAG策略）
   - 生成可执行决策建议
   - 用原始人名替换person_key（如`Technical_Manager` → `技术部负责人`）

------

## **3. 关键组件说明**

### **3.1 报告管理器 (ReportManager)**

表格



| 功能   | 说明         | 实现方式                                  |
| :----- | :----------- | :---------------------------------------- |
| **写** | 保存完整报告 | `save_report()` → `full_reports.json`     |
| **压** | 生成摘要     | `_generate_summary()`（长度>100字符截断） |
| **隔** | 独立存储摘要 | `self.summaries`字典（按类型隔离）        |
| **选** | RAG检索      | `get_context()`返回相关摘要               |

> ✅ **设计亮点**：实现"写-压-隔-选"四步RAG策略，避免重复生成

### **3.2 九型人格系统（核心修复点）**

表格



| 人格类型     | 英文 | 中文术语 | 系统修正         |
| :----------- | :--- | :------- | :--------------- |
| `leadership` | 8号  | 领导型   | ✅ 正确           |
| `peaceful`   | 9号  | 和平型   | ✅ 正确           |
| `skeptical`  | 6号  | 忠诚型   | ❌ 原错误"怀疑型" |

> 💡 **关键改进**：在LLM C提示词中强制要求`personality_original`必须使用中文术语

------

## **4. 代码结构**

### **4.1 主要类**

表格



| 类名               | 职责           | 核心方法                                           |
| :----------------- | :------------- | :------------------------------------------------- |
| `ReportManager`    | 报告存储与检索 | `save_report()`, `get_context()`                   |
| `PDISPipelineTest` | 核心流程引擎   | `run_full_pipeline()`, `generate_person_profile()` |
| `OllamaClient`     | LLM调用封装    | `call_model()`                                     |

### **4.2 核心流程执行顺序**

python

编辑







```
def run_full_pipeline():
    # 1. LLM A: 输入拆分
    decomposed = self.run_llm_a(user_text)
    
    # 2. 生成缺失人物档案 (LLM C)
    for person in decomposed["identified_persons"]:
        if person_key not in self.person_registry:
            profile = self.generate_person_profile(...)
    
    # 3. 条件检查 (LLM B)
    readiness = self.run_llm_b()
    
    # 4. 信息补充 (模拟用户)
    if not readiness["ready"]:
        supplement = ... 
        user_text += supplement
        decomposed = self.run_llm_a(user_text)  # 重新拆分
    
    # 5. 决策分析 (LLM D)
    final_result = self.run_llm_d()
```

------

## **5. 运行示例**

### **5.1 输入场景**

> "老板是个喜欢演讲的人，到处跟人聊AI项目，但没详细规划..."

### **5.2 系统输出**

json

编辑







```
{
  "person_key": "CEO",
  "personality_report": {
    "personality_color": "leadership",
    "personality_original": "领导型"  // ✅ 正确中文术语
  }
}
```

### **5.3 决策分析输出**

text

编辑







```
决策可行性分析报告：
可行性：中等
信心度：0.75
关键原因：老板性格为领导型，易受新概念影响但缺乏规划
执行计划：1. 提前与技术负责人确认PPT内容 2. 用节能算法案例强化演示
风险：老板可能突然改变需求
缺失信息：具体项目资源投入计划
```

------

## **6. 系统优势**

表格



| 优势           | 说明              | 实现方式               |
| :------------- | :---------------- | :--------------------- |
| **语言一致性** | 中文输入→中文输出 | LLM C提示词强制规则    |
| **历史上下文** | 重用历史报告      | ReportManager的RAG机制 |
| **人名友好**   | 使用原始人名      | LLM D二次替换机制      |
| **错误自愈**   | 自动请求补充      | LLM B条件判断          |
| **可扩展性**   | 新增人物类型      | 仅需扩展九型人格系统   |

------

## **7. 部署与使用**

### **7.1 环境要求**

- Ollama服务运行在`localhost:11434`
- 安装依赖：`requests`, `python-dotenv`
- 模型要求：`qwen2.5:7b-instruct`, `qwen3:8b`

### **7.2 快速启动**

bash

编辑







```
# 安装依赖
pip install requests

# 启动Ollama服务（需提前下载模型）
ollama serve

# 运行系统
python pdis_pipeline.py
```

### **7.3 输出文件**

- `full_reports.json`：完整报告存储
- 自动保存的决策摘要：`摘要: 决策可行性分析报告：...`

------

> **系统价值**：通过精准的人物性格分析（非主观猜测），为职场决策提供心理学依据，避免"误判性格导致沟通失败"的常见问题。当前版本已解决中文术语错误问题，确保输出一致性。