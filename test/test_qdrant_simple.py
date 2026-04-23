import requests
import json
from qdrant_config import *

# ==================== Qdrant 集合管理工具 ====================
# 提供统一的接口来管理 Qdrant 向量数据库集合

# 使用从配置文件导入的设置


def create_collection(connection_name: str, vector_size: int = DEFAULT_VECTOR_SIZE) -> bool:
    """
    创建或验证 Qdrant 集合的存在

    如果集合不存在则创建，如果存在则验证维度是否匹配

    Args:
        connection_name (str): 集合名称
        vector_size (int): 向量维度，默认为4

    Returns:
        bool: 操作成功返回True
    """
    try:
        # 检查集合是否存在
        response = requests.get(f"{COLLECTIONS_URL}/{connection_name}")

        if response.status_code == 200:
            # 集合已存在，验证维度
            config = response.json().get('result', {}).get('config', {})
            actual_size = config.get('params', {}).get('vectors', {}).get('size')
            if actual_size == vector_size:
                print(f"✅ 集合 '{connection_name}' 已存在且维度正确 ({vector_size})")
                return True
            else:
                print(f"⚠️  集合 '{connection_name}' 维度不匹配! 期望: {vector_size}, 实际: {actual_size}")
                return False

        elif response.status_code == 404:
            # 集合不存在，创建新集合
            print(f"正在创建集合 '{connection_name}' (维度: {vector_size})...")
            create_resp = requests.put(
                f"{COLLECTIONS_URL}/{connection_name}",
                json={
                    "vectors": {
                        "size": vector_size,
                        "distance": "Cosine"
                    }
                }
            )

            if create_resp.status_code == 200:
                print(f"✅ 集合 '{connection_name}' 创建成功")
                return True
            else:
                print(f"❌ 创建集合失败: {create_resp.status_code}")
                return False
        else:
            print(f"❌ 检查集合状态异常: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 操作异常: {str(e)}")
        return False


def list_all_collections() -> list:
    """
    获取所有现有集合的名称列表

    Returns:
        list: 集合名称列表
    """
    try:
        response = requests.get(COLLECTIONS_URL)
        if response.status_code == 200:
            collections = response.json().get('result', {}).get('collections', [])
            return [coll['name'] for coll in collections]
        else:
            print(f"❌ 获取集合列表失败: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 获取集合列表异常: {str(e)}")
        return []


def delete_collection(name: str) -> bool:
    """
    删除指定的集合

    Args:
        name (str): 要删除的集合名称

    Returns:
        bool: 删除成功返回True
    """
    try:
        response = requests.delete(f"{COLLECTIONS_URL}/{name}")
        if response.status_code == 200:
            print(f"✅ 集合 '{name}' 删除成功")
            return True
        else:
            print(f"❌ 删除集合 '{name}' 失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 删除操作异常: {str(e)}")
        return False


def main_workflow():
    """
    主要工作流程示例：创建集合、添加数据、执行搜索和列出集合
    """
    print("🚀 Qdrant 集合管理工具启动")
    print("=" * 50)

    # 1. 创建默认集合
    print("\n=== 创建集合 ===")
    if create_collection(DEFAULT_COLLECTION, DEFAULT_VECTOR_SIZE):
        # 2. 向集合添加数据点
        print(f"\n=== 向 {DEFAULT_COLLECTION} 添加数据点 ===")
        
        # 准备要发送的数据
        payload = {"points": [{"id": 4,"vector": [0.1, 0.2, 0.3, 0.0] }]}

        # 打印发送的JSON数据
        print(f"发送的数据: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        add_resp = requests.put(
            f"{COLLECTIONS_URL}/{DEFAULT_COLLECTION}/points",
            json=payload
        )
        print(f"返回状态: {add_resp.status_code}, {add_resp.text}")

        # 3. 搜索相似数据点
        print(f"\n=== 在 {DEFAULT_COLLECTION} 中搜索 ===")
        search_resp = requests.post(
            f"http://localhost:6333/collections/{DEFAULT_COLLECTION}/points/search",
            json={
                "vector": [0.1, 0.2, 0.3, 0.4],
                "limit": 5
            }
        )
        print(f"搜索结果状态: {search_resp.status_code},{search_resp.content}")
        if search_resp.status_code == 200:
            results = search_resp.json().get('result', [])
            print(f"找到 {len(results)} 个相似结果")

    # 4. 显示所有集合
    print("\n=== 当前所有集合 ===")
    collections = list_all_collections()
    for coll in collections:
        print(f"  • {coll}")

    print("\n✅ 工作流程完成")
    print("=" * 50)



# 程序入口
if __name__ == "__main__":
    # 执行主要工作流程
    main_workflow()

    print("\n✅ 程序执行完成")