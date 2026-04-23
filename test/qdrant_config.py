# Qdrant 配置文件
# 用于管理 Qdrant 向量数据库的连接配置

# 服务器配置
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_PROTOCOL = "http"

# 默认设置
DEFAULT_VECTOR_SIZE = 4
DEFAULT_COLLECTION = "app_av_charts"

# 构建的URL（在代码中使用）
QDRANT_BASE_URL = f"{QDRANT_PROTOCOL}://{QDRANT_HOST}:{QDRANT_PORT}"
COLLECTIONS_URL = f"{QDRANT_BASE_URL}/collections"

# 可选：其他配置
QDRANT_TIMEOUT = 30  # 请求超时时间（秒）
MAX_RETRIES = 3      # 最大重试次数