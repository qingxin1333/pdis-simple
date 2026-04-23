import datetime
import requests
import json
from typing import Dict, Any, List

# ===================== 全局模型变量 =====================
# 定义PDIS系统中各个LLM模块使用的模型
MODEL_LLM_A = "qwen2.5:7b-instruct"  # 用于LLM A (输入拆分)
MODEL_LLM_B = "qwen2.5:7b-instruct"  # 用于LLM B (条件判断)
MODEL_LLM_C = "qwen2.5:7b-instruct"  # 用于LLM C (人物档案生成)
MODEL_LLM_D = "qwen3:8b"  # 用于LLM D (决策分析)


# ===================== 新增：报告管理器 =====================
class ReportManager:
    """
    报告管理器类，负责管理LLM生成的报告，实现上下文压缩和RAG策略。
    
    该类提供报告的存储、摘要生成和上下文检索功能，支持历史报告的管理和查询。
    """

    def __init__(self, storage_file: str = "full_reports.json"):
        """
        初始化报告管理器实例。
        
        参数:
            storage_file (str): 报告存储文件路径，默认为"full_reports.json"
        """
        self.storage_file = storage_file
        self.summaries: Dict[str, str] = {}  # 内存中存储摘要 (生产环境应替换为数据库)
        self.report_types: List[str] = []  # 保存报告类型列表
        self._load_existing_reports()

    def _load_existing_reports(self) -> None:
        """
        加载已存在的完整报告和摘要。
        
        从存储文件中读取历史报告数据，提取各类型报告的摘要信息。
        如果文件不存在或格式错误，则初始化为空的数据结构。
        """
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                self.reports = json.load(f)
                # 从历史报告中提取摘要
                for report in self.reports:
                    if report["type"] not in self.summaries:
                        self.summaries[report["type"]] = self._generate_summary(report["content"])
                        self.report_types.append(report["type"])
        except (FileNotFoundError, json.JSONDecodeError):
            self.reports = []
            self.summaries = {}
            self.report_types = []

    def save_report(self, report_type: str, content: str) -> str:
        """
        保存报告并生成摘要。
        
        实现WCI模式：Write(写入完整报告) -> Compress(压缩生成摘要) -> Isolate(隔离存储不同摘要)
        
        参数:
            report_type (str): 报告类型，如"decision_analysis"
            content (str): 报告内容(中文)
            
        返回:
            str: 生成的报告摘要
       """
        # 1. 写 (Write) - 保存完整报告
        timestamp = datetime.datetime.now().isoformat()
        new_report = {
            "timestamp": timestamp,
            "type": report_type,
            "content": content
        }
        self.reports.append(new_report)

        # 保存到文件
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.reports, f, indent=2, ensure_ascii=False)

        # 2. 压 (Compress) - 生成摘要
        summary = self._generate_summary(content)

        # 3. 隔 (Isolate) - 独立存储不同类型摘要
        if report_type not in self.summaries:
            self.summaries[report_type] = summary
            self.report_types.append(report_type)

        return summary

    def _generate_summary(self, content: str) -> str:
        """
        生成报告摘要(测试版：简化实现)。
        
        参数:
            content (str): 原始报告内容
            
        返回:
            str: 生成的摘要字符串
        """
        # 实际生产环境应调用LLM生成专业摘要
        if len(content) > 100:
            return f"摘要: {content[:97]}..."
        return f"摘要: {content}"

    def get_context(self, report_type: str) -> str:
        """
        获取相关摘要作为上下文(RAG选择)。
        
        实现RAG策略中的Select(选择)步骤，根据报告类型获取最相关的历史摘要。
        
        参数:
            report_type (str): 请求的报告类型
            
        返回:
            str: 相关摘要内容，如果不存在则返回空字符串
        """
        # 1. 选 (Select) - 选择最相关的摘要
        return self.summaries.get(report_type, "")


