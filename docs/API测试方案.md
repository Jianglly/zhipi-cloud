# 智批云 API 测试方案

**测试焦点：LLM 识别手写体 + 填空选择题批改**

---

## 一、系统现状分析

### 1.1 API 拓扑总览

| 模块 | 端点数 | 核心职责 |
|------|--------|---------|
| 认证 (`/api/auth`) | 4 | 登录/注册/JWT令牌/班级列表 |
| 试卷 (`/api/papers`) | 10 | CRUD/成绩提交/恢复/待批阅/已完成 |
| **OCR (`/api/ocr`)** | **5** | **上传→识别→批改→结果查询→LLM混合批改** |
| 统计 (`/api/stats`) | 7 | 学生成绩/趋势/排名/教师概览/分布 |
| 管理 (`/api/admin`) | 18 | 用户管理/班级管理/试卷/日志 |
| 系统 | 4 | 健康检查/就绪/SPA托管 |
| **合计** | **48** | |

### 1.2 当前测试状态

> **测试覆盖率：0%** — 项目无任何自动化测试代码。

这是生产级应用的最大风险点。以下方案将从零构建完整的测试体系。

### 1.3 OCR 批阅核心链路

```
教师创建试卷 → 录入answer_key → 发布试卷
                                    ↓
上传学生答卷图片(POST /api/ocr/upload-image)     ← 入口
                                    ↓
OCR手写体识别(POST /api/ocr/recognize)           ← 百度OCR API
  ├── 手写体识别(/rest/2.0/ocr/v1/handwriting)
  └── 降级：通用识别(/rest/2.0/ocr/v1/general_basic)
                                    ↓
解析文本为结构化答案(parse_ocr_text_to_answers)
  ├── 模式A：结构化匹配 "1. A"
  ├── 模式B：纯字母序列 "A B C D"
  └── 模式C：位置排序兜底（OCR词坐标）
                                    ↓
批改评分
  ├── 纯客观题：auto-grade (正则比对)             ← 填空/选择批改
  └── 混合题型：llm-grade (正则+LLM)              ← 主观题用DeepSeek
                                    ↓
查看结果(GET /api/ocr/grade-result/{paper_id})
                                    ↓
教师审核(POST /api/papers/{id}/submit-score)
                                    ↓
学生查看(GET /api/stats/student/scores)
```

**要测试的核心链路是：OCR手写体识别 → 答案文本解析 → 填空选择批改**

---

## 二、测试分层策略

```
┌─────────────────────────────────────────┐
│  L4: E2E 端到端测试                       │
│  完整业务流程：创建→上传→识别→批改→审核    │
├─────────────────────────────────────────┤
│  L3: API 集成测试                         │
│  HTTP 端点 + 模拟外部依赖（百度OCR/LLM）   │
├─────────────────────────────────────────┤
│  L2: Service 单元测试                     │
│  parse_ocr_text_to_answers               │
│  auto_grade_answers / grade_mixed_answers │
│  split_ocr_by_questions / call_llm_grade  │
├─────────────────────────────────────────┤
│  L1: 纯函数单元测试                        │
│  工具函数 / 数据模型验证 / 正则匹配         │
└─────────────────────────────────────────┘
```

### 测试优先级矩阵

| 优先级 | 测试类型 | 覆盖目标 | 原因 |
|--------|---------|---------|------|
| **P0** | OCR 文本解析逻辑 | 100% 分支覆盖 | 批改正确性的核心 |
| **P0** | 答案比对评分逻辑 | 100% 分支覆盖 | 直接影响学生成绩 |
| **P0** | 认证/授权安全 | 所有端点 | 数据安全底线 |
| P1 | OCR API 集成链路 | 正常+异常流程 | 端到端可用性 |
| P1 | LLM 批改集成 | 正常+异常流程 | 主观题评分 |
| P1 | 输入验证/防注入 | 所有输入点 | 安全防护 |
| P2 | 性能 SLA | 核心端点 | 用户体验 |
| P2 | 并发/负载 | 关键场景 | 生产稳定性 |
| P3 | 管理端点 CRUD | 基本流程 | 完整性 |

