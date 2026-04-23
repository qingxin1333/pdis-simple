"""
PDIS流程运行脚本
用于直接运行PDIS管道，解决相对导入问题
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from main import PDISPipeline

def main():
    """主函数"""
    print("🚀 启动PDIS决策分析流程...")
    
    # 创建管道实例
    pipeline = PDISPipeline()
    
    # 运行完整流程
    result = pipeline.run_full_pipeline()
    
    print("\n✅ 分析完成！")
    return result

if __name__ == "__main__":
    main()