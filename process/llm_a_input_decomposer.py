"""
LLM A模块：输入拆分器
负责将用户输入分解为结构化要素
"""

import json
from typing import Dict, Any, List
from .ollama_client import OllamaClient
from .config import MODEL_LLM_A


class LLM_A_InputDecomposer:
    """
    LLM A: 输入拆分引擎
    核心功能：识别关键要素（人物、时间、地点、场景）
    """

    def __init__(self):
        self.current_context = None  # 缓存当前分析上下文

    def decompose_input(self, user_text: str) -> Dict[str, Any]:
        """
        拆分用户输入，识别关键要素
        :param user_text: 用户原始输入文本
        :return: 结构化的分解结果
        """
        prompt = f"""
You are a structured input decomposition engine.
Extract ALL key elements from the text with these rules:
1. EXTRACT EVERY PERSON MENTIONED (including roles, attitudes, and key characteristics)
2. EXTRACT ALL TIME INFORMATION (dates, days, deadlines)
3. EXTRACT ALL LOCATION INFORMATION
4. WRITE A CONCISE SCENARIO SUMMARY (1-2 sentences)
5. GENERATE A UNIQUE PERSON_KEY FOR EACH PERSON (format: [Role]_[LastName] or [Role]_ID)
   - For Chinese names/roles, convert them to English and use as the key
   - Example: "技术部负责人" -> "Technical_Manager"
   - Example: "后端负责人" -> "Backend_Lead"
   - Example: "老板" -> "CEO"
   - Example: "老板娘" -> "COO"
   - Always use consistent naming (e.g., if "老板" is "CEO", then "老板娘" should be "COO")
   - Make sure person_key is unique for each person
6. RETURN ONLY JSON, NO ADDITIONAL TEXT

EXAMPLE:
USER_INPUT: "张三负责技术部，喜欢主动推动讨论。李四后端负责人，对文档不满。本周三交PPT，周五评选。"
OUTPUT: {{
  "identified_persons": [
    {{
      "mention": "张三",
      "person_key": "Technical_Manager",
      "confidence": 0.9,
      "description": "技术部负责人，喜欢主动推动讨论"
    }},
    {{
      "mention": "李四",
      "person_key": "Backend_Lead",
      "confidence": 0.8,
      "description": "后端负责人，对文档不满"
    }}
  ],
  "time_info": {{
    "raw_text": "本周三交PPT，周五评选",
    "date": "本周三，本周五"
  }},
  "location_info": "",
  "scenario_summary": "用户需在本周三提交PPT给技术部负责人，周五进行评选。",
  "missing_elements": []
}}

USER_INPUT:
{user_text}

OUTPUT_SCHEMA:
{{
  "identified_persons": [
    {{
      "mention": "",
      "person_key": "",
      "confidence": 0.0,
      "description": ""
    }}
  ],
  "time_info": {{
    "raw_text": "",
    "date": ""
  }},
  "location_info": "",
  "scenario_summary": "",
  "missing_elements": []
}}
"""
        print("\n================ LLM A - 输入拆分 ================")
        print(f"输入文本: {user_text[:100]}...")

        result = OllamaClient.call_model(MODEL_LLM_A, prompt)
        
        # 添加原始用户输入到结果中，供后续模块使用
        result["user_text"] = user_text
        
        # 为每个人物记录原始人名
        for person in result.get("identified_persons", []):
            person["original_name"] = person["mention"]
            
        self.current_context = result
        print("\n================ LLM A - 拆分结果 ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return result

    def get_current_context(self) -> Dict[str, Any]:
        """获取当前缓存的上下文"""
        return self.current_context or {}

    def clear_context(self):
        """清空当前上下文"""
        self.current_context = None


# 用于测试
if __name__ == "__main__":
    decomposer = LLM_A_InputDecomposer()
    
    test_input = "技术部负责人张三要求周三提交PPT，后端负责人李四对此有意见。"
    result = decomposer.decompose_input(test_input)
    print("拆分结果:", json.dumps(result, indent=2, ensure_ascii=False))