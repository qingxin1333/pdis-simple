"""
LLM C模块：人物档案生成器
基于九型人格系统生成详细的人物性格档案
"""

import json
from typing import Dict, Any
from .ollama_client import OllamaClient
from .config import MODEL_LLM_C, ENNEAGRAM_SYSTEM


class LLM_C_ProfileGenerator:
    """
    LLM C: 人物档案生成引擎
    核心功能：根据人物描述生成基于九型人格系统的详细档案
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
Analyze the ENTIRE USER INPUT to determine personality type using the Enneagram system (nine personality types).

{ENNEAGRAM_SYSTEM}

PERSON KEY: {person_key}
DESCRIPTION: {description}

FULL USER INPUT CONTEXT (for reference):
{full_context}

INSTRUCTIONS:
1. ONLY focus on the person with key "{person_key}" and their role in the context.
2. Analyze their behavior, attitude, and interactions mentioned in the full context.
3. Determine the Enneagram type based on the description provided:
   - Use the nine types listed above (perfect/helpful/accomplished/romantic/observational/skeptical/hedonic/leadership/peaceful)
4. Extract core traits, communication style, decision focus, strengths, and weaknesses.
5. Use ONLY the information provided in the full context (do not assume).
6. If information is insufficient for any field, leave it as empty string or empty list.
7. Return ONLY the JSON object, no additional text.
8. ADD A NEW FIELD "personality_original" THAT CONTAINS THE PERSONALITY TYPE IN THE ORIGINAL LANGUAGE OF THE INPUT:
   - If the input is in Chinese (contains Chinese characters), use the Chinese term from the system description (e.g., "领导型")
   - DO NOT use Japanese, English, or any other language for personality_original
   - ALWAYS use Chinese for personality_original when input contains Chinese characters

EXAMPLES (for reference):
- If input is in Chinese: "技术部负责人，对节能算法项目感兴趣，喜欢主动推动技术讨论，关注细节，善于沟通" 
  → personality_color: "leadership", personality_original: "领导型"

- If input is in Chinese: "后端负责人是个公司员老，感觉对我的态度不热情，也没有故意针对，时间有限，不想搞事情。"
  → personality_color: "peaceful", personality_original: "和平型"

OUTPUT_SCHEMA:
{{
  "person_key": "{person_key}",
  "identity_summary": "1-2 sentence summary of this person's role and key characteristics",
  "personality_report": {{
    "core_traits": ["trait1", "trait2", ...],
    "communication_style": "how they communicate (e.g., direct, diplomatic)",
    "decision_focus": "what they prioritize in decisions",
    "personality_color": "perfect/helpful/accomplished/romantic/observational/skeptical/hedonic/leadership/peaceful",
    "personality_original": "type in original language (MUST be Chinese if input contains Chinese characters)",
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...]
  }},
  "profiling_report": {{
    "decision_drivers": ["what drives their decisions"],
    "pressure_points": ["what causes stress for them"],
    "likely_reactions": ["how they might react in key scenarios"]
  }}
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