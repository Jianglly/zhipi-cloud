# -*- coding: utf-8 -*-
"""
ZhiPi Cloud - One-Click Deploy: Server + Cloudflare Tunnel
Double-click deploy.bat from desktop to launch everything.
Replaces unstable natapp with permanent Cloudflare Tunnel.
"""
import subprocess
import sys
import os
import time
import socket
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-frontend")
SQL_DIR = os.path.join(PROJECT_ROOT, "zhipi-cloud", "zhipi-database", "sql")
VENV_PYTHON = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
CF_EXE = os.path.join(PROJECT_ROOT, "cloudflared.exe")
CF_CONFIG = os.path.join(PROJECT_ROOT, "cloudflared-config.yml")
DOMAIN = "zhipicloud.top"
TUNNEL_NAME = "zhipi-cloud"
DB_PORT = 3307


def c(code, text):
    colors = {
        "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
        "blue": "\033[94m", "cyan": "\033[96m", "bold": "\033[1m",
        "dim": "\033[2m", "reset": "\033[0m",
    }
    return f"{colors.get(code, '')}{text}{colors['reset']}"


def check_port(port, timeout=1):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_cmd(cmd, capture=True):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture, text=True,
            encoding="utf-8", errors="replace"
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def banner():
    print(c("bold", "\n" + "=" * 54))
    print(c("bold", c("cyan", "    ZhiPi Cloud - One-Click Deploy")))
    print(c("bold", "    Server + Cloudflare Tunnel"))
    print(c("bold", c("dim", f"    https://{DOMAIN}")))
    print(c("bold", "=" * 54))


def step(msg):
    print(f"\n  {c('cyan', '>>')} {c('bold', msg)}")


def ok(msg="OK"):
    print(f"      {c('green', '[OK]')} {msg}")


def warn(msg=""):
    print(f"      {c('yellow', '[!]')} {msg}")


def die(msg=""):
    print(f"      {c('red', '[X]')} {msg}")
    input("\n  Press Enter to exit...")
    sys.exit(1)


