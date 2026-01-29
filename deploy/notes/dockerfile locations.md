root@C1:/opt/l9# cd /opt/l9
find . -name "Dockerfile*" -type f 2>/dev/null | head -20  # Find all Dockerfiles
ls -la                                                      # Show repo structure
./services/symbolic_computation/Dockerfile
./runtime/Dockerfile
./mcp_memory/Dockerfile
./deploy/docker-production/Dockerfile.mcp-memory
./deploy/docker-production/Dockerfile.l9-api
./deploy/k8s/c1/Dockerfile.mcp-memory
./deploy/k8s/c1/Dockerfile
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
drwxr-xr-x  8 root root  4096 Jan 27 22:55 .git
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
