"""
PDIS流程模块包
包含完整的个人决策智能助手系统组件
"""

# 配置模块
from .config import (
    MODEL_LLM_A,
    MODEL_LLM_B, 
    MODEL_LLM_C,
    MODEL_LLM_D,
    MODEL_EMBEDDING,
    STORAGE_FILE,
    REQUEST_TIMEOUT,
    OLLAMA_ENDPOINT,
    DATABASE_URL,
    MBTI_SYSTEM,
)

# 核心基础组件
from .report_manager import ReportManager
from .ollama_client import OllamaClient

# LLM功能模块
from .llm_a_input_decomposer import LLM_A_InputDecomposer
from .llm_b_condition_checker import LLM_B_ConditionChecker
from .llm_c_profile_generator import LLM_C_ProfileGenerator
from .llm_d_decision_analyzer import LLM_D_DecisionAnalyzer

__all__ = [
    # 配置
    'MODEL_LLM_A',
    'MODEL_LLM_B',
    'MODEL_LLM_C',
    'MODEL_LLM_D',
    'MODEL_EMBEDDING',
    'STORAGE_FILE',
    'REQUEST_TIMEOUT',
    'OLLAMA_ENDPOINT',
    'DATABASE_URL',
    'MBTI_SYSTEM',
    
    # 核心组件
    'ReportManager',
    'OllamaClient',
    
    # LLM模块
    'LLM_A_InputDecomposer',
    'LLM_B_ConditionChecker',
    'LLM_C_ProfileGenerator',
    'LLM_D_DecisionAnalyzer',
    
]

# 版本信息
__version__ = "1.0.0"
__author__ = "PDIS Team"
