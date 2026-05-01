"""
LLM C模块：人物档案生成器
基于 MBTI 16 型人格生成详细的人物侧写档案
"""

import json
from typing import Dict, Any
from .ollama_client import OllamaClient
from .config import MODEL_LLM_C, MBTI_SYSTEM


class LLM_C_ProfileGenerator:
    """
    LLM C: 人物档案生成引擎
    核心功能：根据人物描述生成基于 MBTI 16 型人格系统的详细档案
    """

    def __init__(self):
        self.current_context = None  # 缓存完整上下文

    def set_context(self, context: Dict[str, Any]):
        """设置当前分析上下文"""
        self.current_context = context

    def generate_profile(self, person_key: str, description: str) -> Dict[str, Any]:
        """
        根据人物描述生成性格报告
        :param person_key: 人物键值
        :param description: 人物描述
        :return: 完整的人物档案
        """
        if not self.current_context:
            raise ValueError("No context available. Set context first.")

        full_context = self.current_context.get("user_text", "")

        prompt = f"""
You are a professional personality profiling engine.
Analyze the ENTIRE USER INPUT to infer MBTI type and a structured portrait for the target person.

{MBTI_SYSTEM}

PERSON KEY: {person_key}
DESCRIPTION: {description}

FULL USER INPUT CONTEXT (for reference):
{full_context}

INSTRUCTIONS:
1. ONLY focus on the person with key "{person_key}" and their role in the context.
2. Analyze their behavior, attitude, and interactions mentioned in the full context.
3. Infer MBTI type (e.g., INTJ/ENFP) ONLY if evidence is present. Otherwise keep type empty and confidence low.
4. Provide evidence bullets that justify the MBTI inference.
5. Extract core traits, communication style, decision focus, strengths, weaknesses, triggers, and predicted behaviors.
6. Use ONLY the information provided in the full context (do not assume).
7. If information is insufficient for any field, leave it as empty string or empty list.
8. Return ONLY the JSON object, no additional text.
9. If the input contains Chinese characters, all strings in the output must be Chinese (no English).

OUTPUT_SCHEMA:
{{
  "person_key": "{person_key}",
  "identity_summary": "1-2 sentence summary of this person's role and key characteristics",
  "mbti": {{
    "type": "",
    "confidence": 0.0,
    "evidence": ["evidence1", "evidence2"]
  }},
  "traits": {{
    "core_traits": ["trait1", "trait2"],
    "communication_style": "",
    "decision_focus": "",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "triggers": ["trigger1", "trigger2"]
  }},
  "behavior_predictions": [
    {{
      "scenario": "a scenario description",
      "prediction": "likely behavior",
      "confidence": 0.0
    }}
  ]
}}
"""
        print(f"\n================ LLM C - 生成人物档案 - {person_key} ================")
        print(f"描述: {description}")
        print(f"完整上下文: {full_context[:200]}... (完整上下文已提供)")

        result = OllamaClient.call_model(MODEL_LLM_C, prompt)
        print("\n================ LLM C - 人物档案生成结果 ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        return result

    def clear_context(self):
        """清空当前上下文"""
        self.current_context = None


# 用于测试
if __name__ == "__main__":
    generator = LLM_C_ProfileGenerator()
    
    # 设置测试上下文
    test_context = {
        "user_text": "技术部负责人张三对节能算法很感兴趣，喜欢主动推动讨论。后端负责人李四时间有限，不想搞事情。"
    }
    generator.set_context(test_context)
    
    # 生成测试档案
    profile = generator.generate_profile(
        "Technical_Manager", 
        "技术部负责人，对节能算法项目感兴趣，喜欢主动推动技术讨论"
    )
    print("生成的档案:", json.dumps(profile, indent=2, ensure_ascii=False))