# =========================================================
# PDIS 核心流程测试类 (严格遵循业务文档，已集成ReportManager)
# =========================================================
class PDISPipelineTest:
    """
    PDIS核心流程测试类，实现四阶段工作流。
    
    严格按照业务文档要求，集成ReportManager实现完整的决策支持流程。
    包含LLM A(输入拆分)、LLM B(条件判断)、LLM C(人物档案生成)、LLM D(决策分析)四个核心模块。
    """
    
    def __init__(self):
        """
        初始化PDIS流程测试实例。
        
        初始化人物档案库、上下文缓存和报告管理器。
        """
        self.person_registry = {}  # 人物档案库 (key: person_key)
        self.current_context = None  # 当前分析上下文 (用于缓存LLM A拆分结果)
        # 新增：初始化报告管理器
        self.report_manager = ReportManager()

    # =====================================================
    # LLM A: 输入拆分 (核心: 识别关键要素)
    # =====================================================
    def run_llm_a(self, user_text: str) -> Dict[str, Any]:
        """
        执行LLM A模块：输入拆分，识别关键要素。
        
        核心功能是从用户输入中提取所有关键元素，包括人物、时间、地点等信息，
        并为每个人物生成唯一的person_key。
        
        参数:
            user_text (str): 用户原始输入文本
            
        返回:
            Dict[str, Any]: 包含拆分结果的字典，包含identified_persons、time_info等字段
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
        print("\n================ LLM A - 输入 ================")
        print(prompt)

        result = OllamaClient.call_model(MODEL_LLM_A, prompt)
        print("\n================ LLM A - 输出 ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # ✅ 新增：为每个人物记录原始人名（用户输入中的名字）
        for person in result["identified_persons"]:
            person["original_name"] = person["mention"]  # 保存原始人名

        # 保存原始用户输入到上下文，供LLM C使用
        result["user_text"] = user_text
        self.current_context = result
        return result

    # =====================================================
    # LLM C: 人物档案生成 (核心: 从完整上下文生成报告)
    # =====================================================
    def generate_person_profile(self, person_key: str, description: str) -> Dict[str, Any]:
        """
        执行LLM C模块：根据人物描述生成性格报告。
        
        使用九型人格理论分析人物性格，生成包含核心特质、沟通风格、优缺点等的完整档案。
        触发条件是人物档案不存在时。
        
        参数:
            person_key (str): 人物唯一标识符
            description (str): 人物描述信息
            
        返回:
            Dict[str, Any]: 包含完整人物档案的字典
        """
        full_context = self.current_context.get("user_text", "")

        # ===================== 九型人格系统说明 =====================
        enneagram_system = """
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

        prompt = f"""
You are a professional personality profiling engine.
Analyze the ENTIRE USER INPUT to determine personality type using the Enneagram system (nine personality types).

{enneagram_system}

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

    # =====================================================
    # LLM B: 分析条件判断 (核心: 检查信息完整性)
    # =====================================================
    def run_llm_b(self) -> Dict[str, Any]:
        """
        执行LLM B模块：分析条件判断。
        
        判断当前信息是否满足分析条件，检查必需元素是否完整，
        包括时间信息、地点信息、场景摘要和人物性格信息。
        
        返回:
            Dict[str, Any]: 包含条件检查结果的字典，包含ready、missing_fields等字段
        """
        if not self.current_context:
            raise ValueError("No decomposed context available. Run LLM A first.")

        # 准备输入，让LLM B分析条件
        context_data = {
            "time_info": self.current_context.get("time_info", {}),
            "location_info": self.current_context.get("location_info", ""),
            "scenario_summary": self.current_context.get("scenario_summary", ""),
            "identified_persons": self.current_context.get("identified_persons", []),
            "person_registry": self.person_registry
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
        print("\n================ LLM B - 输入 ================")
        print(prompt)

        result = OllamaClient.call_model(MODEL_LLM_B, prompt)
        print("\n================ LLM B - 输出 ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        return result

    # =====================================================
    # LLM D: 重大决策分析 (核心: 基于档案生成建议) - 已修改
    # =====================================================
    def run_llm_d(self) -> str:
        """
        执行LLM D模块：重大决策可行性分析(已集成报告管理器)。
        
        基于人物档案和场景进行可行性分析，生成决策建议。
        已集成历史报告管理功能，支持RAG策略。
        
        返回:
            str: 客户友好的决策分析报告
        """
        if not self.current_context:
            raise ValueError("No decomposed context available. Run LLM A first.")

        # 获取历史报告摘要 (用于上下文)
        history_context = self.report_manager.get_context("decision_analysis")

        # ✅ 构建人名映射（将person_key -> 原始人名）
        name_mapping = {}
        for person in self.current_context["identified_persons"]:
            name_mapping[person["person_key"]] = person["original_name"]
        mapping_str = ", ".join([f"{k}: {v}" for k, v in name_mapping.items()])

        # 收集所有目标人物档案
        target_profiles = []
        for person in self.current_context["identified_persons"]:
            person_key = person["person_key"]
            if person_key in self.person_registry:
                target_profiles.append(self.person_registry[person_key])

        input_json = {
            "scenario": self.current_context["scenario_summary"],
            "self_profile": self.person_registry.get("self", {}),
            "target_profiles": target_profiles
        }

        # 新增：将历史摘要加入LLM D的上下文
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
        print("\n================ LLM D - 输入 ================")
        print(prompt)

        result = OllamaClient.call_model(MODEL_LLM_D, prompt)
        print("\n================ LLM D - 输出 ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # ✅ 关键修改：二次替换 - 用原始人名替换所有person_key
        for key, original_name in name_mapping.items():
            # 替换所有字段中的person_key
            for field in ['key_reasons', 'execution_plan', 'risks', 'missing_info']:
                if field in result and isinstance(result[field], list):
                    result[field] = [
                        s.replace(key, original_name)
                        for s in result[field]
                    ]

        # 1. 保存结构化JSON（系统内部）
        system_report = json.dumps(result, ensure_ascii=False)
        self.report_manager.save_report("decision_analysis", system_report)

        # 2. 生成客户报告（用替换后的result）
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


    # =====================================================
    # 主流程执行 (严格按业务文档顺序)
    # =====================================================
    def run_full_pipeline(self):
        """
        执行完整的PDIS测试流程。
        
        严格按照业务文档顺序执行四阶段工作流：
        1. 用户输入处理
        2. LLM A输入拆分
        3. 人物档案生成
        4. LLM B条件检查
        5. 信息补充(如需要)
        6. LLM D决策分析
        """
        print("\n\n================= PDIS 测试流程开始 =================\n")

        # 1️⃣ 用户输入 (模拟真实场景)
        user_text = """
