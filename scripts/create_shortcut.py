import sys
import os

# 创建快捷方式
import pythoncom
from win32com.client import Dispatch

desktop = os.path.join(os.path.expanduser("~"), "Desktop")
lnk_path = os.path.join(desktop, "start.lnk")
target = r"E:\Homwork\数据库系统\手工试卷批阅\start.bat"
working_dir = r"E:\Homwork\数据库系统\手工试卷批阅"

shell = Dispatch("WScript.Shell")
shortcut = shell.CreateShortcut(lnk_path)
shortcut.TargetPath = target
shortcut.WorkingDirectory = working_dir
shortcut.Description = "智批云 - 一键启动全部服务"
shortcut.Save()

print(f"快捷方式已创建: {lnk_path}")
