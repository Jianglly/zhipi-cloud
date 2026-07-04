"""
fixtures 包 — 测试数据常量与辅助函数
智批云后端 - tests/fixtures/

支持两种导入方式:
    from fixtures.test_data import ANSWER_KEY_OBJECTIVE_ONLY  # 直接从模块导入
    from fixtures import ANSWER_KEY_OBJECTIVE_ONLY             # 从包导入（重新导出）
"""

from fixtures.test_data import *  # noqa: F401, F403
