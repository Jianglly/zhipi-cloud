# -*- coding: utf-8 -*-
"""
ZhiPi Cloud - Smart Launcher (UTF-8 Safe)
Run this instead of the .bat file for a nice Chinese UI.
"""
import subprocess
import sys
import os
import time
import socket
import shutil

# --- Config ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-frontend")
SQL_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-database", "sql")
VENV_PYTHON = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
MODE = "dev"  # dev | shared


def c(code, text):
    """Color output helper."""
    colors = {
        "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
        "blue": "\033[94m", "cyan": "\033[96m", "bold": "\033[1m",
        "dim": "\033[2m", "reset": "\033[0m",
    }
    return f"{colors.get(code, '')}{text}{colors['reset']}"


def check_port(port, timeout=1):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_cmd(cmd, capture=True):
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture, text=True,
            encoding="utf-8", errors="replace"
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def step(num, total, title):
    print(f"\n  {c('cyan', f'[{num}/{total}]')} {c('bold', title)}")


def ok(msg="OK"):
    print(f"      {c('green', '[OK]')} {msg}")


def fail(msg="FAILED"):
    print(f"      {c('red', '[FAIL]')} {msg}")


def warn(msg="WARN"):
    print(f"      {c('yellow', '[WARN]')} {msg}")


