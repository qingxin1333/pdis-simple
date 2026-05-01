"""
PDIS系统配置文件
定义全局模型变量和其他配置参数
"""

import os

from .env_loader import load_env_file

_ROOT_ENV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_env_file(_ROOT_ENV)

# ===================== 全局模型变量 =====================
MODEL_LLM_A = "qwen2.5:7b-instruct"  # 用于LLM A (输入拆分)
MODEL_LLM_B = "qwen2.5:7b-instruct"  # 用于LLM B (条件判断)
MODEL_LLM_C = "qwen2.5:7b-instruct"  # 用于LLM C (人物档案生成)
MODEL_LLM_D = "qwen3:8b"  # 用于LLM D (决策分析)
MODEL_EMBEDDING = "nomic-embed-text"  # 用于向量化（pgvector / Qdrant）

# ===================== 系统配置 =====================
STORAGE_FILE = "full_reports.json"  # 报告存储文件
REQUEST_TIMEOUT = 600  # LLM请求超时时间(秒)
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"  # Ollama API端点

# ===================== 数据库（可选） =====================
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DEFAULT_USER_EMAIL = os.getenv("PDIS_DEFAULT_USER_EMAIL", "local@pdis")
DEFAULT_USER_DISPLAY_NAME = os.getenv("PDIS_DEFAULT_USER_DISPLAY_NAME", "Local User")

# ===================== MBTI 16 型人格 =====================
MBTI_SYSTEM = """
MBTI (Myers-Briggs Type Indicator) is based on Carl Jung's psychological types.
It has four dichotomies, forming 16 personality types:
- E/I (Extraversion/Introversion): energy source
- S/N (Sensing/Intuition): information processing
- T/F (Thinking/Feeling): decision making
- J/P (Judging/Perceiving): lifestyle approach

Your task is to infer MBTI type ONLY from the provided evidence in the user's text.
If evidence is insufficient, output low confidence and keep fields minimal.
"""
