# Accessing VPS Observability Dashboards

## Current Problem

Grafana and Prometheus are bound to `127.0.0.1` (localhost only), so you can't access them from outside the VPS.

## Solution Options

### Option 1: SSH Port Forwarding (Recommended - Secure)

Access VPS Grafana from your Mac via SSH tunnel:

```bash
# Forward Grafana (port 3000)
ssh -L 3000:localhost:3000 root@157.180.73.53

# In another terminal, forward Prometheus (port 9090)
ssh -L 9090:localhost:9090 root@157.180.73.53

# Forward Jaeger (port 16686)
ssh -L 16686:localhost:16686 root@157.180.73.53
```

**Then access from your Mac:**
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- Jaeger: `http://localhost:16686`

**Pros:** Secure, no firewall changes, works immediately
**Cons:** Need SSH connection active

---

### Option 2: Expose Ports Publicly (With Auth)

Modify `docker-compose.yml` on VPS to bind to `0.0.0.0` instead of `127.0.0.1`:

```yaml
# Change from:
ports:
  - "127.0.0.1:${GRAFANA_PORT:-3000}:3000"

# To:
ports:
  - "0.0.0.0:${GRAFANA_PORT:-3000}:3000"
```

**Then access:**
- Grafana: `http://157.180.73.53:3000`
- Prometheus: `http://157.180.73.53:9090`

**⚠️ Security:** Make sure Grafana has strong password! Already configured:
- Username: `admin`
- Password: Set via `GRAFANA_PASSWORD` env var

**Pros:** Always accessible, no SSH needed
**Cons:** Exposed to internet (use strong password + firewall)

---

### Option 3: Reverse Proxy (Most Secure)

Use Caddy/Nginx to expose Grafana with:
- HTTPS (SSL)
- Authentication
- Domain name (e.g., `grafana.yourdomain.com`)

**Example Caddy config:**
```caddy
grafana.yourdomain.com {
    reverse_proxy localhost:3000
    basicauth {
        admin $2a$14$hashed_password_here
    }
}
```

**Pros:** Most secure, HTTPS, domain name
**Cons:** Requires domain + SSL setup

---

## Quick Setup: SSH Port Forwarding

**One-liner to forward all observability ports:**

```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 -L 16686:localhost:16686 root@157.180.73.53
```

**Then open in browser:**
- Grafana: `http://localhost:3000` (admin/admin)
- Prometheus: `http://localhost:9090`
- Jaeger: `http://localhost:16686`

---

## Verify VPS Services Are Running

```bash
# SSH into VPS
ssh root@157.180.73.53

# Check containers
docker-compose ps | grep -E "grafana|prometheus|jaeger"

# Check if ports are listening
netstat -tlnp | grep -E "3000|9090|16686"
```

---

## Recommended: Use SSH Port Forwarding

For now, **SSH port forwarding is safest** - no firewall changes, fully encrypted, works immediately.

Just run:
```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 root@157.180.73.53
```

Then access `http://localhost:3000` from your Mac - it will show VPS Grafana!

