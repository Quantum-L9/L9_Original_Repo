root@C1:~# cd /root                              # Start from root home or your normal user

echo "=== SYSTEM INFO ==="
hostnamectl
echo "----"
cat /etc/os-release
echo "----"
free -h
df -h /

echo "=== DOCKER STATE ==="
docker version || echo "Docker missing"
echo "----"
docker ps -a
echo "----"
docker images | head -20

echo "=== K3S / KUBERNETES ==="
which kubectl || echo "kubectl missing"
echo "----"
kubectl get nodes -o wide 2>/dev/null || echo "kubectl cannot talk to cluster"
echo "----"
kubectl get pods -A 2>/dev/null || echo "no pods or no access"

echo "=== L9 DIRECTORIES ==="
ls -la /opt
ls -la /opt/l9 2>/dev/null || echo "/opt/l9 missing"
ls -la /opt/l9-build 2>/dev/null || echo "/opt/l9-build missing"
ls -la /opt/l9-build/L9 2>/dev/null || echo "/opt/l9-build/L9 missing"

if [ -d /opt/l9-build/L9 ]; then
  cd /opt/l9-build/L9
  echo "=== GIT STATE (C1 build repo) ==="
  git remote -v
  git status
  echo "HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
fi
=== SYSTEM INFO ===
 Static hostname: C1
       Icon name: computer-vm
         Chassis: vm 🖴
      Machine ID: 7343fe7e7d2241538f74956b71567e2f
         Boot ID: 0a314a6ea7cb4b2195293270bfd229e5
  Virtualization: kvm
Operating System: Ubuntu 24.04.3 LTS              
          Kernel: Linux 6.8.0-90-generic
    Architecture: x86-64
 Hardware Vendor: Hetzner
  Hardware Model: vServer
Firmware Version: 20171111
   Firmware Date: Sat 2017-11-11
    Firmware Age: 8y 2month 2w 3d                 
----
PRETTY_NAME="Ubuntu 24.04.3 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.3 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
----
               total        used        free      shared  buff/cache   available
Mem:           7.6Gi       3.8Gi       2.0Gi        20Mi       2.1Gi       3.8Gi
Swap:             0B          0B          0B
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       150G   83G   62G  58% /
=== DOCKER STATE ===
Client:
 Version:           28.2.2
 API version:       1.50
 Go version:        go1.23.1
 Git commit:        28.2.2-0ubuntu1~24.04.1
 Built:             Wed Sep 10 14:16:39 2025
 OS/Arch:           linux/amd64
 Context:           default

Server:
 Engine:
  Version:          28.2.2
  API version:      1.50 (minimum version 1.24)
  Go version:       go1.23.1
  Git commit:       28.2.2-0ubuntu1~24.04.1
  Built:            Wed Sep 10 14:16:39 2025
  OS/Arch:          linux/amd64
  Experimental:     false
 containerd:
  Version:          1.7.28
  GitCommit:        
 runc:
  Version:          1.3.3-0ubuntu1~24.04.3
  GitCommit:        
 docker-init:
  Version:          0.19.0
  GitCommit:        