---

## 三、OCR 手写体识别测试方案（核心）

### 3.1 parse_ocr_text_to_answers 测试矩阵

这是**整个批改系统正确性的基石**，三种模式的识别率直接影响评分。

| 测试场景 | 输入 | 预期输出 | 状态 |
|---------|------|---------|------|
| 标准格式 "1. A\n2. B" | 结构化文本 | q1=A, q2=B | ✅ 已覆盖 |
| 中文标点 "1、A\n2、B" | 中文分隔符 | q1=A, q2=B | ✅ 已覆盖 |
| 冒号格式 "1: A\n2: B" | 英文冒号 | q1=A, q2=B | ✅ 已覆盖 |
| 无空格 "1A\n2B" | 紧凑格式 | q1=A, q2=B | ✅ 已覆盖 |
| 括号格式 "(1) A\n(2) B" | 括号编号 | q1=A, q2=B | ✅ 已覆盖 |
| 纯字母序列 "A B C D" | 无题号 | q1..q4按序分配 | ✅ 已覆盖 |
| 带标点 "A. B. C. D." | 字母+标点 | q1..q4按序分配 | ✅ 已覆盖 |
| OCR词级坐标排序 | 位置数据 | 从上到下从左到右 | ✅ 已覆盖 |
| 同行多字母 "A B C" | 同行排序 | 从左到右 | ✅ 已覆盖 |
| 空OCR文本 | "" | 全部空答案 | ✅ 已覆盖 |
| 乱码OCR文本 | "%%#@$" | 全部空答案 | ✅ 已覆盖 |
| 识别率低（<50%） | 模式A降级 | 触发模式B/C兜底 | ✅ 已覆盖 |
| 多选题格式 "1. A,B" | 逗号分隔 | 多项匹配 | ✅ 已覆盖 |
| 大小写混合 | "a" vs "A" | 大小写不敏感 | ✅ 已覆盖 |
| 大量题目(50题) | 50题输入 | 全部成功解析 | ✅ 已覆盖 |
| 部分题目未识别 | 只识别3/10 | 未识别标记为空 | ✅ 已覆盖 |

### 3.2 auto_grade_answers 测试矩阵

| 测试场景 | OCR结果 vs 标准答案 | 预期得分 | 状态 |
|---------|-------------------|---------|------|
| 全部正确 | A B C D E vs A B C D E | 100% | ✅ 已覆盖 |
| 全部错误 | D C B A D vs A B C D A | 0% | ✅ 已覆盖 |
| 部分正确 | A B X X A vs A B C D A | 60% (3/5) | ✅ 已覆盖 |
| 多选精确匹配 | A,B vs A,B | 正确 | ✅ 已覆盖 |
| 多选顺序无关 | B,A vs A,B | 正确(set比较) | ✅ 已覆盖 |
| 多选部分错 | A vs A,B | 错误 | ✅ 已覆盖 |
| 学生未作答 | "" vs "A" | 错误 + "(未识别)" | ✅ 已覆盖 |
| 大小写 | "a" vs "A" | 正确 | ✅ 已覆盖 |
| 空格处理 | " A " vs "A" | 正确 | ✅ 已覆盖 |
| 非整数均分 | 150分/7题 | 正确均分 | ✅ 已覆盖 |
| 空标准答案 | {} | 0分 | ✅ 已覆盖 |

### 3.3 LLM 混合批改测试矩阵

