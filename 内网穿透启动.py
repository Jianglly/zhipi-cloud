# -*- coding: utf-8 -*-
"""
ZhiPi Cloud - 内网穿透启动器（单端口版）
使用 natapp 将 8000 端口暴露到公网，任何人都能访问

使用前提：
  1. 先用"启动智批云.bat"选[2]网络共享模式，让前端和后端都在8000端口
  2. 去 https://natapp.cn 注册账号
  3. 创建 1 条免费隧道：本地端口 8000
  4. 下载 natapp.exe 放到本脚本同目录
  5. 把下面的 authtoken 改成你自己的
"""
import subprocess
import sys
import os
import time
import socket

# ===================== 配置区 =====================
NATAPP_TOKEN = "959927161258101b"   # ← 改成你自己的
# =================================================

PROJECT_ROOT  = os.path.dirname(os.path.abspath(__file__))
NATAPP_EXE    = os.path.join(PROJECT_ROOT, "natapp.exe")


def c(code, text):
    colors = {
        "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
        "blue": "\033[94m", "cyan": "\033[96m", "bold": "\033[1m", "reset": "\033[0m",
    }
    return f"{colors.get(code, '')}{text}{colors['reset']}"


def check_port(port, timeout=1):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    os.system("")
    print(c("bold", "\n" + "=" * 56))
    print(c("bold", "     ZhiPi Cloud - 内网穿透共享（单端口）"))
    print(c("bold", "=" * 56))

    # 检查 natapp.exe
    if not os.path.exists(NATAPP_EXE):
        print(f"\n  {c('red', '[错误]')} 找不到 natapp.exe！")
        print(f"\n  请先：")
        print(f"    1. 访问 {c('cyan', 'https://natapp.cn')} 注册账号")
        print(f"    2. 创建隧道（本地端口 8000），并下载 natapp.exe")
        print(f"    3. 放到：{c('bold', PROJECT_ROOT)}")
        print(f"    4. 把 authtoken 填入本脚本顶部")
        input("\n  按 Enter 退出...")
        sys.exit(1)

    if NATAPP_TOKEN == "你的隧道authtoken":
        print(f"\n  {c('yellow', '[提示]')} 还没填 authtoken！")
        print(f"\n  编辑本文件，改顶部：")
        print(f"    {c('bold', 'NATAPP_TOKEN = \"你的隧道authtoken\"')}")
        print(f"\n  natapp 注册：{c('cyan', 'https://natapp.cn')}")
        input("\n  按 Enter 退出...")
        sys.exit(0)

    # 检查 8000 端口
    if not check_port(8000):
        print(f"\n  {c('red', '[错误]')} 端口 8000 没有服务在运行！")
        print(f"  请先以 [2] 网络共享模式启动系统")
        input("\n  按 Enter 退出...")
        sys.exit(1)
    print(f"\n  {c('green', '[OK]')} 服务运行中（:8000）")

    # 启动 natapp 隧道
    print(f"\n  {c('cyan', '启动 natapp 隧道...')}")
    cmd = f'start "natapp-8000" cmd /k "cd /d {PROJECT_ROOT} & {NATAPP_EXE} -authtoken={NATAPP_TOKEN} -log=stdout"'
    subprocess.Popen(cmd, shell=True)
    time.sleep(3)
    print(f"  {c('green', '[OK]')} natapp 窗口已打开")

    # 提示获取地址
    print(f"""
  {c('yellow', '>>> 请查看 natapp 窗口，找到 Forwarding 行 <<<')}
  例如：
      {c('green', 'Forwarding  http://ab12cd34.natapp1.cc -> 127.0.0.1:8000')}

  把 http://ab12cd34.natapp1.cc 发给其他人即可访问！
""")
    tunnel_url = input(f"  输入 [穿透地址]（可选，直接回车跳过）: ").strip().rstrip("/")

    # 完成
    print()
    print(c("bold", "  " + "=" * 56))
    print(c("bold", c("green", "  [共享链接已就绪！]")))
    print(c("bold", "  " + "=" * 56))
    print()
    if tunnel_url:
        print(f"  {c('cyan', '分享这个地址:')} {c('bold', tunnel_url)}")
    else:
        print(f"  {c('yellow', '请查看 natapp 窗口中的 Forwarding 地址')}")
    print()
    print(f"  {c('yellow', '演示账号:')}")
    print(f"    教师：{c('bold','T007')} / {c('bold','123456')}")
    print(f"    学生：{c('bold','S032')} / {c('bold','123456')}")
    print()
    print(f"  {c('dim', '关闭 natapp 窗口后共享链接失效')}")
    print(f"  {c('dim', '本地仍可通过 http://localhost:8000 访问')}")
    print()

    input("  按 Enter 退出本启动器...")


if __name__ == "__main__":
    main()
