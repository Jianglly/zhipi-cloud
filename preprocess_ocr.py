#!/usr/bin/env python3
"""
答题卡预处理 + OCR 识别脚本
支持：压缩尺寸 → 裁剪区域 → 增强对比度 → 调用百度 OCR

用法：
    python preprocess_ocr.py <图片路径> [--crop <region>]

示例：
    python preprocess_ocr.py test_paper/英语/english_answercard_full.jpg
    python preprocess_ocr.py test_paper/语文/liangzelang_1.jpg --crop left
    python preprocess_ocr.py test_paper/英语/english_answercard_full.jpg --crop right
"""
import os
import sys
import json
import base64
import time
import argparse
import tempfile
from pathlib import Path
from typing import Tuple, List, Optional

import requests
from PIL import Image, ImageEnhance, ImageFilter

# ========== 配置 ==========
BACKEND_ROOT = r"G:/Homwork/数据库系统/手工试卷批阅/zhipi-cloud/zhipi-backend"
env_path = os.path.join(BACKEND_ROOT, ".env")

config = {}
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

BAIDU_API_KEY = config.get("BAIDU_OCR_API_KEY", "")
BAIDU_SECRET_KEY = config.get("BAIDU_OCR_SECRET_KEY", "")

# 输出临时目录
OUTPUT_DIR = r"G:/Homwork/数据库系统/手工试卷批阅/test_paper/preprocessed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

_baidu_token_cache = {"token": None, "expires_at": 0}


# ========== 百度 OCR 工具 ==========

def get_baidu_access_token():
    """获取百度 Token"""
    global _baidu_token_cache
    if _baidu_token_cache["token"] and _baidu_token_cache["expires_at"] > time.time() + 300:
        return _baidu_token_cache["token"]

    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        print("Error: 百度OCR未配置")
        sys.exit(1)

    token_url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY,
    }

    resp = requests.post(token_url, params=params, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if "error" in result:
        print(f"Token failed: {result}")
        sys.exit(1)

    token = result["access_token"]
    expires = result.get("expires_in", 2592000)
    _baidu_token_cache["token"] = token
    _baidu_token_cache["expires_at"] = time.time() + expires
    return token


def call_baidu_general(image_path: str, token: str) -> Tuple[str, List[dict]]:
    """调用百度通用文字识别"""
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={token}"

    with open(image_path, "rb") as f:
        img_data = f.read()

    img_base64 = base64.b64encode(img_data).decode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"image": img_base64, "detect_direction": "true", "paragraph": "true"}

    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if "error_code" in result:
        return None, result

    words = result.get("words_result", [])
    full_text = "\n".join([item["words"] for item in words])
    return full_text, words


# ========== 预处理函数 ==========

def preprocess_image(
    image_path: str,
    max_dimension: int = 2000,
    enhance_contrast: float = 1.5,
    sharpen: bool = True,
    grayscale: bool = False
) -> Image.Image:
    """
    预处理图片：
    - 尺寸限制（max_dimension）
    - 增强对比度
    - 锐化
    - 可选灰度
    """
    img = Image.open(image_path)

    # 1. 转 RGB（去除 alpha 通道等）
    if img.mode != "RGB":
        img = img.convert("RGB")

    # 2. 尺寸限制（保持比例缩放）
    w, h = img.size
    max_d = max(w, h)
    if max_d > max_dimension:
        ratio = max_dimension / max_d
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"  [Resize] {w}x{h} → {new_w}x{new_h}")

    # 3. 增强对比度
    if enhance_contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(enhance_contrast)

    # 4. 锐化
    if sharpen:
        img = img.filter(ImageFilter.SHARPEN)

    # 5. 灰度（可选）
    if grayscale:
        img = img.convert("L").convert("RGB")

    return img


def crop_region(img: Image.Image, region: str) -> Image.Image:
    """
    裁剪答题卡区域

    region:
    - left:   左半部分（通常含选择题 ABCD）
    - right:  右半部分（通常含主观题/改错）
    - top:    上半部分
    - bottom: 下半部分
    - center: 中间主体（去掉页边距）
    """
    w, h = img.size

    if region == "left":
        return img.crop((0, 0, w * 0.55, h))
    elif region == "right":
        return img.crop((w * 0.45, 0, w, h))
    elif region == "top":
        return img.crop((0, 0, w, h * 0.5))
    elif region == "bottom":
        return img.crop((0, h * 0.5, w, h))
    elif region == "center":
        margin = int(min(w, h) * 0.05)
        return img.crop((margin, margin, w - margin, h - margin))
    elif region.startswith("custom:"):
        # custom:left,top,right,bottom (比例)
        coords = list(map(float, region.split(":")[1].split(",")))
        box = (
            int(w * coords[0]), int(h * coords[1]),
            int(w * coords[2]), int(h * coords[3])
        )
        return img.crop(box)
    else:
        return img


