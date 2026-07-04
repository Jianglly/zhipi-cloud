# -*- coding: utf-8 -*-
"""Check if database is initialized. Exit 0 = ready, 1 = not ready."""
import sys, os

backend_dir = os.path.join(os.path.dirname(__file__), '..', 'zhipi-cloud', 'zhipi-backend')
backend_dir = os.path.abspath(backend_dir)
sys.path.insert(0, backend_dir)

try:
    import pymysql

    env = {}
    env_path = os.path.join(backend_dir, '.env')
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()

    conn = pymysql.connect(
        host=env.get('DB_HOST', 'localhost'),
        port=int(env.get('DB_PORT', '3306')),
        user=env['DB_USER'],
        password=env['DB_PASSWORD'],
        database=env.get('DB_NAME', 'zhipi_cloud'),
        charset='utf8mb4',
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM admin')
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    if count > 0:
        print('READY')
        sys.exit(0)
    else:
        print('EMPTY')
        sys.exit(1)
except Exception:
    print('MISSING')
    sys.exit(1)
