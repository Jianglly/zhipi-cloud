#!/usr/bin/env python3
"""
智批云 - 数据库初始化脚本
用途：全新环境下一键创建数据库、建表、灌入种子数据
使用：python scripts/init_database.py
"""
import os
import sys
import re
import pymysql

# ─── 路径 ───
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-backend")
SQL_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-database", "sql")
ENV_FILE = os.path.join(BACKEND_DIR, ".env")


def read_env(path):
    """读取 .env 文件"""
    env = {}
    if not os.path.exists(path):
        print(f"  [ERROR] .env not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def strip_sql_comments(content):
    """去掉 -- 行注释，保留 SQL 语句"""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        # 去掉行内尾注释（简单处理，不处理字符串内的 -- ）
        if "--" in line and not line.strip().startswith("'"):
            line = line.split("--")[0].rstrip()
        if line.strip():
            lines.append(line)
    return "\n".join(lines)


def split_sql(content):
    """按分号分割 SQL，正确处理多行语句"""
    clean = strip_sql_comments(content)
    statements = []
    for stmt in clean.split(";"):
        stmt = stmt.strip()
        if stmt:
            statements.append(stmt)
    return statements


def hash_password(password):
    """用 bcrypt 哈希密码（兼容后端 security_service）"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    except ImportError:
        # fallback: passlib
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.hash(password)


def main():
    print("=" * 50)
    print("  ZhiPi Cloud - Database Initialization")
    print("=" * 50)
    print()

    env = read_env(ENV_FILE)
    host = env.get("DB_HOST", "localhost")
    port = int(env.get("DB_PORT", "3306"))
    user = env.get("DB_USER", "root")
    pwd = env.get("DB_PASSWORD", "")
    db = env.get("DB_NAME", "zhipi_cloud")

    print(f"  Host: {host}:{port}")
    print(f"  User: {user}")
    print(f"  DB:   {db}")
    print()

    # ─── Step 1: 创建数据库 ───
    print("[1/4] Creating database ...")
    conn = pymysql.connect(host=host, port=port, user=user, password=pwd, charset="utf8mb4")
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db}` "
        "DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn.commit()
    cursor.close()
    conn.close()
    print("      OK")
    print()

    # ─── Step 2: 执行 SQL 脚本 ───
    conn = pymysql.connect(
        host=host, port=port, user=user, password=pwd,
        database=db, charset="utf8mb4"
    )
    cursor = conn.cursor()

    sql_files = [
        "01_create_tables.sql",
        "02_seed_data.sql",
        "03_views_subschema.sql",
        "04_admin.sql",
    ]

    print("[2/4] Executing SQL scripts ...")
    for sf in sql_files:
        path = os.path.join(SQL_DIR, sf)
        if not os.path.exists(path):
            print(f"      [SKIP] {sf} not found")
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        statements = split_sql(content)
        ok = 0
        skip = 0
        for stmt in statements:
            try:
                cursor.execute(stmt)
                ok += 1
            except pymysql.err.MySQLError as e:
                code = e.args[0]
                # 1050: table exists, 1062: duplicate entry — 都跳过
                if code in (1050, 1062):
                    skip += 1
                else:
                    print(f"      [WARN] {sf}: {e}")
        conn.commit()
        print(f"      [OK] {sf}  ({ok} executed, {skip} skipped)")
    print()

    # ─── Step 3: 修正 admin 密码 ───
    print("[3/4] Setting admin password ...")
    admin_hash = hash_password("123456")
    cursor.execute(
        "INSERT INTO admin (admin_id, name, password) VALUES ('admin', 'system admin', %s) "
        "ON DUPLICATE KEY UPDATE password = %s",
        (admin_hash, admin_hash)
    )
    conn.commit()
    print("      OK (admin / 123456)")
    print()

    # ─── Step 4: 汇总 ───
    print("[4/4] Database Summary")
    print("  ──────────────────────────")
    tables = ["class", "student", "teacher", "paper", "score", "operation_log", "admin"]
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{t}`")
            count = cursor.fetchone()[0]
            print(f"  {t:15s}  {count:>5} rows")
        except pymysql.err.MySQLError:
            print(f"  {t:15s}  [TABLE MISSING]")
    print()

    cursor.close()
    conn.close()

    print("=" * 50)
    print("  Done! Demo accounts:")
    print("    Teacher:  T007 / 123456")
    print("    Student:  S032 / 123456")
    print("    Admin:    admin / 123456")
    print("=" * 50)


if __name__ == "__main__":
    main()
