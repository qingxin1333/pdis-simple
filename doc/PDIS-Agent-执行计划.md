# PDIS-Agent 执行计划 (精简版)

## 目标
将现有PDIS流水线系统，逐步重构为"个人决策小秘书智能体"

---

## 核心转变

```
原来: 用户输入 → [LLM-A→B→C→D] → 输出结果 (一次性)
      
现在: 用户对话 → Agent循环 [感知→记忆→推理→行动→反馈] → 持续对话
```

---

## 三阶段实施计划

### 第一阶段: Agent核心框架 (当前)

**目标**: 让Agent能"思考"和"对话"

**要写的代码**:
```
agent/
├── core/
│   ├── agent.py          # Agent主循环 (ReAct)
│   ├── perception.py     # 意图识别
│   └── memory.py         # 简单记忆存储
├── tools/
│   ├── base.py           # 工具基类
│   ├── llm_a_tool.py     # 封装现有LLM-A
│   ├── llm_c_tool.py     # 封装现有LLM-C
│   ├── llm_d_tool.py     # 封装现有LLM-D
│   └── profile_tools.py  # 人物档案工具
└── cli.py                # 命令行交互
```

**验收标准**:
- [ ] 用户输入一句话，Agent能理解意图
- [ ] Agent能判断是否需要补充信息
- [ ] Agent能调用现有LLM进行决策分析
- [ ] 多轮对话状态正常保持

---

### 第二阶段: 记忆增强

**目标**: Agent能"记住"人物和决策

**要写的代码**:
```
agent/memory/
├── short_term.py         # 工作记忆 (当前对话)
├── long_term.py          # 长期记忆
│   ├── profile_store.py  # 人物档案存储
│   ├── decision_store.py # 决策历史存储
│   └── vector_store.py   # 语义检索 (SQLite→PG)
└── retriever.py          # 记忆召回模块
```

**验收标准**:
- [ ] 能创建和查询人物档案
- [ ] 能搜索历史决策记录
- [ ] 相关记忆能自动召回

---

### 第三阶段: Web界面

**目标**: 有友好的聊天界面

**技术栈**:
```
前端: React/Vue + 流式输出(SSE)
后端: FastAPI + WebSocket
```

**验收标准**:
- [ ] 聊天界面可输入输出
- [ ] 支持流式显示Agent思考过程
- [ ] 移动端可用

---

## 本周具体任务

### Day 1-2: Agent核心循环

创建 `agent/core/agent.py`:

```python
class PDISAgent:
    """PDIS决策小秘书Agent"""
    
    def __init__(self):
        self.memory = SimpleMemory()  # 先用最简单的
        self.tools = ToolRegistry()
        self.llm = OllamaClient()
    
    def chat(self, user_input: str) -> str:
        # 1. 理解意图
        intent = self.understand(user_input)
        
        # 2. 加载记忆
        context = self.memory.load(intent.entities)
        
        # 3. Agent决策循环
        for _ in range(5):  # 最多5轮思考
            # 思考下一步
            thought = self.llm.think(user_input, intent, context)
            
            # 决定行动
            action = self.decide(thought)
            
            # 执行行动
            if action.type == "ask_user":
                return action.question  # 暂停，等用户回复
            
            elif action.type == "analyze":
                return self.tools["analyze"].run(intent, context)
            
            elif action.type == "need_info":
                context += self.tools["search_profile"].run(intent.persons)
                continue
        
        return "思考超时，请重试"
```

### Day 3-4: 工具封装

将现有4个LLM封装为Tool:

```python
class LLM_A_Tool(BaseTool):
    """输入拆分工具"""
    name = "decompose_input"
    
    def run(self, text: str) -> dict:
        # 调用现有 llm_a_input_decomposer.py
        return self.llm_a.decompose_input(text)

class LLM_D_Tool(BaseTool):
    """决策分析工具"""
    name = "analyze_decision"
    
    def run(self, scenario, persons, profiles) -> dict:
        # 调用现有 llm_d_decision_analyzer.py
        return self.llm_d.analyze_decision(scenario, persons, profiles)
```

### Day 5-7: CLI交互

创建 `agent/cli.py`:

```python
def main():
    agent = PDISAgent()
    print("PDIS-Agent 已启动，输入exit退出")
    
    while True:
        user_input = input("\n你: ")
        if user_input == "exit":
            break
        
        response = agent.chat(user_input)
        print(f"\nAgent: {response}")

if __name__ == "__main__":
    main()
```

---

## 关键设计决策 (已确定)

| 决策项 | 方案 | 理由 |
|--------|------|------|
| Agent框架 | 先不用LangChain | 保持简单，直接调LLM |
| 记忆存储 | SQLite起步 | 你的文档说"数据量不大时PG够用" |
| 模型选择 | 沿用Ollama本地模型 | 成本低，响应快 |
| 旧代码处理 | 封装为Tool | 逐步迁移，不废弃 |

---

## 下一步行动

1. **创建分支**: `git checkout -b feature/agent-core`
2. **写Agent核心**: 按上面代码框架实现
3. **跑通闭环**: 验证能对话、能分析、能记忆
4. **遇到问题**: 随时讨论，逐步迭代

---

## 预期效果 (MVP)

```
用户: 我想和老板谈加薪
Agent: 好的，为了给你更准确的建议，我需要了解一些信息：
       1. 你老板的性格怎样？
       2. 你入职多久了？
       3. 有加薪的硬性理由吗？

用户: 老板比较强势，入职2年，有外部offer
Agent: [调用LLM-D分析后]
       基于这些信息，我的分析如下：
       可行性: 中高
       建议策略: ...
       风险提示: ...

用户: 保存这个分析，我想下周再谈
Agent: 已保存到"加薪谈判-老板"案例。
       需要我下周提醒你吗？
```

---

## 文件结构 (目标)

```
pdis-simple/
├── agent/                    # 新增Agent核心
│   ├── core/
│   ├── tools/
│   ├── memory/
│   └── cli.py
├── process/                  # 现有代码保留
│   ├── llm_a_input_decomposer.py
│   ├── llm_d_decision_analyzer.py
│   └── ...
├── storage/                  # 数据存储
│   ├── profiles.db           # SQLite人物档案
│   └── conversations/        # 对话历史
├── main.py                   # 保留旧入口
├── agent_cli.py              # 新增Agent入口
└── PDIS-Agent-智能体架构重构规划-v1.md  # 详细规划
```

---

**开始动手吧！先写Agent核心循环，跑起来再说。**
