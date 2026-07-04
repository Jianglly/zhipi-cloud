# test_paper - 手写试卷测试样本集

本目录按科目分类整理"包含手写答案的试卷/答题卡"图片样本，每科 3 份，供**智批云（AI智能批阅系统）**的 OCR 识别、批改模型研发与测试使用。

## 📁 目录结构

```
test_paper/
├── 语文/      ← 中文答题卡（含手写答案/填涂）
│   ├── EPHOIE_example.png            # 4 张真实中文学校试卷合集（EPHOIE）
│   ├── leeguandong_题目排版1.png     # 中文答题卡模板（leeguandong/Answer_card_identification）
│   └── liangzelang_1.jpg             # 公务员考试中文答题卡扫描件（liangzelang/Answer-Card-Recognition）
│
├── 数学/      ← 含初中数学公式的手写题
│   ├── math_formula_1.png            # 手写公式: x = (a²-2)/2, y = (ab)/2（分式方程组）
│   ├── math_formula_2.png            # 手写公式: x₁ - x₅ + x₀ = 0（一元方程）
│   └── math_formula_3.png            # 手写公式: ξ = x/(2√t)（根号分式）
│
├── 英语/      ← 国内英语答题卡（含客观题+主观题）
│   ├── english_answercard_full.jpg           # 完整星火教育2021春初中英语答题卡
│   ├── english_answercard_section_1.jpg      # 单项选择题填涂区域（15题A/B/C/D）
│   └── english_answercard_section_5.jpg      # 阅读理解填涂区域（20题A/B/C/D）
│
└── README.md
```

## 📊 数据来源与说明

### 一、语文答题卡

| 文件 | 来源 | 内容描述 |
|------|------|---------|
| `EPHOIE_example.png` | [HCIILAB/EPHOIE](https://github.com/HCIILAB/EPHOIE)（AAAI 2021） | 真实中文学校试卷头部扫描合集：①兰江小学 2018 学年第二学期六年级语文期中学情独立作业答题卡 ②五年级人教第二学期期末考试 - 语文试题（五）·廊坊安次区 ③莆田一中六年级(上)语文期末直通车 ④四年级下册语文配套练习。涵盖"Complex Layout"和"Noisy Background"两类典型挑战样本 |
| `leeguandong_题目排版1.png` | [leeguandong/Answer_card_identification](https://github.com/leeguandong/Answer_card_identification) | 中文答题卡模板示例：含单选题(15题)、判断题(10题)、多选题(8题)、填空题(11题)、解答题、语言题、选做题、作文题(格子)。说明"客观题必须使用2B铅笔填涂，主观题必须使用黑色签字笔书写" |
| `liangzelang_1.jpg` | [liangzelang/Answer-Card-Recognition](https://github.com/liangzelang/Answer-Card-Recognition) | 公务员考试中文答题卡扫描件，140道单项选择题A/B/C/D填涂区，含真实手写准考证号填涂痕迹 |

### 二、数学试卷（含初中数学公式）

所有 3 张手写公式图片均由 **Google MathWriting 数据集**（[google-research/google-research/mathwriting](https://github.com/google-research/google-research/tree/master/mathwriting)）的 InkML 笔迹数据通过 `convert_inkml_to_png.py` 脚本渲染生成。

| 文件 | 公式（LaTeX） | 难度 | 描述 |
|------|--------------|------|------|
| `math_formula_1.png` | `x = (a²-2)/2, y = (ab)/2` | 初中 | 分式方程组（分式 + 平方） |
| `math_formula_2.png` | `x₁ - x₅ + x₀ = 0` | 初中 | 一元方程（含下标与上标） |
| `math_formula_3.png` | `ξ = x / (2√t)` | 初中 | 根号分式（开方 + 分式） |

> **数据来源细节**：从 MathWriting excerpt 数据集（1.6MB）中筛选出 157 个初中水平的简单代数公式（剔除偏微分、积分、求和、矩阵、希腊字母等大学/研究生级别符号），选取 6 个样本再精选 3 个作为最终样本。InkML 格式的笔迹坐标通过 PIL 渲染为白底黑字的 PNG 图片（参见 `convert_inkml_to_png.py`）。

### 三、英语答题卡

| 文件 | 来源 | 内容描述 |
|------|------|---------|
| `english_answercard_full.jpg` | [Wasim37/answer_card_detection](https://github.com/Wasim37/answer_card_detection) | **星火教育教师季度考（2021春）初中英语**完整答题卡扫描件。包含：①填写区（姓名、班级、校区、准考证号）②14题单项选择（A/B/C/D）③5题词汇运用 ④20题完形填空（A/B/C/D）⑤4题语法填空 ⑥4题任务型阅读 ⑦8题短文改错（手写）⑧1题书面表达（Dear Diary... 70词手写英文作文，含 7 处手写更正）。**含完整客观题填涂与主观题手写英文** |
| `english_answercard_section_1.jpg` | 同上 | 第1大题 - 单项选择题（15题）填涂区域特写 |
| `english_answercard_section_5.jpg` | 同上 | 第5大题 - 阅读理解（20题）填涂区域特写 |

## 🔍 搜索过程

数据来源从以下 5 个平台搜索：
- **Google Dataset Search** (https://datasetsearch.research.google.com/)
- **Kaggle** (https://www.kaggle.com/)
- **IEEE DataPort** (https://ieee-dataport.org/)
- **arXiv** (https://arxiv.org/)
- **GitHub** (https://github.com/)

实际可用下载情况：
- **Google Dataset Search / Kaggle / arXiv / IEEE DataPort**：搜索结果多为分类、检测、识别数据集或需注册申请，未找到可直接下载的"完整真实考试试卷"图集
- **GitHub**：找到最完整、最易下载的真实样张，已全部采用

## 📈 质量评估

| 维度 | 语文 | 数学 | 英语 |
|------|------|------|------|
| 含手写内容 | ✅ | ✅ | ✅ |
| 含客观题 | ✅ 填涂 | ✅ 公式 | ✅ 填涂 |
| 含主观题 | ✅ 签名/笔迹 | ✅ 笔迹 | ✅ 手写英文作文 |
| 学科符合 | ✅ 中文语文 | ✅ 初中数学 | ✅ 国内英语 |
| 真实场景 | ✅ 真实学校/考试 | ⚠️ 数据集重渲染 | ✅ 真实考试扫描 |
| 分辨率 | 高 | 中（重渲染） | 高 |

## 🔧 重新生成数学公式

如需重新生成数学公式图片：
```bash
# 1. 下载 MathWriting excerpt 数据集
#    https://storage.googleapis.com/mathwriting_data/mathwriting-2024-excerpt.tgz
# 2. 解压到 test_paper/数学/ 目录
# 3. 运行转换脚本
python convert_inkml_to_png.py
```

## 📝 备注

- 本数据集**仅用于学术研究和模型测试**，请勿用于商业用途
- 各图片版权归原作者及对应仓库所有
- Google MathWriting 数据集采用 CC BY-NC-SA 4.0 协议
