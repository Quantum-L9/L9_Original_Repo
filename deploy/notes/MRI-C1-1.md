cd /root                              # Start from root home or your normal user

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