| 测试场景 | 输入 | 预期 | 状态 |
|---------|------|------|------|
| 纯客观题 | answer_key 纯字符串 | 正则比对，跳过LLM | ✅ 已覆盖 |
| 纯主观题 | answer_key 全 dict | LLM 评分 | ✅ 已覆盖 |
| 混合题型 | 客观+主观混合 | 分别处理 | ✅ 已覆盖 |
| 主观题含关键词 | keywords 字段 | Prompt 包含关键词 | ✅ 已覆盖 |
| 学生未作答主观题 | 空答案 | "未识别到答案" | ✅ 已覆盖 |
| LLM返回格式异常 | 不带json标记 | `_extract_json` 兜底 | ✅ 已覆盖 |
| LLM API 失败 | 连接超时 | RuntimeError → 500 | ⚠️ 需真实环境 |
| DeepSeek欠费 | insufficient_quota | 用户友好错误 | ⚠️ 需真实环境 |
| JSON提取：markdown包裹 | ```json...``` | 正确提取 | ✅ 已覆盖 |
| JSON提取：裸数组 | [...] | 正确提取 | ✅ 已覆盖 |
| JSON提取：无JSON | 纯文本 | None | ✅ 已覆盖 |
| 分数越界防护 | score > max_score | min/max 限制 | ✅ 已覆盖 |

### 3.4 DeepSeek 搜题批改测试矩阵（方案C — 今日实施）

本方案利用 DeepSeek LLM 替代第三方题库 API：教师拍试卷原题 → OCR → DeepSeek 搜答案 → 自动填充 answer_key → 批改全班。

**API 端点**：
- `POST /api/ocr/search-answers` — 搜题并返回 answer_key（可选保存到试卷）
- `POST /api/ocr/search-grade` — 全链路：搜题+保存+批改全班

| 测试场景 | 输入 | 预期 | 状态 |
|---------|------|------|------|
| 语文试卷搜题 | 选择+阅读+作文 | 结构化 answer_key | ✅ 已覆盖 |
| 数学试卷搜题 | 选择+填空+解答 | 题目分类正确 | ✅ 已覆盖 |
| 英语试卷搜题 | 单选+完形+翻译 | 答案格式正确 | ✅ 已覆盖 |
| 纯客观题搜题 | 15道选择题 | q1..q15 字母答案 | ✅ 已覆盖 |
| 混合题型搜题 | 客观+填空+主观 | 不同类型 answer_key | ✅ 已覆盖 |
| 多选题识别 | 多选题干 | "A,D" 格式 | ✅ 已覆盖 |
| LLM未识别题目 | 模糊图片OCR | ValueError | ✅ 已覆盖 |
| LLM回复无JSON | 纯文本回复 | ValueError | ✅ 已覆盖 |
| LLM API未配置 | LLM_API_KEY=占位 | RuntimeError | ✅ 已覆盖 |
| LLM API连接失败 | 网络异常 | RuntimeError | ✅ 已覆盖 |
| OCR识别为空 | 白纸/模糊图 | RuntimeError | ✅ 已覆盖 |
| 已有部分答案增量补充 | 传 answer_key | 题目提示不重复 | ✅ 已覆盖 |
| 搜题限流 | >5次/分 | 429 Too Many | ⚠️ 需启动服务器 |
| 全链路批改（search-grade） | 搜题+批改全班 | 多学生成绩 | ⚠️ 需真实环境 |
| 搜题保存到试卷 | 传 paper_id | answer_key 已存储 | ⚠️ 需真实环境 |
| Prompt包含评分关键词 | 主观题 | keywords 字段 | ✅ 已覆盖 |

**技术要点**：
- temperature=0.05（极低温度确保答案确定性，比批改用 0.1 更低）
- JSON 提取支持 markdown 包裹 + 裸 JSON 双模式
- answer_key 格式与现有系统 100% 兼容（向后兼容全系列接口）

---

## 四、安全测试方案

### 4.1 认证安全

| 测试项 | 测试内容 | 预期 | 状态 |
|--------|---------|------|------|
| 无Token访问 | 不传Authorization | 401 | ✅ 已覆盖 |
| 过期Token | exp < now | 401 | ✅ 已覆盖 |
| 篡改Token | payload被修改 | 401 (签名不匹配) | ✅ 已覆盖 |
| 错误Schema | Basic而非Bearer | 401 | ✅ 已覆盖 |
| 空Token | "Bearer " | 401 | ✅ 已覆盖 |
| 角色越权 | 学生访问OCR | 403 | ✅ 已覆盖 |
| 角色越权 | 教师访问管理 | 403 | ✅ 已覆盖 |
| 跨资源越权 | 教师删其他教师试卷 | 403/404 | ✅ 已覆盖 |