下面想让你分析一个事情，我们要在本周五做年终总结的PPT的演讲。我现在PPT已经写好了。 本周三下午是技术分享会，要求大家把PPT交给技术部的负责人，说是周三一起讨论一下。但是周五讲PPT要评选的，我感觉我写的还可以，可以再加强，但是我实在是没有时间了。 我们公司是一家小型的科技公司，以做物联网园区设备接入和设备管理运维软件为主要业务。做节能算法，节能大屏展示，还有3D可视化建模的团队。 我要是周三，也就是明天，把PPT给团队负责人看，他要是把我的PPT给其它人看怎么办？上次我有个运维文档，他感觉很好，把后端负责人找来一起看，让我给他讲，结果后端负责人不是很高兴，他说现在已经有运维文档了，就照那个就可以了，我感觉也很尴尬。我明天是要交PPT给他，还是说还没写好再优化一下，然后周三完上，或者周四再给他呢？ 开发部的总负责人是一名前端工程师，兼开发部负责人，负责一些工作业务上的管理，人事的管理由老板娘自己在管理。 我们的后端负责人是个公司员老，感觉对我的态度不热情，也没有故意针对，我感觉他就是一方面时间上没有太多时间，自己的眼界也有限，不想搞一些事情。 我们老板呢，是一个很喜欢演讲的人，到处跟人聊项目，有很多的企业的老板跟他说AI怎么好，做AGENT矩阵什么的，他就跑来跟我们讲，但是他只说让我们做，谁谁谁负责，2周做一个xxx的agnent出来，也没有规划，也不说投入，投入多少钱，多少人。我感觉他就是被人洗了脑，然后跑来给我们洗脑的。这人喜欢读中国的国学，孔子，孟子，老子的书，还天天让我们读，读了还要发到微信群里 老板娘是个人精，想把研发部从公司独立出去一个公司，独立结算，到我态度有点冷淡，对外看着大大咧咧，客客气气，感觉都是表面现像，她不坐在自己办公室跑到员工区，坐在大家中间，正好在我旁边，开始还老问我一些问题，但是我要是说了，她没说话，又去问别人，说的跟我差不多，事情就交给别人了。后来就不怎么问我了，有时候问事情也不直接点我名，就说这个是谁负责，谁来说一下吧。 你能从心理学和人物侧写的角度帮我分析一下吗？这些人的性格，和对我的态度，还有我在这家公司的生存策略。 
"""

        # 2️⃣ LLM A: 拆分输入
        decomposed = self.run_llm_a(user_text)

        # 3️⃣ 检查并生成缺失人物档案
        for person in decomposed["identified_persons"]:
            person_key = person["person_key"]
            # 仅当人物档案不存在时生成
            if person_key not in self.person_registry:
                print(f"\n⚠️ 人物档案缺失: {person_key}")
                # 生成人物档案 (LLM C)
                profile = self.generate_person_profile(
                    person_key=person_key,
                    description=person["description"]
                )
                self.person_registry[person_key] = profile

        # 4️⃣ LLM B: 检查条件
        readiness = self.run_llm_b()

        # 5️⃣ 信息不足时请求补充 (模拟用户补充)
        if not readiness["ready"]:
            print("\n================ 模拟用户补充信息 ================")
            # 补充所有缺失字段
            supplement = []
            for field in readiness["missing_fields"]:
                if field == "time_info.date":
                    supplement.append("本周三下午是2026年2月15日，本周五是2026年2月17日")
                elif field == "location_info":
                    supplement.append("地点：公司三楼会议室")
                elif field.startswith("person_profile:"):
                    person_key = field.split(":")[1]
                    # 补充描述，让AI分析性格、优点和缺点
                    supplement.append(
                        f"{person_key}的详细描述: 该角色是公司技术部门负责人，对节能算法项目感兴趣，喜欢主动推动技术讨论，关注细节，善于沟通")
                elif field.startswith("personality_color:"):
                    # 补充描述，让AI分析性格
                    person_key = field.split(":")[1]
                    supplement.append(
                        f"{person_key}的详细描述: 该角色是公司技术部门负责人，对节能算法项目感兴趣，喜欢主动推动技术讨论，关注细节，善于沟通")

            # 添加补充内容
            temp_text = "\n补充: " + " | ".join(supplement)
            print(f"\n用户补充：{temp_text}")
            user_text += temp_text

            # 重新拆分
            decomposed = self.run_llm_a(user_text)

            # 重新生成缺失档案
            for person in decomposed["identified_persons"]:
                person_key = person["person_key"]
                if person_key not in self.person_registry:
                    print(f"\n⚠️ 人物档案缺失: {person_key}")
                    profile = self.generate_person_profile(
                        person_key=person_key,
                        description=person["description"]
                    )
                    self.person_registry[person_key] = profile

            # 重新检查条件（但不再用于终止流程）
            readiness = self.run_llm_b()

        # 6️⃣ LLM D: 执行分析 (关键修改：已集成历史报告)
        print("\n================ 执行最终决策分析 ================")
        final_result = self.run_llm_d()
        print("\n================ 最终决策分析 ================")
        print(json.dumps(final_result, indent=2, ensure_ascii=False))

        # 新增：打印保存的完整报告
        print("\n" + "=" * 50)
        print("报告已保存到:", self.report_manager.storage_file)
        print("报告摘要:", self.report_manager.get_context("decision_analysis"))
        print("=" * 50)


# =========================================================
# 通用 LLM 调用器 (保持不变)
# =========================================================
class OllamaClient:
    """
    通用LLM调用器，封装Ollama API调用。
    
    提供统一的接口调用不同LLM模型，处理API响应和JSON解析。
    """
    
    @staticmethod
    def call_model(model_name: str, prompt_text: str) -> Dict[str, Any]:
        """
        调用指定模型执行推理任务。
        
        参数:
            model_name (str): 要调用的模型名称
            prompt_text (str): 提示词文本
            
        返回:
            Dict[str, Any]: 解析后的JSON响应结果
        """
        response = requests.post(
            "http://192.168.1.8:11434/api/generate",
            json={
                "model": model_name,
                "prompt": prompt_text,
                "stream": False
            },
            timeout=600
        )

        raw_text = response.json().get("response", "")

        # 尝试解析JSON，如果失败则提取第一个JSON对象
        try:
            # 如果返回的文本包含JSON，尝试提取
            if raw_text.startswith('{') and raw_text.endswith('}'):
                return json.loads(raw_text)
            else:
                # 尝试找到第一个{开始和最后一个}结束
                start = raw_text.find('{')
                end = raw_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = raw_text[start:end]
                    return json.loads(json_str)
                else:
                    # 如果找不到JSON，返回空字典（避免崩溃）
                    print(f"⚠️ 未找到有效JSON，返回空字典: {raw_text[:100]}...")
                    return {}
        except Exception as e:
            print(f"\n⚠️ JSON解析失败，原始输出如下：\n{raw_text}")
            print(f"错误详情: {str(e)}")
            return {}


# =========================================================
# 主入口
# =========================================================
if __name__ == "__main__":
    pipeline = PDISPipelineTest()
    pipeline.run_full_pipeline()