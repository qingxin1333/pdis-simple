"""
PDIS主流程控制器
整合所有模块，协调完整的决策分析流程
"""

import json
from typing import Dict, Any, List
from process.report_manager import ReportManager
from process.llm_a_input_decomposer import LLM_A_InputDecomposer
from process.llm_b_condition_checker import LLM_B_ConditionChecker
from process.llm_c_profile_generator import LLM_C_ProfileGenerator
from process.llm_d_decision_analyzer import LLM_D_DecisionAnalyzer


class PDISPipeline:
    """
    PDIS核心流程控制器
    整合所有LLM模块，执行完整的个人决策分析流程
    """

    def __init__(self, storage_file: str = "full_reports.json"):
        """
        初始化PDIS流程管道
        :param storage_file: 报告存储文件路径
        """
        # 初始化核心组件
        self.report_manager = ReportManager(storage_file)
        self.llm_a = LLM_A_InputDecomposer()
        self.llm_b = LLM_B_ConditionChecker()
        self.llm_c = LLM_C_ProfileGenerator()
        self.llm_d = LLM_D_DecisionAnalyzer(self.report_manager)
        
        # 数据存储
        self.person_registry = {}  # 人物档案库
        self.current_context = None  # 当前分析上下文

    def run_full_pipeline(self, user_input: str = None) -> str:
        """
        执行完整的PDIS分析流程
        :param user_input: 用户输入文本（如果为None则使用默认测试输入）
        :return: 最终的决策分析报告
        """
        print("\n\n================= PDIS 测试流程开始 =================\n")

        # 1️⃣ 用户输入处理
        if user_input is None:
            user_input = self._get_default_user_input()
        
        print("📝 用户输入:")
        print(user_input[:200] + "..." if len(user_input) > 200 else user_input)

        # 2️⃣ LLM A: 输入拆分
        decomposed = self.llm_a.decompose_input(user_input)
        self.current_context = decomposed

        # 3️⃣ 检查并生成缺失人物档案
        self._generate_missing_profiles(decomposed)

        # 4️⃣ LLM B: 条件检查
        readiness = self.llm_b.check_conditions(decomposed, self.person_registry)

        # 5️⃣ 信息补充处理
        if not readiness.get("ready", False):
            print("\n================ 需要补充信息 ================")
            final_result = self._handle_information_supplement(user_input, decomposed, readiness)
        else:
            # 6️⃣ 直接执行决策分析
            print("\n================ 执行最终决策分析 ================")
            final_result = self._execute_decision_analysis(decomposed)

        # 7️⃣ 输出最终结果
        self._print_final_results(final_result)
        return final_result

    def _get_default_user_input(self) -> str:
        """获取默认测试输入"""
        return """
下面想让你分析一个事情，我们要在本周五做年终总结的PPT的演讲。我现在PPT已经写好了。 本周三下午是技术分享会，要求大家把PPT交给技术部的负责人，说是周三一起讨论一下。但是周五讲PPT要评选的，我感觉我写的还可以，可以再加强，但是我实在是没有时间了。 我们公司是一家小型的科技公司，以做物联网园区设备接入和设备管理运维软件为主要业务。做节能算法，节能大屏展示，还有3D可视化建模的团队。 我要是周三，也就是明天，把PPT给团队负责人看，他要是把我的PPT给其它人看怎么办？上次我有个运维文档，他感觉很好，把后端负责人找来一起看，让我给他讲，结果后端负责人不是很高兴，他说现在已经有运维文档了，就照那个就可以了，我感觉也很尴尬。我明天是要交PPT给他，还是说还没写好再优化一下，然后周三完上，或者周四再给他呢？ 开发部的总负责人是一名前端工程师，兼开发部负责人，负责一些工作业务上的管理，人事的管理由老板娘自己在管理。 我们的后端负责人是个公司员老，感觉对我的态度不热情，也没有故意针对，我感觉他就是一方面时间上没有太多时间，自己的眼界也有限，不想搞一些事情。 我们老板呢，是一个很喜欢演讲的人，到处跟人聊项目，有很多的企业的老板跟他说AI怎么好，做AGENT矩阵什么的，他就跑来跟我们讲，但是他只说让我们做，谁谁谁负责，2周做一个xxx的agnent出来，也没有规划，也不说投入，投入多少钱，多少人。我感觉他就是被人洗了脑，然后跑来给我们洗脑的。这人喜欢读中国的国学，孔子，孟子，老子的书，还天天让我们读，读了还要发到微信群里 老板娘是个人精，想把研发部从公司独立出去一个公司，独立结算，到我态度有点冷淡，对外看着大大咧咧，客客气气，感觉都是表面现像，她不坐在自己办公室跑到员工区，坐在大家中间，正好在我旁边，开始还老问我一些问题，但是我要是说了，她没说话，又去问别人，说的跟我差不多，事情就交给别人了。后来就不怎么问我了，有时候问事情也不直接点我名，就说这个是谁负责，谁来说一下吧。 你能从心理学和人物侧写的角度帮我分析一下吗？这些人的性格，和对我的态度，还有我在这家公司的生存策略。 
"""

    def _generate_missing_profiles(self, decomposed: Dict[str, Any]):
        """生成缺失的人物档案"""
        for person in decomposed.get("identified_persons", []):
            person_key = person["person_key"]
            # 仅当人物档案不存在时生成
            if person_key not in self.person_registry:
                print(f"\n⚠️ 人物档案缺失: {person_key}")
                # 设置上下文
                self.llm_c.set_context(decomposed)
                # 生成人物档案
                profile = self.llm_c.generate_profile(
                    person_key=person_key,
                    description=person["description"]
                )
                self.person_registry[person_key] = profile

    def _handle_information_supplement(self, user_input: str, decomposed: Dict[str, Any], 
                                     readiness: Dict[str, Any]) -> str:
        """处理信息补充流程"""
        # 生成补充提示
        supplement_prompts = self.llm_b.generate_supplement_prompt(
            readiness.get("missing_fields", [])
        )
        
        print("需要补充的信息:")
        for prompt in supplement_prompts:
            print(f"- {prompt}")

        # 模拟用户补充（实际应用中应该交互式获取）
        supplement_text = self._simulate_user_supplement(readiness.get("missing_fields", []))
        print(f"\n用户补充：{supplement_text}")
        
        # 重新拆分输入
        updated_input = user_input + "\n补充: " + supplement_text
        decomposed = self.llm_a.decompose_input(updated_input)
        self.current_context = decomposed

        # 重新生成缺失档案
        self._generate_missing_profiles(decomposed)

        # 执行决策分析
        return self._execute_decision_analysis(decomposed)

    def _simulate_user_supplement(self, missing_fields: List[str]) -> str:
        """模拟用户补充信息（测试用）"""
        supplements = []
        for field in missing_fields:
            if field == "time_info.date":
                supplements.append("本周三下午是2026年2月15日，本周五是2026年2月17日")
            elif field == "location_info":
                supplements.append("地点：公司三楼会议室")
            elif field.startswith("person_profile:") or field.startswith("personality_color:"):
                person_key = field.split(":")[1]
                supplements.append(
                    f"{person_key}的详细描述: 该角色是公司技术部门负责人，"
                    f"对节能算法项目感兴趣，喜欢主动推动技术讨论，关注细节，善于沟通"
                )
        
        return " | ".join(supplements)

    def _execute_decision_analysis(self, decomposed: Dict[str, Any]) -> str:
        """执行决策分析"""
        return self.llm_d.analyze_decision(
            scenario_summary=decomposed.get("scenario_summary", ""),
            identified_persons=decomposed.get("identified_persons", []),
            person_registry=self.person_registry
        )

    def _print_final_results(self, final_result: str):
        """打印最终结果"""
        print("\n================ 最终决策分析 ================")
        print(final_result)
        
        # 打印报告管理信息
        print("\n" + "=" * 50)
        print("报告已保存到:", self.report_manager.storage_file)
        print("报告摘要:", self.report_manager.get_context("decision_analysis"))
        print("=" * 50)

    def get_person_registry(self) -> Dict[str, Any]:
        """获取当前人物档案库"""
        return self.person_registry.copy()

    def get_current_context(self) -> Dict[str, Any]:
        """获取当前分析上下文"""
        return self.current_context or {}

    def reset_pipeline(self):
        """重置管道状态"""
        self.person_registry.clear()
        self.current_context = None
        self.llm_a.clear_context()
        self.llm_c.clear_context()


# 用于测试
if __name__ == "__main__":
    pipeline = PDISPipeline()
    result = pipeline.run_full_pipeline()
    print("\n✅ 流程执行完成")