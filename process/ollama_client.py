"""
LLM客户端模块
封装Ollama API调用，提供统一的LLM接口
"""

import requests
import json
from typing import Dict, Any, List, Optional
from .config import OLLAMA_ENDPOINT, REQUEST_TIMEOUT, MODEL_EMBEDDING


class OllamaClient:
    """
    通用LLM调用器，封装Ollama API调用
    """

    @staticmethod
    def call_model(model_name: str, prompt_text: str) -> Dict[str, Any]:
        """
        调用指定模型执行推理任务
        :param model_name: 模型名称
        :param prompt_text: 提示词文本
        :return: 解析后的JSON响应
        """
        try:
            response = requests.post(
                OLLAMA_ENDPOINT,
                json={
                    "model": model_name,
                    "prompt": prompt_text,
                    "stream": False
                },
                timeout=REQUEST_TIMEOUT
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

        except requests.exceptions.RequestException as e:
            print(f"❌ LLM调用失败: {str(e)}")
            return {}
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return {}

    @staticmethod
    def embed(text: str, model_name: str = MODEL_EMBEDDING) -> Optional[List[float]]:
        base = OLLAMA_ENDPOINT
        if "/api/" in base:
            base = base.split("/api/")[0]

        for url in (f"{base}/api/embeddings", f"{base}/api/embed"):
            try:
                response = requests.post(
                    url,
                    json={"model": model_name, "prompt": text},
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code >= 400:
                    continue
                payload = response.json()
                vec = payload.get("embedding")
                if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
                    return [float(x) for x in vec]
            except Exception:
                continue

        return None


# 用于测试
if __name__ == "__main__":
    # 测试基本功能
    result = OllamaClient.call_model(
        "qwen2.5:7b-instruct",
        "Hello, please return {'test': 'success'}"
    )
    print("测试结果:", result)