### 4.2 输入安全

| 测试项 | 测试内容 | 预期 | 状态 |
|--------|---------|------|------|
| SQL注入-用户名 | `'; DROP TABLE --` | 不崩溃,返回401 | ✅ 已覆盖 |
| SQL注入-密码 | `' OR '1'='1` | 不通过认证 | ✅ 已覆盖 |
| XSS-标题 | `<script>alert()</script>` | 不崩溃 | ✅ 已覆盖 |
| 超长输入 | >200字符标题 | Pydantic 422 | ✅ 已覆盖 |
| 负分数 | total_score=-10 | Pydantic 422 | ✅ 已覆盖 |
| 0分试卷 | total_score=0 | Pydantic 422 (需>0) | ✅ 已覆盖 |
| 超大分数 | total_score=9999 | Pydantic 422 (>1000) | ✅ 已覆盖 |
| 未来日期 | exam_date=2099 | Pydantic 422 | ✅ 已覆盖 |
| 空字段 | user_id="" | Pydantic 422 | ✅ 已覆盖 |
| 密码不一致 | confirm_password != password | Pydantic 422 | ✅ 已覆盖 |
| 教师缺subject | role=teacher, subject=None | Pydantic 422 | ✅ 已覆盖 |
| 短密码 | password="12" | Pydantic 422 (>=6) | ✅ 已覆盖 |
| 无效角色 | role="hacker" | Pydantic 422 | ✅ 已覆盖 |
| 非图片上传 | text/plain | 400 | ✅ 已覆盖 |
| 空文件上传 | 0字节 | 400/500 | ✅ 已覆盖 |
| 不存在的试卷 | paper_id=99999 | 404 | ✅ 已覆盖 |
| 不存在的学生 | student_id=NOBODY | 400/404 | ✅ 已覆盖 |

---

## 五、性能测试方案

### 5.1 SLA 目标

| 接口分类 | 95th Percentile | 最坏情况 |
|---------|----------------|---------|
| 健康检查 | < 50ms | < 100ms |
| 认证类 | < 200ms | < 500ms |
| 查询类 | < 200ms | < 500ms |
| 写入类 | < 300ms | < 1000ms |
| OCR上传 | < 300ms | < 1000ms |
| OCR批改（含外部API） | < 3000ms | < 10000ms |
| 管理统计 | < 300ms | < 1000ms |

### 5.2 并发目标

| 场景 | 并发数 | 成功率要求 |
|------|--------|-----------|
| 健康检查 | 50 | > 95% |
| 登录 | 20 | > 90% |
| 试卷列表 | 30 | > 95% |
| OCR上传 | 10 | > 90% |

### 5.3 吞吐量目标

| 指标 | 基准值 |
|------|--------|
| /health RPS | > 50 req/s |
| 单次完整OCR链路 | < 5s (10题) |

### 5.4 性能测试基础设施

已创建轻量级性能测试（`test_performance.py`），生产环境建议额外使用：

- **locust**: 分布式负载测试，模拟真实用户行为
- **k6**: API 级别性能压测
- **pytest-benchmark**: 集成到 CI/CD 的性能回归基线

---

## 六、测试套件完整清单

### 6.1 文件结构

```
zhipi-cloud/zhipi-backend/
├── pytest.ini                          # Pytest 配置
├── requirements.txt                    # 生产依赖
└── tests/
    ├── __init__.py                     # 测试包标记
    ├── conftest.py                     # Fixtures + Mock 服务
    ├── test_requirements.txt           # 测试依赖
    ├── fixtures/
    │   ├── __init__.py                 # 测试数据常量
    │   └── test_data.py               # (已合并到 __init__.py)
    ├── test_ocr_service.py             # OCR解析+批改 单元测试 (30+ 用例)
    ├── test_llm_service.py             # LLM批改服务 单元测试 (20+ 用例)
    ├── test_question_search.py         # 搜题批改服务 单元测试 (30+ 用例) 🆕
    ├── test_auth.py                    # 认证+安全 集成测试 (35+ 用例)
    ├── test_ocr_pipeline.py            # OCR完整链路 集成测试 (15+ 用例)
    ├── test_performance.py             # 性能+负载 测试 (15+ 用例)
    ├── test_paper_api.py              # (待补充) 试卷CRUD测试
    ├── test_admin_api.py              # (待补充) 管理员接口测试
    └── test_stats_api.py              # (待补充) 统计接口测试
```

