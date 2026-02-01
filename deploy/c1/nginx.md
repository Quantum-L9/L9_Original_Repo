<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# approved

We’ll wire this so your Mac’s Cursor talks to `l9-mcp-memory` on C1 via nginx, with a clean env‑driven entrypoint.

Below are the concrete Phase 2–6 deliverables you can drop into the repo and onto C1.

***

## 1. Nginx config: expose `/memory/` → `l9-mcp-memory:9002`

Assumptions (based on your container list):

- `l9-nginx` and `l9-mcp-memory` are on the same Docker network.
- `l9-mcp-memory` container name is resolvable as `l9-mcp-memory` inside that network.
- `l9-nginx` already listens on `0.0.0.0:80`.


### 1.1 New nginx location block

Locate the existing nginx server config used by `l9-nginx`. In most L9‑style setups this will be one of:

- `/etc/nginx/conf.d/default.conf` (inside container)
- or a mounted file from the repo such as `infra/nginx/l9.conf` or `infra/nginx/default.conf`.

Inside the **existing** `server` block that listens on port 80 for C1 (do not create a new server), add:

```nginx
    # L9 MCP memory – exposed at /memory/
    location /memory/ {
        proxy_pass http://l9-mcp-memory:9002/;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

Notes:

- Using `l9-mcp-memory:9002` keeps all routing inside the Docker network, no host‑network coupling.
- The trailing slash on `proxy_pass` ensures `/memory/health` on C1 maps to `/health` on the memory service.


### 1.2 Reload on C1

On C1, once you’ve updated the config that `l9-nginx` mounts:

```bash
# Inside the l9-nginx container:
docker exec -it l9-nginx nginx -t
docker exec -it l9-nginx nginx -s reload
```

Quick sanity check from your Mac (replace `C1_HOST` with IP or DNS):

```bash
curl -v http://C1_HOST/memory/health
```

You should hit the memory service’s health endpoint via nginx.

***

## 2. Cursor memory client: env‑driven base URL

File: `agents/cursor/cursor_memory_client.py`

### 2.1 Add configuration block near the top

Right below imports, add:

```python
import os
from urllib.parse import urljoin

# Base URL resolution for L9 memory service.
# Priority:
#   1. L9_MEMORY_URL (explicit override)
#   2. http://l9-mcp-memory:9002 (Docker / C1 default)
#   3. http://localhost:9002 (last‑resort local dev)
DEFAULT_DOCKER_MEMORY_URL = "http://l9-mcp-memory:9002"
DEFAULT_LOCAL_MEMORY_URL = "http://localhost:9002"

def get_memory_base_url() -> str:
    explicit = os.environ.get("L9_MEMORY_URL")
    if explicit:
        return explicit.rstrip("/")

    # Simple heuristic: if running inside Docker (common markers),
    # prefer container name endpoint.
    if os.path.exists("/.dockerenv") or os.environ.get("L9_ENV") == "docker":
        return DEFAULT_DOCKER_MEMORY_URL

    return DEFAULT_LOCAL_MEMORY_URL

MEMORY_BASE_URL = get_memory_base_url()
```


### 2.2 Use `MEMORY_BASE_URL` for all requests

Wherever the client currently builds URLs (pseudo‑example):

```python
# OLD
url = f"http://127.0.0.1:9002/write"

# NEW
url = urljoin(MEMORY_BASE_URL + "/", "write")
```

Do the same for any `read`, `health`, or other endpoints:

```python
write_url = urljoin(MEMORY_BASE_URL + "/", "write")
read_url = urljoin(MEMORY_BASE_URL + "/", "read")
health_url = urljoin(MEMORY_BASE_URL + "/", "health")
```


### 2.3 Optional: log the effective URL in CLI mode

Inside the CLI `main()` (or equivalent entrypoint):

```python
def main() -> None:
    # ...
    if os.environ.get("L9_DEBUG_MEMORY_URL") == "1":
        print(f"[l9-cursor-memory] Using MEMORY_BASE_URL={MEMORY_BASE_URL}", flush=True)
    # continue with argument parsing + request logic
```

This makes it obvious what your Mac’s CLI is actually targeting.

***

## 3. Env config: `.env.example`

File: `.env.example` (or the primary env template in the repo)

Add a clearly documented section (do not change existing keys):

```env
# === L9 Memory Service (MCP) ===
# Default for Docker / C1 deployment: l9-mcp-memory is reachable inside the
# compose network at port 9002. This is what services INSIDE the cluster use.
L9_MEMORY_URL=http://l9-mcp-memory:9002

# When calling C1 FROM YOUR LAPTOP (Cursor on Mac) via nginx:
# Replace C1_HOST with your C1 IP or DNS name, e.g. http://c1.yourdomain.com
# Uncomment the next line locally if you want to override the default:
# L9_MEMORY_URL=http://C1_HOST/memory
```

This keeps Docker default stable while making the remote‑from‑Mac case one env change away.

***

## 4. Docs: Cursor + C1 workflow

File: `agents/cursor/README.md` (if it exists). If not, add a short section into the main `README.md`.

Suggested section:

```markdown
### Using Cursor Memory Against C1 From Your Laptop

Prereqs:

- C1 is running with `docker compose up -d` and all `l9-*` containers are healthy.
- `l9-nginx` is reachable on `http://C1_HOST` from your laptop.

1. Verify memory is exposed via nginx:

   ```bash
   curl -v http://C1_HOST/memory/health
```

2. On your laptop, point Cursor's memory client at C1:

```bash
export L9_MEMORY_URL="http://C1_HOST/memory"
```

3. Test a write via the Cursor memory client:

```bash
python3 agents/cursor/cursor_memory_client.py write \
  "Memory fix verification test - unique marker TEST123FIX" \
  --kind lesson
```

You should receive a success JSON response.
```

This documents exactly how you’ll run the test you mentioned.

***

## 5. Validation steps (C1 + Mac)

### On C1

1. Confirm containers:

   ```bash
   docker ps --format "table {{.Names}}\t{{.Ports}}"
```

2. Confirm nginx routes:

```bash
docker exec -it l9-nginx nginx -T | grep -A5 "location /memory/"
```

3. Health check:

```bash
curl -v http://localhost/memory/health
```


### On your Mac

1. Set the env var:

```bash
export L9_MEMORY_URL="http://C1_HOST/memory"
```

2. Run your original test:

```bash
python3 agents/cursor/cursor_memory_client.py write \
  "Memory fix verification test - unique marker TEST123FIX" \
  --kind lesson
```

3. If it still fails, run with debug:

```bash
L9_DEBUG_MEMORY_URL=1 \
python3 agents/cursor/cursor_memory_client.py write \
  "Memory fix verification test - unique marker TEST123FIX" \
  --kind lesson
```


You should see the effective `MEMORY_BASE_URL` printed and the JSON success payload from `l9-mcp-memory`.

If you paste the current `agents/cursor/cursor_memory_client.py` and the nginx config file that `l9-nginx` mounts, I can adapt the snippets above to your exact function names and layout so you can patch with zero manual merging.

