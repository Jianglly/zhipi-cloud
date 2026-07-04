# 测试套件 Bug 修复完成

## 问题

用户运行 `pytest` 报 `ModuleNotFoundError: No module named 'fixtures'`，整个测试套件无法运行。

## 根因分析

排查后发现 **6 个独立问题** 叠加在一起：

| # | 问题 | 根因 |
|---|------|------|
| 1 | `No module named 'fixtures'` | `pytest.ini` 缺 `pythonpath`，`tests/` 不在 Python 路径上 |
| 2 | `No module named 'fixtures.test_data'` | 测试数据全写在 `__init__.py` 里，但导入路径是 `fixtures.test_data`（找 `test_data.py` 文件） |
| 3 | OCR 模式B 纯字母序列失败 | `len(clean) <= 4` 限制过严，`"ABCDABCDAB"` (10字母) 被拒绝 |
| 4 | OCR 多选题解析失败 | 模式A 正则 `([A-D])` 只捕获单字母，`"A,B"` 被截断为 `"A"` |
| 5 | Windows 环境变量超长崩溃 | `backend_env` fixture 的 `os.environ.clear()` 在 Windows 触发 PATH > 32767 字符错误 |
| 6 | DB 集成测试全部 401 | 没有 MySQL 时集成测试无法登录，报 401 噪音 |

## 修复内容

### 1. 模块导入修复
- **`pytest.ini`** — 新增 `pythonpath = . tests`
- **`tests/conftest.py`** — 新增 `tests_dir` 到 `sys.path`
- **`tests/fixtures/test_data.py`** — 新建文件，从 `__init__.py` 拆出所有测试数据常量
- **`tests/fixtures/__init__.py`** — 改为 `from fixtures.test_data import *` 重新导出

### 2. OCR 解析 Bug 修复 (`services/ocr_service.py`)
- **多选题支持** — 模式A 正则 `([A-D])` → `([A-D](?:\s*[,，]\s*[A-D])*)` 支持 `"A,B"` / `"A,B,C,D"` 格式
- **纯字母序列** — 模式B 移除 `len(clean) <= 4` 限制，`"ABCDABCDAB"` 不再被拒绝

### 3. Windows 兼容性修复
- **`backend_env` fixture** — 不再 `os.environ.clear()`，改为精确记录和恢复改过的键

### 4. DB 集成测试自动跳过
- 新增 `db_available` fixture — 检测 MySQL 连通性
- `app` fixture 无 DB 时 `pytest.skip()` — 67 个集成测试干净跳过，不再报 401

## 最终测试结果

```
91 passed, 67 skipped, 0 failed, 0 errors in 0.89s
```

| 测试文件 | 通过 | 跳过 | 说明 |
|----------|------|------|------|
| test_ocr_service.py | 32 | 0 | OCR 解析 + 批改单元测试 |
| test_llm_service.py | 25 | 0 | LLM 批改服务单元测试 |
| test_question_search.py | 34 | 0 | 搜题服务单元测试 |
| test_auth.py | 0 | 25 | 需 MySQL（集成测试） |
| test_ocr_pipeline.py | 0 | 19 | 需 MySQL（集成测试） |
| test_performance.py | 0 | 23 | 需 MySQL（性能测试） |

## 运行方式

```bash
cd zhipi-cloud/zhipi-backend

# 安装依赖
pip install -r tests/test_requirements.txt

# 运行全部测试（无 DB 时自动跳过集成测试）
pytest tests/ -v

# 只运行单元测试
pytest tests/test_ocr_service.py tests/test_llm_service.py tests/test_question_search.py -v

# 有 MySQL 时运行集成测试
# 确保 MySQL 运行在 localhost:3307，数据库 zhipi_cloud 已导入种子数据
pytest tests/ -v
```