### 6.2 测试用例统计

| 模块 | 用例数 | 类型 | 覆盖目标 |
|------|-------|------|---------|
| test_ocr_service | 30+ | 单元 | OCR解析全分支 |
| test_llm_service | 20+ | 单元 | LLM批改全流程 |
| test_question_search | 30+ | 单元 | 搜题批改全场景 🆕 |
| test_auth | 35+ | 集成 | 认证/权限/输入验证 |
| test_ocr_pipeline | 15+ | 集成 | OCR端到端链路 |
| test_performance | 15+ | 性能 | SLA+并发+稳定性 |
| **合计** | **145+** | | |

---

## 七、CI/CD 集成配置

### 7.1 GitHub Actions 示例

```yaml
# .github/workflows/api-tests.yml
name: API 测试

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test123
          MYSQL_DATABASE: zhipi_cloud
        ports:
          - 3306:3306
        options: >-
          --health-cmd "mysqladmin ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          cd zhipi-cloud/zhipi-backend
          pip install -r requirements.txt
          pip install -r tests/test_requirements.txt

      - name: Init test database
        run: |
          mysql -h 127.0.0.1 -u root -ptest123 zhipi_cloud < zhipi-cloud/zhipi-database/sql/05_full_dump.sql

      - name: Run tests with coverage
        env:
          DB_HOST: 127.0.0.1
          DB_PORT: 3306
          DB_USER: root
          DB_PASSWORD: test123
          DB_NAME: zhipi_cloud
          JWT_SECRET_KEY: ci_test_secret_key
        run: |
          cd zhipi-cloud/zhipi-backend
          pytest tests/ --cov=. --cov-report=xml --cov-report=html -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./zhipi-cloud/zhipi-backend/coverage.xml

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run security-only tests
        run: |
          cd zhipi-cloud/zhipi-backend
          pip install httpx pytest
          pytest tests/ -m security -v

  performance:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Run performance benchmarks
        run: |
          cd zhipi-cloud/zhipi-backend
          pip install httpx pytest
          pytest tests/test_performance.py -v -s
```

### 7.2 本地运行指南

```bash
# 1. 安装测试依赖
cd zhipi-cloud/zhipi-backend
pip install -r tests/test_requirements.txt

# 2. 确保数据库已启动且有种子数据
# MySQL: localhost:3307, database: zhipi_cloud
# seed accounts: T007/123456, S032/123456, admin/123456

# 3. 运行全部测试
pytest tests/ -v

# 4. 按模块运行
pytest tests/test_ocr_service.py -v          # OCR 单元测试
pytest tests/test_llm_service.py -v          # LLM 单元测试
pytest tests/test_ocr_pipeline.py -v         # OCR 集成测试
pytest tests/test_auth.py -v                 # 认证安全测试
pytest tests/test_performance.py -v -s       # 性能测试(-s显示print)

# 5. 按标记运行
pytest -m unit -v                     # 仅单元测试
pytest -m integration -v             # 仅集成测试
pytest -m security -v                # 仅安全测试
pytest -m performance -v             # 仅性能测试
pytest -m ocr -v                     # 仅OCR链路测试

# 6. 覆盖率报告
pytest tests/ --cov=. --cov-report=html
# 打开 htmlcov/index.html 查看详细覆盖率
```

---

## 八、风险与建议

