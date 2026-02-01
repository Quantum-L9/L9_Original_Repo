cd /root  # Stay in root’s home on C1

# 1) Describe the failing pods to see recent events
kubectl describe pod -n l9-c1 l9-api-676f564875-mkch7
kubectl describe pod -n l9-c1 l9-api-6bbf75674c-5nxmr
kubectl describe pod -n l9-c1 l9-mcp-memory-565c74b954-g49mt
kubectl describe pod -n l9-c1 l9-mcp-memory-c7678bf7f-w4tsm

# 2) Get recent logs for the crashing containers
kubectl logs -n l9-c1 l9-api-676f564875-mkch7 --tail=80
kubectl logs -n l9-c1 l9-api-6bbf75674c-5nxmr --tail=80
kubectl logs -n l9-c1 l9-mcp-memory-565c74b954-g49mt --tail=80
kubectl logs -n l9-c1 l9-mcp-memory-c7678bf7f-w4tsm --tail=80