# ============================================================
#  MAIN
# ============================================================
def main():
    os.system("")
    banner()

    # ── 1. MySQL ──
    step("1/6  Checking MySQL...")
    if check_port(DB_PORT):
        ok(f"MySQL running on :{DB_PORT}")
    else:
        for svc in ["MySQL80", "MySQL"]:
            rc, out, _ = run_cmd(f"net start {svc}")
            time.sleep(2)
            if check_port(DB_PORT):
                ok(f"MySQL started ({svc})")
                break
        else:
            warn("Can't start MySQL - trying anyway...")

    # ── 2. Read .env ──
    step("2/6  Reading config...")
    db_cfg = {"host": "localhost", "port": DB_PORT, "user": "root", "password": "", "db": "zhipi_cloud"}
    env_path = os.path.join(BACKEND_DIR, ".env")
    if not os.path.exists(env_path):
        env_example = os.path.join(BACKEND_DIR, ".env.example")
        if os.path.exists(env_example):
            shutil.copy(env_example, env_path)
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k == "DB_PASSWORD": db_cfg["password"] = v
                    elif k == "DB_PORT": db_cfg["port"] = int(v)
    ok(f"DB: {db_cfg['user']}@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['db']}")

    # ── 3. DB Init ──
    step("3/6  Initializing database...")
    mysql_paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe",
        r"D:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    ]
    rc, out, _ = run_cmd("where mysql")
    if rc == 0:
        for line in out.splitlines():
            line = line.strip()
            if line.endswith("mysql.exe") and os.path.exists(line):
                mysql_paths.insert(0, line)
    mysql_exe = next((p for p in mysql_paths if os.path.exists(p)), None)

    if mysql_exe:
        def run_mysql(sql_or_file, is_file=False):
            base = f'"{mysql_exe}" --default-character-set=utf8mb4 -h {db_cfg["host"]} -P {db_cfg["port"]} -u {db_cfg["user"]} -p{db_cfg["password"]}'
            cmd = f'{base} < "{sql_or_file}"' if is_file else f'{base} -e "{sql_or_file}"'
            return run_cmd(cmd)

        # Table structure
        for fn in ["01_create_tables.sql", "03_views_subschema.sql"]:
            fp = os.path.join(SQL_DIR, fn)
            if os.path.exists(fp):
                run_mysql(fp, is_file=True)

        # Seed data (only once)
        rc, out, _ = run_mysql(f"SELECT COUNT(*) FROM {db_cfg['db']}.class;")
        count = 0
        for line_ in out.splitlines():
            if line_.strip().isdigit():
                count = int(line_.strip())
                break
        seed_path = os.path.join(SQL_DIR, "02_seed_data.sql")
        if count == 0 and os.path.exists(seed_path):
            run_mysql(seed_path, is_file=True)
            ok("Database initialized (first run)")
        else:
            ok("Database ready (data preserved)")
    else:
        warn("mysql.exe not found, skipping DB init")

    # ── 4. Build & Start Backend ──
    if check_port(8000):
        step("4/6  Server already running on :8000")
        ok("Skipping build - reusing existing server")
    else:
        step("4/6  Building frontend + starting server...")
        if not os.path.exists(FRONTEND_DIR):
            die("Frontend directory not found")
        os.chdir(FRONTEND_DIR)
        if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
            print("      Installing dependencies...")
            rc, _, err = run_cmd("npm install")
            if rc != 0:
                die(f"npm install failed: {err[:100]}")
        rc, _, err = run_cmd("npm run build")
        if rc != 0:
            die(f"Build failed: {err[:150]}")
        # Vite config 已配置 outDir 直接输出到 backend/frontend_dist，无需手动拷贝

        os.chdir(BACKEND_DIR)
        subprocess.Popen(
            f'start "ZhiPi-8000" cmd /k "cd /d {BACKEND_DIR} & title ZhiPi Server :8000 & {VENV_PYTHON} main.py"',
            shell=True
        )
        ok("Build done, backend launching...")

        print("      Waiting for server...", end="", flush=True)
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
            if check_port(8000):
                break
        print()
        if check_port(8000):
            ok("Server ready on http://localhost:8000")
        else:
            die("Server did not start in 30s - check backend window for errors")

    # ── 5. Cloudflare Tunnel ──
    step("5/6  Starting Cloudflare Tunnel...")
    if not os.path.exists(CF_EXE):
        die("cloudflared.exe not found! Re-run setup or download manually.")

    # Check if tunnel credentials file exists (UUID-named, not tunnel name)
    cred_dir = os.path.expanduser("~/.cloudflared")
    cred_file = None
    if os.path.isdir(cred_dir):
        for f in os.listdir(cred_dir):
            if f.endswith(".json") and f != "cert.pem":
                cred_file = os.path.join(cred_dir, f)
                break

    if not cred_file:
        print()
        print(f"      {c('yellow', 'First-time setup needed!')}")
        print(f"      Please follow the ONE-TIME steps below:")
        print()
        print(f"      {c('bold', 'Step A')} Open a NEW command window and run:")
        print(f"              cd \"{PROJECT_ROOT}\"")
        print(f"              cloudflared.exe tunnel login")
        print(f"      This will open a browser to authorize.")
        print()
        print(f"      {c('bold', 'Step B')} After login, create tunnel:")
        print(f"              cloudflared.exe tunnel create {TUNNEL_NAME}")
        print()
        print(f"      {c('bold', 'Step C')} Configure DNS route:")
        print(f"              cloudflared.exe tunnel route dns {TUNNEL_NAME} {DOMAIN}")
        print(f"              cloudflared.exe tunnel route dns {TUNNEL_NAME} www.{DOMAIN}")
        print()
        print(f"      Then re-run this script (deploy.bat).")
        input("\n  Press Enter to exit...")
        sys.exit(0)

    # Launch cloudflared tunnel
    subprocess.Popen(
        f'start "Cloudflare-Tunnel" cmd /k "cd /d {PROJECT_ROOT} & title CF Tunnel - https://{DOMAIN} & cloudflared.exe tunnel --config "{CF_CONFIG}" run {TUNNEL_NAME}"',
        shell=True
    )
    time.sleep(3)
    ok(f"Tunnel launched -> https://{DOMAIN}")

    # ── 6. Done ──
    print()
    print("  " + "-" * 50)
    print(c("bold", c("green", "  [ ALL DONE ]")))
    print("  " + "-" * 50)
    print()
    print(f"  Local   : {c('bold', 'http://localhost:8000')}")
    print(f"  Public  : {c('bold', c('green', f'https://{DOMAIN}'))}")
    print(f"  API     : {c('dim', 'http://localhost:8000/docs')}")
    print()
    print(f"  Share this URL with others:")
    print(f"       {c('bold', c('cyan', f'https://{DOMAIN}'))}")
    print()
    print(f"  {c('dim', 'Teacher: T007/123456   Student: S032/123456')}")
    print()
    input("  Press Enter to close this window...")


if __name__ == "__main__":
    main()