### 8.1 已识别的高风险区域

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| **OCR 识别率不稳定** | 🔴 高 | 百度手写体 API 对手写答案的识别率波动大，尤其草书、涂改 | 测试多种笔迹样本；降级到通用OCR的兜底策略已验证 |
| **LLM 评分一致性** | 🟡 中 | 同一答案多次调用 LLM 得分可能不同（temperature=0.1 仍有变化） | 应用层做分数抖动检测；定期人工抽检 |
| **answer_key 格式演进** | 🟡 中 | 从纯字符串到 dict 混合格式，需向后兼容 | 已有兼容逻辑；需持续添加回归测试 |
| **并发批改数据库争抢** | 🟡 中 | 多教师同时批改可能产生 Score 记录状态冲突 | 使用乐观锁或数据库行锁 |
| **外部 API 不可用** | 🟡 中 | 百度 OCR / DeepSeek 宕机导致批改中断 | 实现健康检查 + 告警 + 降级提示 |
| **OCR 图片过大** | 🟢 低 | 高清照片 base64 编码后可能超时 | 前端压缩 + 后端限制文件大小 |

### 8.2 改进建议

1. **OCR 识别质量监控**：添加 `parse_rate` 指标的 Dashboard，当识别率 < 50% 时告警
2. **答案比对增强**：当前只做精确匹配，建议增加模糊匹配（如 OCR 识别 "A" 和 "A " 视为相同）
3. **LLM 评分审计**：记录每次 LLM 调用的原始请求/响应，用于事后审查
4. **限流策略优化**：LLM 接口 5/min 可能不够用，建议改为 per-user 而非 per-IP
5. **增加测试样本**：准备 50+ 份真实手写答卷图片作为 Golden Dataset

---

## 九、实施路线图

```
Phase 1 (本周): 基础设施搭建 ✅
  ├── conftest.py (Fixtures + Mock)         ✅ Done
  ├── pytest.ini 配置                        ✅ Done
  └── 测试数据常量                           ✅ Done

Phase 2 (本周): 核心逻辑单元测试 ✅
  ├── test_ocr_service.py (30+ cases)       ✅ Done
  ├── test_llm_service.py (20+ cases)       ✅ Done
  └── fixtures/test_data.py                 ✅ Done

Phase 3 (本周): 安全+集成测试
  ├── test_auth.py (35+ cases)              ✅ Done
  └── test_ocr_pipeline.py (15+ cases)      ✅ Done

Phase 4 (本周): 性能测试 + 搜题批改 ✅🆕
  ├── test_performance.py (15+ cases)       ✅ Done
  ├── question_search_service.py            ✅ Done
  └── test_question_search.py (30+ cases)   ✅ Done

Phase 5 (下周): 补充覆盖
  ├── test_paper_api.py                     ⏳ 待做
  ├── test_admin_api.py                     ⏳ 待做
  └── test_stats_api.py                     ⏳ 待做

Phase 6 (两周内): 真实环境验证
  ├── 真实百度OCR + DeepSeek API 回归测试
  ├── 50份真实手写答卷 Golden Dataset
  └── locust 分布式负载测试

Phase 7 (持续): CI/CD 集成 + 监控
  ├── GitHub Actions 自动化测试
  ├── 覆盖率门禁 (85%+)
  └── 生产环境 API 健康监控
```

---

## 十、快速参考卡

```bash
# 一键运行核心测试
pytest tests/test_ocr_service.py tests/test_ocr_pipeline.py -v

# 只运行安全相关测试
pytest tests/test_auth.py -k "security or sql_injection or xss or tampered" -v

# 只运行 OCR 批改逻辑
pytest tests/test_ocr_service.py -k "grade or mode_a or mode_b" -v

# 生成覆盖率
pytest tests/ --cov=services --cov=controllers --cov-report=term

# 快速冒烟（跳过慢速测试）
pytest tests/ -m "not slow and not performance" -v

# 并行运行（8核）
pytest tests/ -n 8 -v
```

---

**测试设计：API Tester Expert**
**日期：2026-07-04**
**版本：v1.1**
**状态：Phase 1-4 已完成（含搜题批改），Phase 5-7 待实施**