----
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
----
REPOSITORY      TAG         IMAGE ID       CREATED        SIZE
l9-mcp-memory   latest      4fe7e27a89c3   24 hours ago   8.04GB
l9-mcp-memory   logfix      4fe7e27a89c3   24 hours ago   8.04GB
l9-api          latest      6e63b748dc77   24 hours ago   8.05GB
<none>          <none>      79602fa83bb8   24 hours ago   8.04GB
<none>          <none>      5f4b01539681   24 hours ago   12.6GB
<none>          <none>      48f1a42f8e41   24 hours ago   8.03GB
<none>          <none>      f774debc18ca   24 hours ago   12.6GB
<none>          <none>      4ef24c3c47ee   24 hours ago   8.02GB
python          3.12-slim   c78a70d7588f   2 weeks ago    119MB
=== K3S / KUBERNETES ===
/usr/local/bin/kubectl
----
NAME   STATUS   ROLES           AGE    VERSION        INTERNAL-IP    EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION     CONTAINER-RUNTIME
c1     Ready    control-plane   5d2h   v1.34.3+k3s1   46.62.243.82   <none>        Ubuntu 24.04.3 LTS   6.8.0-90-generic   containerd://2.1.5-k3s1
----
NAMESPACE     NAME                                      READY   STATUS                   RESTARTS          AGE
kube-system   coredns-7f496c8d7d-7fdwv                  1/1     Running                  0                 5d2h
kube-system   helm-install-traefik-crd-kv8lh            0/1     Completed                0                 5d2h
kube-system   helm-install-traefik-nwl26                0/1     Completed                1                 5d2h
kube-system   local-path-provisioner-578895bd58-7vbt6   1/1     Running                  0                 5d2h
kube-system   metrics-server-7b9c9c4b9c-nnb6j           1/1     Running                  0                 5d2h
kube-system   svclb-traefik-28b4f6ce-28dl4              2/2     Running                  0                 5d2h
kube-system   traefik-6f5f87584-gpd7f                   1/1     Running                  0                 5d2h
l9-c1         grafana-58bccd57bd-4gbmh                  1/1     Running                  0                 24h
l9-c1         grafana-58bccd57bd-ww6h6                  0/1     Completed                0                 5d2h
l9-c1         l9-api-676f564875-mkch7                   0/1     Running                  266 (30s ago)     23h
l9-c1         l9-api-6bbf75674c-5nxmr                   0/1     Running                  253 (3m43s ago)   23h
l9-c1         l9-api-7cf956bfff-7jwln                   0/1     Completed                0                 2d6h
l9-c1         l9-api-8bf75b966-p88gc                    0/1     ContainerStatusUnknown   334 (24h ago)     2d6h
l9-c1         l9-mcp-memory-565c74b954-g49mt            0/1     CrashLoopBackOff         18 (4m14s ago)    71m
l9-c1         l9-mcp-memory-754f97dcd-8c6mt             0/1     Completed                0                 2d13h
l9-c1         l9-mcp-memory-c7678bf7f-w4tsm             0/1     CrashLoopBackOff         279 (2m15s ago)   23h
l9-c1         l9-neo4j-0                                1/1     Running                  0                 24h
l9-c1         l9-postgres-0                             1/1     Running                  0                 24h
l9-c1         l9-redis-5b48f489bf-4xc5q                 0/1     Completed                0                 5d2h
l9-c1         l9-redis-5b48f489bf-fh9hv                 1/1     Running                  0                 24h
l9-c1         prometheus-57764b444b-5dkml               1/1     Running                  0                 24h
l9-c1         prometheus-57764b444b-7drtd               0/1     Completed                0                 5d2h
=== L9 DIRECTORIES ===
total 20
drwxr-xr-x  5 root root 4096 Jan 22 20:56 .
drwxr-xr-x 23 root root 4096 Jan 22 20:23 ..
drwx--x--x  4 root root 4096 Jan 22 20:51 containerd
drwxr-xr-x 54 root root 4096 Jan 26 22:25 l9
drwxr-xr-x  2 root root 4096 Jan 22 20:24 l9-k8s
total 592
drwxr-xr-x 54 root root  4096 Jan 26 22:25 .
drwxr-xr-x  5 root root  4096 Jan 22 20:56 ..
drwxr-xr-x  3 root root  4096 Jan 26 22:25 adapters
drwxr-xr-x  6 root root  4096 Jan 26 22:25 agents
drwxr-xr-x  7 root root  4096 Jan 26 22:25 api
drwxr-xr-x  5 root root  4096 Jan 22 20:56 _archived
drwxr-xr-x  3 root root  4096 Jan 26 22:25 .backup
-rw-r--r--  1 root root   652 Jan 24 22:53 .bandit
drwxr-xr-x  3 root root  4096 Jan 26 22:25 ci
drwxr-xr-x  2 root root  4096 Jan 26 22:25 clients
-rw-r--r--  1 root root  1751 Jan 26 22:25 codecov.yml
drwxr-xr-x  4 root root  4096 Jan 26 22:25 codegenagent
-rw-r--r--  1 root root  2233 Jan 26 22:25 coderabbit.yaml
drwxr-xr-x  2 root root  4096 Jan 26 22:25 collaborative_cells
drwxr-xr-x  9 root root  4096 Jan 26 22:25 config
-rw-r--r--  1 root root  4216 Jan 26 22:25 conftest.py
-rw-r--r--  1 root root 11914 Jan 26 22:25 CONTAINER_LOADING_DIAGNOSIS.md
drwxr-xr-x 39 root root  4096 Jan 26 22:25 core
drwxr-xr-x  3 root root  4096 Jan 26 22:25 current_work
lrwxrwxrwx  1 root root    54 Jan 22 20:56 .cursor-commands -> '/Users/ib-mac/Dropbox/Cursor Governance/GlobalCommands'
-rw-r--r--  1 root root   218 Jan 26 22:25 .cursorignore
lrwxrwxrwx  1 root root    60 Jan 22 20:56 .cursorrules -> '/Users/ib-mac/Dropbox/Cursor Governance/GlobalCommands/rules'
-rw-r--r--  1 root root  1779 Jan 26 22:25 .datree-policy.yaml
drwxr-xr-x  6 root root  4096 Jan 26 22:25 deploy
drwxr-xr-x  3 root root  4096 Jan 26 22:25 dev
drwxr-xr-x  2 root root  4096 Jan 26 22:25 docker
-rw-r--r--  1 root root   964 Jan 22 20:56 docker-compose.override.yml.example
-rw-r--r--  1 root root  8017 Jan 26 22:25 docker-compose-README.md
-rw-r--r--  1 root root 12322 Jan 26 22:25 docker-compose.yml
-rw-r--r--  1 root root   438 Jan 26 22:25 .dockerignore
-rw-r--r--  1 root root  6046 Jan 26 22:25 DOCKER_QUICK_START.md
drwxr-xr-x  4 root root  4096 Jan 26 22:25 docs
drwxr-xr-x  5 root root  4096 Jan 26 22:25 domain_tensor_bridge
-rw-r--r--  1 root root  9225 Jan 26 22:25 DORA_BLOCK_ROOT_CAUSE_ANALYSIS.md
-rw-r--r--  1 root root   554 Jan 26 22:25 dora_complete_injection_report.json
-rw-r--r--  1 root root   299 Jan 26 22:25 dora_validation_report.json
-rw-r--r--  1 root root   458 Jan 24 22:53 .editorconfig
drwxr-xr-x  2 root root  4096 Jan 26 22:25 email_agent
-rw-r--r--  1 root root  6256 Jan 26 22:25 .env.docker
-rw-r--r--  1 root root  5047 Jan 24 22:53 .env.example
drwxr-xr-x  2 root root  4096 Jan 26 22:25 examples
-rw-r--r--  1 root root 55366 Jan 26 22:25 gap-analysis-memory.md
drwxr-xr-x  2 root root  4096 Jan 26 22:25 .gemini
drwxr-xr-x  8 root root  4096 Jan 26 23:12 .git
drwxr-xr-x  4 root root  4096 Jan 26 22:25 .github
-rw-r--r--  1 root root  2317 Jan 26 22:25 .gitignore
-rw-r--r--  1 root root   224 Jan 22 20:56 .gitleaksignore
-rw-r--r--  1 root root  2332 Jan 25 16:21 .gitleaks.toml
drwxr-xr-x  3 root root  4096 Jan 22 20:56 grafana
drwxr-xr-x  2 root root  4096 Jan 26 22:25 graph_adapter
-rw-r--r--  1 root root    21 Jan 22 20:56 __init__.py
drwxr-xr-x  2 root root  4096 Jan 26 22:25 ir_engine
-rw-r--r--  1 root root    71 Jan 26 22:25 L9.code-workspace
drwxr-xr-x  2 root root  4096 Jan 26 22:25 langgraph
drwxr-xr-x  2 root root  4096 Jan 26 22:25 local_dashboard
drwxr-xr-x  3 root root  4096 Jan 26 22:25 mac_agent
-rw-r--r--  1 root root  8795 Jan 26 22:25 Makefile
drwxr-xr-x  7 root root  4096 Jan 26 22:25 mcp_memory
drwxr-xr-x  5 root root  4096 Jan 26 23:11 memory
drwxr-xr-x  2 root root  4096 Jan 26 22:25 migrations
-rw-r--r--  1 root root     0 Jan 22 20:56 .migrations_applied
drwxr-xr-x  2 root root  4096 Jan 26 22:25 motifs
drwxr-xr-x  2 root root  4096 Jan 22 20:56 ops
drwxr-xr-x  2 root root  4096 Jan 26 22:25 orchestration
drwxr-xr-x 11 root root  4096 Jan 26 22:25 orchestrators
-rw-r--r--  1 root root  2846 Jan 26 22:25 .pre-commit-config.yaml
drwxr-xr-x  4 root root  4096 Jan 22 20:56 private
-rw-r--r--  1 root root   930 Jan 26 22:25 pr.md
drwxr-xr-x  6 root root  4096 Jan 26 22:25 prompts
-rw-r--r--  1 root root  3415 Jan 26 22:25 pyproject.toml
-rw-r--r--  1 root root   422 Jan 26 22:25 pytest.ini
drwxr-xr-x  6 root root  4096 Jan 26 22:25 readme
-rw-r--r--  1 root root 23894 Jan 26 22:25 README.md
drwxr-xr-x  2 root root  4096 Jan 26 22:25 .refactor-config
drwxr-xr-x  2 root root  4096 Jan 26 22:25 .refactor-reports
drwxr-xr-x  6 root root  4096 Jan 26 22:25 reports
-rw-r--r--  1 root root  3049 Jan 26 22:25 requirements-docker.txt
-rw-r--r--  1 root root  1760 Jan 26 22:25 requirements.txt
-rw-r--r--  1 root root  5512 Jan 26 22:25 ruff.toml
-rw-r--r--  1 root root  1660 Jan 22 20:56 RUNBOOK.md
drwxr-xr-x  2 root root  4096 Jan 26 22:25 runtime
drwxr-xr-x 20 root root  4096 Jan 26 22:25 scripts
drwxr-xr-x  2 root root  4096 Jan 26 22:25 .sec
-rw-r--r--  1 root root  2123 Jan 26 22:25 SECURITY.md
drwxr-xr-x  4 root root  4096 Jan 26 22:25 services
drwxr-xr-x  2 root root  4096 Jan 26 22:25 simulation
-rw-r--r--  1 root root   510 Jan 24 22:53 sonar-project.properties
-rw-r--r--  1 root root   819 Jan 26 22:25 .suite6-config.json
-rw-r--r--  1 root root  9249 Jan 26 22:25 TECHNICAL_DEBT_CLEANUP_PR.md
drwxr-xr-x  2 root root  4096 Jan 26 22:25 telemetry
-rw-r--r--  1 root root     0 Jan 22 20:56 test
drwxr-xr-x 35 root root  4096 Jan 26 22:25 tests
-rw-r--r--  1 root root  8688 Jan 26 22:25 TODO-AB-Testing-Framework.md
-rw-r--r--  1 root root  6624 Jan 26 22:25 TODO-Compile-Chat-Transcripts.md
-rw-r--r--  1 root root 33133 Jan 26 22:25 TODO.md
-rw-r--r--  1 root root  3365 Jan 26 22:25 TODO-Research.md
-rw-r--r--  1 root root  3737 Jan 26 22:25 TODO-Update-Extractors.md
drwxr-xr-x  6 root root  4096 Jan 26 22:25 tools
-rw-r--r--  1 root root   520 Jan 26 22:25 VPS-Commands.md
-rw-r--r--  1 root root     0 Jan 22 20:56 .vultureignore
drwxr-xr-x  2 root root  4096 Jan 26 22:25 workers
drwxr-xr-x  5 root root  4096 Jan 26 22:25 workflows
-rw-r--r--  1 root root 10965 Jan 26 22:25 workflow_state.md
drwxr-xr-x  4 root root  4096 Jan 26 22:25 world_model
/opt/l9-build missing
/opt/l9-build/L9 missing
root@C1:~# 