def detect_dark_regions(img: Image.Image, threshold: int = 128) -> List[dict]:
    """
    简单的暗区检测（用于识别涂黑的选择题区域）
    返回暗区列表，每个含位置和平均灰度
    """
    gray = img.convert("L")
    w, h = gray.size

    # 将图片分成网格，检测每个网格的平均亮度
    grid_w, grid_h = w // 20, h // 20
    dark_regions = []

    for row in range(20):
        for col in range(20):
            left = col * grid_w
            top = row * grid_h
            right = min((col + 1) * grid_w, w)
            bottom = min((row + 1) * grid_h, h)

            region = gray.crop((left, top, right, bottom))
            avg_brightness = sum(region.getdata()) / (region.width * region.height)

            if avg_brightness < threshold:
                dark_regions.append({
                    "row": row, "col": col,
                    "x": (left + right) / 2, "y": (top + bottom) / 2,
                    "brightness": round(avg_brightness, 1),
                    "left": left, "top": top,
                    "right": right, "bottom": bottom
                })

    return dark_regions


# ========== 主流程 ==========

def process_image(image_path: str, region: str = None, max_dim: int = 2000):
    """处理单张图片"""
    print(f"\n{'='*60}")
    print(f"处理: {os.path.basename(image_path)}")
    print(f"{'='*60}")

    # 1. 预处理
    img = preprocess_image(image_path, max_dimension=max_dim)
    print(f"  [Preprocess] Contrast↑, Sharpen")

    # 2. 裁剪（如果指定）
    if region:
        img = crop_region(img, region)
        print(f"  [Crop] region={region}, size={img.size}")

    # 3. 保存预处理后的图片
    base_name = Path(image_path).stem
    suffix = f"_{region}" if region else ""
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}{suffix}_preprocessed.jpg")
    img.save(out_path, "JPEG", quality=90)
    print(f"  [Save] {out_path}")

    # 4. 获取暗区（可选，用于分析涂卡区域）
    dark_regions = detect_dark_regions(img)
    if dark_regions:
        print(f"  [Dark Regions] 发现 {len(dark_regions)} 个暗区（可能为涂卡区域）")
        # 按列分组，看是否有规律排列（选择题模式）
        cols = {}
        for r in dark_regions:
            c = r["col"]
            cols[c] = cols.get(c, 0) + 1
        sorted_cols = sorted(cols.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"  [Dark Pattern] 暗区最多的列: {sorted_cols}")

    # 5. 调用 OCR
    token = get_baidu_access_token()
    print(f"  [OCR] Calling Baidu general_basic...")

    text, words = call_baidu_general(out_path, token)
    if text is None:
        print(f"  [OCR Failed] {json.dumps(words, ensure_ascii=False, indent=2)}")
        return

    print(f"  [OCR Result] 识别到 {len(words)} 个词块:")
    for i, item in enumerate(words[:15]):
        print(f"    {i+1:2d}. {item['words']}")
    if len(words) > 15:
        print(f"    ... 还有 {len(words)-15} 个词块")

    print(f"\n  [Full Text]\n  {text[:500]}{'...' if len(text) > 500 else ''}")

    return text, words


def main():
    parser = argparse.ArgumentParser(description="答题卡预处理 + OCR")
    parser.add_argument("image", nargs="?", help="图片路径（--all 时可选）")
    parser.add_argument("--crop", choices=["left", "right", "top", "bottom", "center"],
                        help="裁剪区域: left=选择题区, right=主观题区")
    parser.add_argument("--max-dim", type=int, default=2000,
                        help="最大边长（默认2000）")
    parser.add_argument("--all", action="store_true",
                        help="处理所有测试图片")
    args = parser.parse_args()

    if not args.all and not args.image:
        parser.print_help()
        sys.exit(1)

    if args.all:
        # 处理所有测试图片
        base = r"G:/Homwork/数据库系统/手工试卷批阅/test_paper"
        images = [
            ("英语/english_answercard_full.jpg", "英语完整答题卡"),
            ("英语/english_answercard_section_1.jpg", "英语选择区"),
            ("英语/english_answercard_section_5.jpg", "英语改错区"),
            ("英语/1a095a0ecbf240f3551c24ed367b0e49.jpg", "英语截图"),
            ("语文/liangzelang_1.jpg", "公务员考试涂卡"),
            ("语文/leeguandong_题目排版1.png", "语文题目排版"),
            ("数学/math_formula_1.png", "数学公式1"),
        ]

        for rel_path, label in images:
            path = os.path.join(base, rel_path)
            if not os.path.exists(path):
                print(f"\n跳过: {path} 不存在")
                continue
            try:
                # 公务员涂卡太大，用更大尺寸
                max_dim = 3000 if "liangzelang" in path else 2000
                process_image(path, max_dim=max_dim)
                time.sleep(0.5)
            except Exception as e:
                print(f"Error: {e}")
    else:
        process_image(args.image, region=args.crop, max_dim=args.max_dim)


if __name__ == "__main__":
    main()
