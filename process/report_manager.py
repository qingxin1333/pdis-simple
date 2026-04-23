"""
报告管理器模块
实现LLM生成报告的存储、管理和上下文压缩功能
"""

import json
import datetime
from typing import Dict, List, Any


class ReportManager:
    """
    管理LLM生成的报告的类，实现上下文压缩和RAG策略
    """

    def __init__(self, storage_file: str = "full_reports.json"):
        """
        初始化报告管理器
        :param storage_file: 完整报告存储文件路径
        """
        self.storage_file = storage_file
        self.summaries: Dict[str, str] = {}  # 内存中存储摘要 (生产环境应替换为数据库)
        self.report_types: List[str] = []  # 保存报告类型列表
        self._load_existing_reports()

    def _load_existing_reports(self) -> None:
        """加载已有的完整报告和摘要"""
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
        保存报告并生成摘要
        :param report_type: 报告类型 (如 "decision_analysis")
        :param content: 报告内容 (中文)
        :return: 生成的摘要
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
        生成报告摘要 (测试版：简化实现)
        :param content: 原始报告内容
        :return: 摘要字符串
        """
        # 实际生产环境应调用LLM生成专业摘要
        if len(content) > 100:
            return f"摘要: {content[:97]}..."
        return f"摘要: {content}"

    def get_context(self, report_type: str) -> str:
        """
        获取相关摘要作为上下文 (RAG选择)
        :param report_type: 请求的报告类型
        :return: 相关摘要 (如果不存在则返回空)
        """
        # 1. 选 (Select) - 选择最相关的摘要
        return self.summaries.get(report_type, "")

    def get_all_contexts(self) -> Dict[str, str]:
        """
        获取所有报告类型的摘要 (用于调试)
        :return: 所有摘要的字典
        """
        return self.summaries.copy()


# 用于测试
if __name__ == "__main__":
    manager = ReportManager()

    # 保存测试报告
    test_content = (
        "系统性能测试报告：执行100个用例，成功率95%，平均响应时间230ms。"
        "执行方案：优化数据库索引和缓存机制。关键发现：查询优化提升40%性能。"
    )
    manager.save_report("performance", test_content)

    # 获取上下文
    context = manager.get_context("performance")
    print("获取的上下文：", context)