"""
LLM B模块：条件检查器
负责判断当前信息是否满足分析条件
"""

import json
from typing import Dict, Any, List
from .ollama_client import OllamaClient
from .config import MODEL_LLM_B


class LLM_B_ConditionChecker:
    """
    LLM B: 条件检查引擎
    核心功能：验证输入信息完整性，确定是否可以进行分析
    """

    def __init__(self):
        pass

    def check_conditions(self, decomposed_data: Dict[str, Any], person_registry: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM B判断当前信息是否满足分析条件
        :param decomposed_data: LLM A拆分的结果
        :param person_registry: 人物档案注册表
        :return: 条件检查结果
        """
        # 准备输入，让LLM B分析条件
        context_data = {
            "time_info": decomposed_data.get("time_info", {}),
            "location_info": decomposed_data.get("location_info", ""),
            "scenario_summary": decomposed_data.get("scenario_summary", ""),
            "identified_persons": decomposed_data.get("identified_persons", []),
            "person_registry": person_registry
        }

        prompt = f"""
You are a structured input validation engine.
Analyze the provided context to determine if all required information is present for analysis.
Check for these required elements:
1. Time information (date) must be provided
2. Location information must be provided
3. Scenario summary must be provided
4. For each person mentioned, their personality_color must be present in the profile

INPUT CONTEXT:
{json.dumps(context_data, ensure_ascii=False)}

OUTPUT_SCHEMA:
{{
  "ready": true/false,
  "missing_fields": ["field1", "field2", ...],
  "followup_questions": ["Question1", "Question2", ...]
}}

INSTRUCTIONS:
1. Return ONLY the JSON object, no additional text, no Markdown formatting, no explanations.
2. "ready" should be true if all required information is present, false otherwise.
3. "missing_fields" should list all missing fields.
4. "followup_questions" should provide questions to ask the user to fill in missing information.
5. Only include fields that are actually missing.
"""
        print("\n================ LLM B - 条件检查 ================")
        print("检查上下文:", json.dumps(context_data, indent=2, ensure_ascii=False)[:200] + "...")

        result = OllamaClient.call_model(MODEL_LLM_B, prompt)
        print("\n================ LLM B - 检查结果 ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        return result

    def generate_supplement_prompt(self, missing_fields: List[str]) -> List[str]:
        """
        根据缺失字段生成补充提示
        :param missing_fields: 缺失的字段列表
        :return: 补充内容列表
        """
        supplement = []
        for field in missing_fields:
            if field == "time_info.date":
                supplement.append("请提供具体的时间信息，如日期、截止时间等")
            elif field == "location_info":
                supplement.append("请提供相关的地点信息")
            elif field.startswith("person_profile:"):
                person_key = field.split(":")[1]
                supplement.append(f"请提供更多关于{person_key}的信息，包括性格特点、沟通方式等")
            elif field.startswith("personality_color:"):
                person_key = field.split(":")[1]
                supplement.append(f"请描述{person_key}的性格特征和行为模式")
        
        return supplement


# 用于测试
if __name__ == "__main__":
    checker = LLM_B_ConditionChecker()
    
    # 模拟拆分数据
    test_data = {
        "time_info": {"raw_text": "本周三"},
        "location_info": "",
        "scenario_summary": "需要提交PPT",
        "identified_persons": [{"person_key": "Technical_Manager"}]
    }
    
    # 模拟人物档案
    person_registry = {"Technical_Manager": {"personality_color": "leadership"}}
    
    result = checker.check_conditions(test_data, person_registry)
    print("检查结果:", json.dumps(result, indent=2, ensure_ascii=False))