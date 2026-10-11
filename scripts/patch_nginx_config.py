#!/usr/bin/env python3
"""
Aegis-Quant Nginx Configuration Patcher for Hostinger VPS.
Finds all active Nginx configuration files (including SSL port 443 and port 80),
and ensures:
  1. location /           -> http://127.0.0.1:3000  (Next.js modern UI)
  2. location /api/       -> http://127.0.0.1:8888  (FastAPI quant engine)
  3. location /ws         -> http://127.0.0.1:8888  (FastAPI websockets)
Backs up original configs before modifying and validates with 'nginx -t'.
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path

NGINX_DIRS = [
    Path("/etc/nginx/sites-enabled"),
    Path("/etc/nginx/sites-available"),
    Path("/etc/nginx/conf.d"),
]

API_BLOCK = """
    # Aegis-Quant Backend APIs
    location /api/ {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Aegis-Quant WebSockets
    location /ws {
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
    }
"""

def patch_file(file_path: Path) -> bool:
    content = file_path.read_text(encoding="utf-8")
    original = content
    modified = False

    # Check if this file proxies to 8888 or defines server block
    if "8888" not in content and "server" not in content:
        return False

    # 1. Update location / to 3000 if it proxies to 8888
    # Match location / { ... proxy_pass http://127.0.0.1:8888 ... }
    def repl_loc_root(match):
        block = match.group(0)
        # Replace 8888 with 3000 in proxy_pass
        new_block = re.sub(r'proxy_pass\s+http://(127\.0\.0\.1|localhost):8888', r'proxy_pass http://127.0.0.1:3000', block)
        return new_block

    # Look for location / { ... }
    loc_pattern = re.compile(r'location\s+/\s*\{[^}]*proxy_pass\s+http://(127\.0\.0\.1|localhost):8888[^}]*\}', re.DOTALL)
    if loc_pattern.search(content):
        content = loc_pattern.sub(repl_loc_root, content)
        modified = True

    # 2. If location / was modified or if server block has 3000, ensure /api/ and /ws are present
    if "127.0.0.1:3000" in content:
        # Check if location /api/ is missing
        if "location /api/" not in content and "location /api" not in content:
            # Insert API_BLOCK before 'location /'
            content = content.replace("location /", f"{API_BLOCK}\n    location /", 1)
            modified = True

    if modified and content != original:
        backup = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, backup)
        file_path.write_text(content, encoding="utf-8")
        print(f"✓ Patched {file_path} (backup at {backup})")
        return True

    return False

def main():
    print("==================================================")
    print("Scanning Nginx configurations on Hostinger VPS...")
    print("==================================================")

    modified_any = False
    for nginx_dir in NGINX_DIRS:
        if not nginx_dir.exists():
            continue
        for conf_file in nginx_dir.glob("*"):
            if conf_file.is_file() and not conf_file.name.endswith(".bak"):
                try:
                    if patch_file(conf_file):
                        modified_any = True
                except Exception as e:
                    print(f"Notice reading {conf_file}: {e}")

    # Also check /etc/nginx/nginx.conf
    nginx_conf = Path("/etc/nginx/nginx.conf")
    if nginx_conf.exists():
        if patch_file(nginx_conf):
            modified_any = True

    print("--------------------------------------------------")
    print("Testing Nginx configuration syntax ('nginx -t')...")
    res = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

    if res.returncode == 0:
        print("Reloading Nginx...")
        subprocess.run(["systemctl", "reload", "nginx"])
        print("✅ SUCCESS: Nginx reloaded! Next.js is now serving port 443 & 80!")
    else:
        print("❌ ERROR: Nginx configuration test failed! Please check output above.")

if __name__ == "__main__":
    main()
