# LLM 大题批改功能使用指南

## 功能概述

智批云现在支持**主观题（大题）的 AI 智能批改**。系统采用混合批改策略：
- **客观题**（选择题）：正则比对，快速准确
- **主观题**（简答/论述/计算）：调用 LLM 进行语义理解评分

## 配置方法

### 1. 获取 LLM API Key（以 DeepSeek 为例，最便宜）

1. 打开 https://platform.deepseek.com/
2. 注册账号
3. 创建 API Key
4. 复制 Key

### 2. 填写配置

编辑 `zhipi-cloud/zhipi-backend/.env`：

```env
LLM_API_KEY=sk-你的实际key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 3. 其他可用的 LLM（都兼容 OpenAI 接口）

| 服务商 | BASE_URL | MODEL | 说明 |
|:---|:---|:---|:---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | 最便宜，中文强 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | 阿里云，有免费额度 |
| 智谱GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 免费模型 |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | 需翻墙 |

## 试卷标准答案格式

`answer_key` 字段支持两种格式混合：

### 纯客观题（向后兼容）
```json
{
  "q1": "A",
  "q2": "B",
  "q3": "C"
}
```

### 客观题 + 主观题混合
```json
{
  "q1": "A",
  "q2": "B",
  "q3": {"type": "subjective", "answer": "数据库是长期存储在计算机内的有组织的可共享的数据集合", "score": 10, "keywords": ["长期存储", "有组织", "可共享"]},
  "q4": {"type": "subjective", "answer": "ACID指原子性、一致性、隔离性、持久性", "score": 20, "keywords": ["原子性", "一致性", "隔离性", "持久性"]}
}
```

### 主观题字段说明

| 字段 | 必填 | 说明 |
|:---|:---|:---|
| `type` | 是 | 必须为 `"subjective"` |
| `answer` | 是 | 参考答案 |
| `score` | 是 | 该题满分 |
| `keywords` | 否 | 关键词列表，帮助 LLM 评分 |

## 使用流程

1. 教师创建试卷时，在 `answer_key` 中设置主观题（格式见上）
2. 上传学生答卷图片
3. 点击 **「🧠 大题AI批改」** 按钮
4. 系统自动：OCR识别 → 客观题正则比对 → 主观题LLM评分
5. 每题显示：学生答案、AI评分、AI评语
6. 教师可修改每题分数后提交

## 技术架构

```
答卷图片 → 百度OCR → 全文文本
                        ├─ 客观题 → 正则比对 → 得分
                        └─ 主观题 → 按题号切分 → LLM评分 → 得分+评语
                                              ↓
                                    总分 = 客观题得分 + 主观题得分
```

## API 接口

```
POST /api/ocr/llm-grade?paper_id=1&student_id=S001
```

响应示例：
```json
{
  "message": "AI批改完成（客观题+主观题）",
  "ai_score": 85.5,
  "total_score": 100,
  "detail": [
    {"question": "q1", "score": 5, "is_correct": true, "type": "objective"},
    {"question": "q3", "score": 8, "max_score": 10, "type": "subjective", "feedback": "答到主要要点，但缺少'可共享'特性"}
  ]
}
```

## 注意事项

- LLM 调用需要时间（约5-15秒），前端已设置2分钟超时
- 限流：每分钟5次 LLM 批改请求
- LLM_API_KEY 未配置时，接口会返回明确的错误提示
- 主观题分数可由教师在界面上手动修改后提交