def main():
    os.system("")  # Enable ANSI escape codes on Windows
    global MODE

    print(c("bold", "\n" + "=" * 50))
    print(c("bold", "       ZhiPi Cloud - One-Click Launcher"))
    print(c("bold", "=" * 50))

    # --- Mode Selection ---
    print(f"\n  {c('cyan', '选择运行模式:')}")
    print(f"    {c('bold', '[1]')} 本地开发  — 前后端分离，各开窗口，热更新")
    print(f"    {c('bold', '[2]')} 网络共享  — 构建前端，单端口8000，只需一条natapp隧道")
    choice = input(f"\n  请输入 [1/2]（默认1）: ").strip()
    MODE = "shared" if choice == "2" else "dev"

    if MODE == "shared":
        print(f"\n  {c('yellow', '>>> 网络共享模式 <<<')}")
        print(f"     前端将构建为静态文件，由后端统一托管在 8000 端口")
        print(f"     内网穿透时只需一条隧道指向 8000\n")

    # ---- Step 1: Python ----
    step(1, 6, "Checking Python...")
    rc, out, _ = run_cmd("python --version")
    if rc != 0:
        fail("Python not found!")
        print(f"      Install from: https://www.python.org/downloads/")
        input("\n  Press Enter to exit...")
        sys.exit(1)
    ok(out)

    # ---- Step 2: Node.js ----
    step(2, 6, "Checking Node.js...")
    rc, out, _ = run_cmd("node --version")
    if rc != 0:
        fail("Node.js not found!")
        print(f"      Install from: https://nodejs.org/")
        input("\n  Press Enter to exit...")
        sys.exit(1)
    ok(out)

    # ---- Step 3: MySQL ----
    step(3, 6, "Checking MySQL Service...")
    mysql_started = False
    for svc in ["MySQL80", "MySQL"]:
        rc, out, _ = run_cmd(f"sc query {svc}")
        if rc == 0:
            # Check if already running
            if "RUNNING" in out:
                ok(f"{svc} already running")
                mysql_started = True
                break
            # Try to start (may fail with permission error if not admin - that's OK)
            run_cmd(f"net start {svc}")
            # Verify by checking port
            time.sleep(1)
            if check_port(3306) or check_port(3307):
                ok(f"{svc} is online")
            else:
                ok(f"{svc} start attempted (run as Admin if needed)")
            mysql_started = True
            break
    if not mysql_started:
        warn("MySQL service NOT found - start it manually")

    # ---- Step 4: Database Init ----
    step(4, 6, "Initializing Database...")

    # Read DB credentials from .env
    db_cfg = {"host": "localhost", "port": 3306, "user": "root", "password": "", "db": "zhipi_cloud"}
    env_path = os.path.join(BACKEND_DIR, ".env")
    if not os.path.exists(env_path):
        env_example = os.path.join(BACKEND_DIR, ".env.example")
        if os.path.exists(env_example):
            shutil.copy(env_example, env_path)
            ok(".env created from .env.example")
        else:
            warn(".env.example not found, using defaults")

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()
                    if key == "DB_HOST": db_cfg["host"] = val
                    elif key == "DB_PORT": db_cfg["port"] = int(val)
                    elif key == "DB_USER": db_cfg["user"] = val
                    elif key == "DB_PASSWORD": db_cfg["password"] = val
                    elif key == "DB_NAME": db_cfg["db"] = val

    # Try init database - auto-detect MySQL client
    mysql_paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe",
        r"C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysql.exe",
        r"D:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    ]
    # Also check PATH
    rc, out, _ = run_cmd("where mysql")
    if rc == 0:
        for line in out.splitlines():
            line = line.strip()
            if line.endswith("mysql.exe") and os.path.exists(line):
                mysql_paths.insert(0, line)
    mysql_client = None
    for mp in mysql_paths:
        if os.path.exists(mp):
            mysql_client = mp
            break

    if mysql_client:
        # Use MySQL CLI (handles multi-line SQL correctly)
        def run_mysql(sql_or_file, is_file=False):
            """Execute SQL against the database."""
            base_cmd = (
                f'"{mysql_client}" --default-character-set=utf8mb4 '
                f'-h {db_cfg["host"]} -P {db_cfg["port"]} '
                f'-u {db_cfg["user"]} -p{db_cfg["password"]}'
            )
            if is_file:
                cmd = f'{base_cmd} < "{sql_or_file}"'
            else:
                cmd = f'{base_cmd} -e "{sql_or_file}"'
            return run_cmd(cmd)

        try:
            # Step 1: Always run table creation (IF NOT EXISTS — safe to repeat)
            for fname in ["01_create_tables.sql", "03_views_subschema.sql"]:
                fpath = os.path.join(SQL_DIR, fname)
                if os.path.exists(fpath):
                    rc, _, err = run_mysql(fpath, is_file=True)
                    if rc != 0 and err and "already exists" not in err.lower():
                        warn(f"{fname}: {err[:80]}")

            # Step 2: Only run seed data if class table is empty (first run)
            rc, out, _ = run_mysql(
                f"SELECT COUNT(*) FROM {db_cfg['db']}.class;"
            )
            row_count = 0
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    row_count = int(line)
                    break

            seed_path = os.path.join(SQL_DIR, "02_seed_data.sql")
            if row_count == 0 and os.path.exists(seed_path):
                rc, _, err = run_mysql(seed_path, is_file=True)
                if rc != 0 and err and "already exists" not in err.lower():
                    warn(f"seed_data: {err[:80]}")
                ok(f"Database '{db_cfg['db']}' initialized with seed data")
            else:
                ok(f"Database '{db_cfg['db']}' already has data — skipping seed (data preserved)")

        except Exception as e:
            warn(f"DB init issue: {str(e)[:80]}")
    else:
        warn("MySQL client not found, skipping DB init")

    # ---- Step 5: Backend ----
    step(5, 6, "Starting Backend (FastAPI)...")
    os.chdir(BACKEND_DIR)

    # Launch backend in new window (use venv Python 3.13)
    backend_cmd = f'start "ZhiPi-Backend" cmd /k "cd /d {BACKEND_DIR} & echo Backend: http://localhost:8000 & {VENV_PYTHON} main.py"'
    subprocess.Popen(backend_cmd, shell=True)
    ok("Launching in new window...")

    # ---- Step 6: Frontend ----
    if MODE == "shared":
        # Build frontend and copy to backend for single-port serving
        step(6, 6, "Building Frontend (Production)...")
        os.chdir(FRONTEND_DIR)

        if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
            print("      Installing frontend deps (first run may take a while)...")
            rc, _, err = run_cmd("npm install")
            if rc != 0:
                fail(f"npm install failed: {err}")
                input("\n  Press Enter to exit...")
                sys.exit(1)

        print("      Building...")
        rc, out, err = run_cmd("npm run build")
        if rc != 0:
            fail(f"Build failed: {err[:200]}")
            input("\n  Press Enter to exit...")
            sys.exit(1)
        ok("Build complete")

        # Copy dist -> backend/frontend_dist
        dist_src = os.path.join(FRONTEND_DIR, "dist")
        dist_dst = os.path.join(BACKEND_DIR, "frontend_dist")
        if os.path.exists(dist_dst):
            shutil.rmtree(dist_dst)
        shutil.copytree(dist_src, dist_dst)
        ok("Frontend deployed to backend (single port 8000)")

        # Clean up old dev server leftovers
        for leftover in ["uploads", "test_ocr_baidu.py"]:
            lpath = os.path.join(BACKEND_DIR, leftover)
            if os.path.exists(lpath):
                if os.path.isdir(lpath):
                    shutil.rmtree(lpath)
                else:
                    os.remove(lpath)
    else:
        step(6, 6, "Starting Frontend (Vue3 Dev)...")
        os.chdir(FRONTEND_DIR)

        if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
            print("      Installing frontend deps (first run may take a while)...")
            rc, _, err = run_cmd("npm install")
            if rc != 0:
                fail(f"npm install failed: {err}")
                input("\n  Press Enter to exit...")
                sys.exit(1)

        # Launch frontend in new window
        frontend_cmd = f'start "ZhiPi-Frontend" cmd /k "cd /d {FRONTEND_DIR} & echo Frontend: http://localhost:5173 & npm run dev"'
        subprocess.Popen(frontend_cmd, shell=True)
        ok("Launching in new window...")

    # ---- Done ----
    print()
    print(c("bold", "  " + "-" * 50))
    print(c("bold", c("green", "  [ALL SERVICES STARTED SUCCESSFULLY!]")))
    print(c("bold", "  " + "-" * 50))
    print()
    if MODE == "shared":
        print(f"  {c('cyan', '访问地址 :')} {c('bold', 'http://localhost:8000')}")
        print(f"  {c('dim', '  （前端+后端统一端口，可直接用于内网穿透）')}")
    else:
        print(f"  {c('cyan', 'Frontend URL :')} http://localhost:5173")
        print(f"  {c('cyan', 'Backend URL  :')} http://localhost:8000")
    print(f"  {c('cyan', 'API Docs     :')} http://localhost:8000/docs")
    print()
    print(f"  {c('yellow', 'Demo Accounts:')}")
    print(f"    Teacher : {c('bold','T007')} / {c('bold','123456')}")
    print(f"    Student : {c('bold','S032')} / {c('bold','123456')}")
    print()
    print(f"  {c('dim', 'Close the popup windows to stop services.')}")
    print()

    # Wait for services to be ready
    print("  Waiting for services to be ready...", end="", flush=True)
    for i in range(10):
        time.sleep(1)
        print(".", end="", flush=True)
    print()

    if check_port(8000):
        ok("Backend is responding on port 8000")
    else:
        warn("Backend not yet ready (may still be starting)")

    if MODE != "shared":
        if check_port(5173):
            ok("Frontend is responding on port 5173")
        else:
            warn("Frontend not yet ready (may still be starting)")

    print()
    input("  Press Enter to exit this launcher...")


if __name__ == "__main__":
    main()
