#!/usr/bin/env python3
"""
真实百度OCR识别测试脚本
直接调用百度OCR API，识别 test_paper 目录下的图片

用法：
    cd zhipi-cloud/zhipi-backend
    python test_real_ocr.py
"""
import os
import sys
import json
import base64
import time
import requests

# 配置正确的路径
BACKEND_ROOT = r"G:/Homwork/数据库系统/手工试卷批阅/zhipi-cloud/zhipi-backend"
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# 直接读取 .env 文件，不依赖 pydantic-settings 的路径解析
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

TEST_PAPER_DIR = r"G:/Homwork/数据库系统/手工试卷批阅/test_paper"

_baidu_token_cache = {"token": None, "expires_at": 0}


def get_baidu_access_token():
    global _baidu_token_cache
    if _baidu_token_cache["token"] and _baidu_token_cache["expires_at"] > time.time() + 300:
        return _baidu_token_cache["token"]

    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY or BAIDU_API_KEY == "your_api_key_here":
        print("Error: Baidu OCR not configured. Check BAIDU_OCR_API_KEY in .env")
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
    print(f"Token OK, expires in {expires//86400} days")
    return token


def call_baidu_handwriting(image_path, token):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting?access_token={token}"
    with open(image_path, "rb") as f:
        img_data = f.read()

    img_base64 = base64.b64encode(img_data).decode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"image": img_base64, "recognize_granularity": "big"}

    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if "error_code" in result:
        return None, result

    words = result.get("words_result", [])
    full_text = "\n".join([item["words"] for item in words])
    return full_text, words


def call_baidu_general(image_path, token):
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


def test_single_image(image_path, token, label):
    print(f"\n{'='*60}")
    print(f"Image: {label}")
    print(f"Path: {image_path}")
    print(f"{'='*60}")

    # 1. 手写体识别
    print("\n>>> Handwriting OCR:")
    hw_text, hw_words = call_baidu_handwriting(image_path, token)
    if hw_text is None:
        print(f"Failed: {json.dumps(hw_words, ensure_ascii=False, indent=2)}")
    else:
        print(f"Found {len(hw_words)} words:")
        for item in hw_words[:12]:
            print(f"  [{item.get('words', '')}]")
        if len(hw_words) > 12:
            print(f"  ... and {len(hw_words)-12} more")
        print(f"\nFull text:\n{hw_text[:500]}{'...' if len(hw_text) > 500 else ''}")

    # 2. 通用识别
    print("\n>>> General OCR:")
    gen_text, gen_words = call_baidu_general(image_path, token)
    if gen_text is None:
        print(f"Failed: {json.dumps(gen_words, ensure_ascii=False, indent=2)}")
    else:
        print(f"Found {len(gen_words)} words:")
        for item in gen_words[:12]:
            print(f"  [{item.get('words', '')}]")
        if len(gen_words) > 12:
            print(f"  ... and {len(gen_words)-12} more")
        print(f"\nFull text:\n{gen_text[:500]}{'...' if len(gen_text) > 500 else ''}")


def main():
    print("=" * 60)
    print("  ZhiPi Cloud - Real Baidu OCR Test")
    print("=" * 60)

    token = get_baidu_access_token()

    images = [
        (os.path.join(TEST_PAPER_DIR, "英语", "english_answercard_full.jpg"), "English answer card (handwriting + print mix)"),
        (os.path.join(TEST_PAPER_DIR, "语文", "liangzelang_1.jpg"), "Chinese exam answer card (pure print/fill)"),
        (os.path.join(TEST_PAPER_DIR, "数学", "math_formula_1.png"), "Math handwritten formula (pure handwriting)"),
    ]

    for path, label in images:
        if not os.path.exists(path):
            print(f"\nSkip: {path} not found")
            continue
        try:
            test_single_image(path, token, label)
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")

    print(f"\n{'='*60}")
    print("Test complete")


if __name__ == "__main__":
    main()
