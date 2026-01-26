# C1 Hetzner Firewall Configuration

## Required Firewall Rules

Apply these rules via Hetzner Console → Firewalls → firewall-1 (or create new)

### Inbound Rules

| Description    | Protocol | Port  | Source         | Priority |
| -------------- | -------- | ----- | -------------- | -------- |
| SSH            | TCP      | 22    | Any IPv4/IPv6  | 1        |
| ICMP (ping)    | ICMP     | -     | Any IPv4/IPv6  | 2        |
| HTTP           | TCP      | 80    | Any IPv4/IPv6  | 3        |
| HTTPS          | TCP      | 443   | Any IPv4/IPv6  | 4        |
| L9 API         | TCP      | 30080 | Any IPv4/IPv6  | 5        |
| MCP Memory     | TCP      | 30902 | Any IPv4/IPv6  | 6        |
| PostgreSQL     | TCP      | 30432 | Admin IPs only | 7        |
| Grafana        | TCP      | 30300 | Any IPv4/IPv6  | 8        |
| Neo4j Browser  | TCP      | 30474 | Any IPv4/IPv6  | 9        |
| Neo4j Bolt     | TCP      | 30687 | Any IPv4/IPv6  | 10       |
| Prometheus     | TCP      | 30909 | Any IPv4/IPv6  | 11       |
| Kubernetes API | TCP      | 6443  | Admin IPs only | 12       |

### Outbound Rules

| Description  | Protocol | Port | Destination |
| ------------ | -------- | ---- | ----------- | --------------- |
| All outbound | All      | All  | Any         | (default allow) |

---

## Hetzner Console Steps

1. Go to: https://console.hetzner.cloud
2. Select project: L9
3. Navigate to: Firewalls
4. Either:
   - Edit existing `firewall-1` (currently applied to L9)
   - Create new `firewall-c1` for C1 specifically

### To Create New Firewall for C1:

```
Name: firewall-c1
Rules:
  Inbound:
    - TCP 22 (SSH)
    - ICMP
    - TCP 80
    - TCP 443
    - TCP 30080 (L9 API)
    - TCP 30902 (MCP Memory)
    - TCP 30432 (PostgreSQL - restrict to admin IPs)
    - TCP 30300 (Grafana)
    - TCP 30474 (Neo4j Browser)
    - TCP 30687 (Neo4j Bolt)
    - TCP 30909 (Prometheus)
    - TCP 6443 (K8s API - restrict to your IP)
  Outbound:
    - Allow all
Apply to: C1
```

---

## Security Recommendations

### Production Hardening

1. **Restrict K8s API (6443)** to specific admin IPs only
2. **Restrict Neo4j ports** to VPN or specific IPs (contains graph data)
3. **Use TLS** - configure Let's Encrypt via cert-manager
4. **Change default passwords** in `c1-secrets.yaml`

### IP Restrictions (Optional)

For sensitive services, limit source IPs:

```
# Only allow your office/home IP
Source: 203.0.113.50/32  # Replace with your IP

# Or use VPN subnet
Source: 10.8.0.0/24  # WireGuard/OpenVPN subnet
```

---

## Quick Commands

### Check current firewall on server:

```bash
ssh root@46.62.243.82
iptables -L -n
```

### Test port accessibility:

```bash
# From your local machine
nc -zv 46.62.243.82 30080  # L9 API
nc -zv 46.62.243.82 30902  # MCP Memory
nc -zv 46.62.243.82 30432  # PostgreSQL
nc -zv 46.62.243.82 30300  # Grafana
nc -zv 46.62.243.82 30474  # Neo4j Browser
nc -zv 46.62.243.82 30687  # Neo4j Bolt
nc -zv 46.62.243.82 30909  # Prometheus
```

---

## Current firewall-1 Rules (L9 Server)

From screenshots, existing rules on firewall-1:

- TCP 22 (SSH)
- ICMP
- TCP 80 (HTTP)
- TCP 443 (HTTPS)
- TCP 9001

**Note:** firewall-1 is applied to L9 server. Create separate firewall-c1 for C1 to avoid conflicts.
