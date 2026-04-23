"""
PDIS系统配置文件
定义全局模型变量和其他配置参数
"""

# ===================== 全局模型变量 =====================
MODEL_LLM_A = "qwen2.5:7b-instruct"  # 用于LLM A (输入拆分)
MODEL_LLM_B = "qwen2.5:7b-instruct"  # 用于LLM B (条件判断)
MODEL_LLM_C = "qwen2.5:7b-instruct"  # 用于LLM C (人物档案生成)
MODEL_LLM_D = "qwen3:8b"  # 用于LLM D (决策分析)

# ===================== 系统配置 =====================
STORAGE_FILE = "full_reports.json"  # 报告存储文件
REQUEST_TIMEOUT = 600  # LLM请求超时时间(秒)
OLLAMA_ENDPOINT = "http://192.168.1.8:11434/api/generate"  # Ollama API端点

# ===================== 九型人格 =====================
ENNEAGRAM_SYSTEM = """
Enneagram is a conceptual theory that divides personality into nine basic types, classified based on thinking patterns, emotional reactions, and behavioral habits, namely:
- perfect (1): Perfectionism pursuing correctness
- helpful (2): Emphasizing identification with others
- accomplished (3): Achievement orientation
- romantic (4): Emotional depth and individualism
- observational (5): Knowledge-seeking and detachment
- skeptical (6): Security-seeking and loyalty
- hedonic (7): Enjoyment-seeking and spontaneity
- leadership (8): Assertiveness and control
- peaceful (9): Harmony-seeking and pacifism

Each type corresponds to specific core motivations, underlying fears, and behavioral characteristics.
"""