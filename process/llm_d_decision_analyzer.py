"""
LLM D模块：决策分析器
基于人物档案和场景进行重大决策可行性分析
"""

import json
from typing import Dict, Any, List
from .ollama_client import OllamaClient
from .config import MODEL_LLM_D
from .report_manager import ReportManager


class LLM_D_DecisionAnalyzer:
    """
    LLM D: 重大决策分析引擎
    核心功能：基于人物档案和场景进行可行性分析，生成决策建议
    """

    def __init__(self, report_manager: ReportManager):
        """
        初始化决策分析器
        :param report_manager: 报告管理器实例
        """
        self.report_manager = report_manager

    def analyze_decision(self, 
                        scenario_summary: str, 
                        identified_persons: List[Dict[str, Any]], 
                        person_registry: Dict[str, Any]) -> str:
        """
        执行重大决策可行性分析
        :param scenario_summary: 场景摘要
        :param identified_persons: 识别出的人物列表
        :param person_registry: 人物档案注册表
        :return: 客户友好的决策分析报告
        """
        # 获取历史报告摘要 (用于上下文)
        history_context = self.report_manager.get_context("decision_analysis")

        # 构建人名映射（将person_key -> 原始人名）
        name_mapping = {}
        for person in identified_persons:
            name_mapping[person["person_key"]] = person["original_name"]
        mapping_str = ", ".join([f"{k}: {v}" for k, v in name_mapping.items()])

        # 收集所有目标人物档案
        target_profiles = []
        for person in identified_persons:
            person_key = person["person_key"]
            if person_key in person_registry:
                target_profiles.append(person_registry[person_key])

        input_json = {
            "scenario": scenario_summary,
            "self_profile": person_registry.get("self", {}),
            "target_profiles": target_profiles
        }

        # 构建提示词
        prompt = f"""
You are a strategic decision analysis engine.
Analyze the scenario using ONLY the provided profiles, including personality_original, strengths, and weaknesses.
Focus on how these factors affect interactions and decision-making.

HISTORICAL CONTEXT (from previous analyses):
{history_context}

# PERSON_NAME_MAPPING (请用此映射替换所有person_key):
{mapping_str}

INSTRUCTIONS:
1. If personality_color, strengths, or weaknesses are missing for a person, skip personality-based analysis for that person.
2. For each person with personality_original, reference their personality_original when explaining reactions.
3. Use strengths and weaknesses to provide nuanced advice.
4. Provide actionable advice based on personality dynamics.
5. If critical information is missing, state it clearly in the analysis.
6. All output languages must be consistent with the input language
7. Character titles must use the original input name (e.g. if the user inputs "技术部负责人", use "技术部负责人")
8. NEVER USE person_key (e.g. Technical_Manager) IN THE OUTPUT

INPUT_CONTEXT:
{json.dumps(input_json, ensure_ascii=False)}

OUTPUT_SCHEMA:
{{
  "feasibility": "",
  "confidence": 0.0,
  "key_reasons": [],
  "execution_plan": [],
  "risks": [],
  "missing_info": []
}}
"""
        print("\n================ LLM D - 决策分析 ================")
        print("场景摘要:", scenario_summary)
        print("涉及人物:", [p["original_name"] for p in identified_persons])

        result = OllamaClient.call_model(MODEL_LLM_D, prompt)
        print("\n================ LLM D - 分析结果 ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 二次替换 - 用原始人名替换所有person_key
        for key, original_name in name_mapping.items():
            # 替换所有字段中的person_key
            for field in ['key_reasons', 'execution_plan', 'risks', 'missing_info']:
                if field in result and isinstance(result[field], list):
                    result[field] = [
                        s.replace(key, original_name)
                        for s in result[field]
                    ]

        # 保存结构化JSON（系统内部）
        system_report = json.dumps(result, ensure_ascii=False)
        self.report_manager.save_report("decision_analysis", system_report)

        # 生成客户报告
        client_report = (
            f"决策可行性分析报告：\n"
            f"可行性：{result.get('feasibility', '未提供')}\n"
            f"信心度：{result.get('confidence', '未提供')}\n"
            f"关键原因：{', '.join(result.get('key_reasons', []))}\n"
            f"执行计划：{', '.join(result.get('execution_plan', []))}\n"
            f"风险：{', '.join(result.get('risks', []))}\n"
            f"缺失信息：{', '.join(result.get('missing_info', []))}"
        )

        return client_report


# 用于测试
if __name__ == "__main__":
    # 创建测试实例
    manager = ReportManager()
    analyzer = LLM_D_DecisionAnalyzer(manager)
    
    # 测试数据
    test_scenario = "需要在周三提交PPT给技术部负责人"
    test_persons = [
        {
            "person_key": "Technical_Manager",
            "original_name": "技术部负责人"
        }
    ]
    test_registry = {
        "Technical_Manager": {
            "personality_report": {
                "personality_color": "leadership",
                "personality_original": "领导型",
                "strengths": ["主动性强", "结果导向"],
                "weaknesses": ["可能忽视团队协作"]
            }
        }
    }
    
    result = analyzer.analyze_decision(test_scenario, test_persons, test_registry)
    print("分析结果:", result)