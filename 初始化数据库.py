"""
智批云 - 数据库一键初始化脚本
自动创建数据库、建表、插入测试数据、创建视图
"""

import os
import sys
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SQL_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-database", "sql")
ENV_FILE = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-backend", ".env")

# ── 读取配置 ──────────────────────────────────────────
def load_env():
    """从 .env 文件读取数据库配置"""
    config = {"host": "localhost", "port": 3306, "user": "root", "password": "", "db": "zhipi_cloud"}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if key == "DB_HOST":
                        config["host"] = val
                    elif key == "DB_PORT":
                        config["port"] = int(val)
                    elif key == "DB_USER":
                        config["user"] = val
                    elif key == "DB_PASSWORD":
                        config["password"] = val
                    elif key == "DB_NAME":
                        config["db"] = val
    return config


def check_mysql():
    """检查 pymysql 是否可用"""
    try:
        import pymysql
        return True
    except ImportError:
        return False


def install_pymysql():
    """安装 pymysql"""
    print("  [*] Installing pymysql...")
    python = sys.executable
    os.system(f'"{python}" -m pip install pymysql -q')
    try:
        import pymysql
        return True
    except ImportError:
        return False


def create_database(cfg, password):
    """创建数据库（如果不存在）"""
    import pymysql
    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=password,
        charset="utf8mb4",
    )
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{cfg['db']}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn.commit()
    cursor.close()
    conn.close()
    return cfg["db"]


def run_sql_file(cfg, password, filepath, desc):
    """执行单个 SQL 文件"""
    import pymysql
    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=password,
        database=cfg["db"],
        charset="utf8mb4",
    )
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()

    # 按分号分割执行每条语句（跳过注释和空行）
    statements = []
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("--") and not stmt.startswith("/*"):
            statements.append(stmt)

    cursor = conn.cursor()
    ok = 0
    fails = 0
    for stmt in statements:
        try:
            cursor.execute(stmt)
            ok += 1
        except Exception as e:
            # 忽略一些无害错误（如重复建表）
            err_msg = str(e)
            if "already exists" in err_msg.lower() or "duplicate" in err_msg.lower():
                ok += 1
            else:
                fails += 1
                print(f"    [!] {err_msg[:80]}")
    conn.commit()
    cursor.close()
    conn.close()
    return ok, fails


# ── 主入口 ────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  ZhiPi Cloud - Database Initialization")
    print("=" * 55)
    print()

    cfg = load_env()

    # 显示配置
    print(f"  MySQL Host : {cfg['host']}:{cfg['port']}")
    print(f"  MySQL User : {cfg['user']}")
    print(f"  Database   : {cfg['db']}")
    print()

    # 密码
    if cfg["password"]:
        password = cfg["password"]
        print("  [*] Using password from .env file")
    else:
        password = input("  Enter MySQL password: ").strip()
    print()

    # 检查 pymysql
    if not check_mysql():
        if not install_pymysql():
            print("\n  [FAIL] Cannot install pymysql. Run: pip install pymysql")
            input("\n  Press Enter to exit...")
            return

    sql_files = [
        ("01_create_tables.sql", "Creating tables"),
        ("02_seed_data.sql", "Inserting seed data"),
        ("03_views_subschema.sql", "Creating views"),
    ]

    # Step 1: 创建数据库
    print(f"  [1/4] Creating database '{cfg['db']}'...")
    try:
        create_database(cfg, password)
        print(f"        [OK] Database '{cfg['db']}' ready")
    except Exception as e:
        print(f"        [FAIL] {e}")
        print("\n  请确认:")
        print("   1. MySQL 服务已启动")
        print("   2. 主机/端口/密码正确")
        input("\n  Press Enter to exit...")
        return

    # Step 2-4: 执行 SQL 文件
    total_ok, total_fail = 0, 0
    for i, (filename, desc) in enumerate(sql_files, start=2):
        filepath = os.path.join(SQL_DIR, filename)
        print(f"  [{i}/4] {desc} ({filename})...")
        if not os.path.exists(filepath):
            print(f"        [FAIL] File not found: {filepath}")
            total_fail += 1
            continue
        try:
            ok, fails = run_sql_file(cfg, password, filepath, desc)
            total_ok += ok
            total_fail += fails
            status = "OK" if fails == 0 else f"OK ({ok} passed, {fails} warnings)"
            print(f"        [{status}] {filename}")
        except Exception as e:
            print(f"        [FAIL] {e}")
            total_fail += 1

    # 结果
    print()
    print("  " + "-" * 40)
    if total_fail == 0:
        print(f"  [ALL DONE] {total_ok} statements executed successfully!")
        print(f"  Database '{cfg['db']}' is ready.")
    else:
        print(f"  [DONE] {total_ok} passed, {total_fail} warnings")
    print()
    print("  Demo Accounts:")
    print("    Teacher : T001 / 123456")
    print("    Student : 2414100311 / 123456")
    print()
    input("  Press Enter to exit...")


if __name__ == "__main__":
    main()
