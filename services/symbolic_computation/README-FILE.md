# Symbolic Computation Module

> SymPy-based expression evaluation, code generation, and optimization for L9

## Quick Start

```bash
# From L9 root - run with main API
cd /Users/ib-mac/Projects/L9
python -c "from services.symbolic_computation import SymbolicComputation; print('OK')"

# Or via Docker isolated test container
cd services/symbolic_computation
docker build -t symtest .
docker run --rm symtest
```

## What This Module Does

| Capability                  | Description                                                                   |
| --------------------------- | ----------------------------------------------------------------------------- |
| **Expression Evaluation**   | Parse and evaluate SymPy expressions numerically (numpy/math/mpmath backends) |
| **Code Generation**         | Generate compilable C, Fortran, Cython, Python from symbolic expressions      |
| **Expression Optimization** | Simplify, factor, expand, CSE (common subexpression elimination)              |
| **Validation**              | Security checks to block dangerous expressions (`eval`, `exec`, imports)      |

## Architecture

```
services/symbolic_computation/
├── Dockerfile              # Test runner container (Python 3.11 + gcc/gfortran)
├── docker-compose.yml      # STANDALONE dev stack (NOT used in production)
├── requirements.txt        # Module-specific dependencies
├── api/
│   └── routes.py           # FastAPI endpoints at /symbolic/*
├── core/
│   ├── expression_evaluator.py   # Numerical evaluation
│   ├── code_generator.py         # C/Fortran/Cython generation
│   ├── optimizer.py              # Expression optimization
│   ├── validator.py              # Security validation
│   ├── cache_manager.py          # Result caching
│   └── metrics.py                # Performance metrics
└── tools/
    └── symbolic_tool.py    # L9 tool executor wrapper
```

## Wiring in L9

| Integration Point | Location                                                                           | Status        |
| ----------------- | ---------------------------------------------------------------------------------- | ------------- |
| API Router        | `api/server.py` → `/symbolic/*`                                                    | ✅ Active     |
| Tool Executors    | `runtime/l_tools.py` → `symbolic_compute`, `symbolic_codegen`, `symbolic_optimize` | ✅ Active     |
| Tool Registry     | `core/tools/registry_adapter.py`                                                   | ✅ Registered |

**SymPy is lazy-loaded** — API starts even if sympy not installed, returns error only if tools called.

---

## Testing Codegen and SymPy Built Code

### Option 1: Isolated Docker Container (Recommended for Codegen)

The Dockerfile includes gcc, g++, gfortran, and OpenBLAS for compiling generated code:

```bash
# Build test container with all compilers
cd /Users/ib-mac/Projects/L9/services/symbolic_computation
docker build -t l9-symtest .

# Run all tests
docker run --rm l9-symtest

# Run specific test
docker run --rm l9-symtest pytest tests/test_code_generator.py -v

# Interactive shell to test manually
docker run --rm -it l9-symtest bash
```

### Option 2: Local Python (Quick Tests)

```bash
# Ensure sympy installed
pip install sympy numpy

# Run from L9 root
cd /Users/ib-mac/Projects/L9
pytest tests/services/symbolic_computation/ -v

# With coverage
pytest tests/services/symbolic_computation/ --cov=services.symbolic_computation --cov-report=html
```

### Option 3: Via L9 API (Integration Test)

```bash
# Start L9 stack
docker-compose up -d

# Test evaluate endpoint
curl -X POST http://localhost:8000/symbolic/evaluate \
  -H "Content-Type: application/json" \
  -d '{"expression": "x**2 + sin(x)", "variables": {"x": 3.14}, "backend": "numpy"}'

# Test code generation
curl -X POST http://localhost:8000/symbolic/generate_code \
  -H "Content-Type: application/json" \
  -d '{"expression": "x**2 + y**2", "variables": ["x", "y"], "language": "C", "function_name": "compute_sum"}'

# Test optimization
curl -X POST http://localhost:8000/symbolic/optimize \
  -H "Content-Type: application/json" \
  -d '{"expression": "x**2 + 2*x*y + y**2", "strategies": ["factor"]}'
```

---

## Testing Generated C/Fortran Code

### Generate and Compile C Code

```bash
# Enter container with compilers
docker run --rm -it l9-symtest bash

# Inside container - generate C code
python3 << 'EOF'
from services.symbolic_computation.core.code_generator import CodeGenerator

gen = CodeGenerator()
result = gen.generate_code_sync(
    expr="x**2 + sin(y)",
    variables=["x", "y"],
    language="C",
    function_name="my_math_func"
)
print(result.source_code)

# Save to file
with open("/tmp/my_math_func.c", "w") as f:
    f.write(result.source_code)
EOF

# Compile the generated C code
cd /tmp
gcc -c my_math_func.c -o my_math_func.o -lm
echo "Compilation successful!"
```

### Generate and Compile Fortran Code

```bash
# Inside container
python3 << 'EOF'
from services.symbolic_computation.core.code_generator import CodeGenerator

gen = CodeGenerator()
result = gen.generate_code_sync(
    expr="x**3 + y**3 + z**3",
    variables=["x", "y", "z"],
    language="Fortran",
    function_name="cube_sum"
)
print(result.source_code)

with open("/tmp/cube_sum.f90", "w") as f:
    f.write(result.source_code)
EOF

# Compile Fortran
gfortran -c /tmp/cube_sum.f90 -o /tmp/cube_sum.o
echo "Fortran compilation successful!"
```

---

## API Endpoints

| Endpoint                  | Method | Purpose                           |
| ------------------------- | ------ | --------------------------------- |
| `/symbolic/evaluate`      | POST   | Evaluate expression numerically   |
| `/symbolic/generate_code` | POST   | Generate C/Fortran/Python code    |
| `/symbolic/optimize`      | POST   | Simplify/factor/expand expression |
| `/symbolic/validate`      | POST   | Check expression safety           |
| `/symbolic/metrics`       | GET    | Performance metrics summary       |
| `/symbolic/health`        | GET    | Service health check              |
| `/symbolic/cache/stats`   | GET    | Cache hit/miss stats              |
| `/symbolic/cache/clear`   | POST   | Clear expression cache            |

---

## Test Files

| File                           | Coverage Target | Purpose                                 |
| ------------------------------ | --------------- | --------------------------------------- |
| `test_expression_evaluator.py` | ≥85%            | Numerical evaluation, backends, caching |
| `test_code_generator.py`       | ≥85%            | C/Fortran/Cython generation             |
| `test_validator.py`            | ≥90%            | Security validation                     |
| `test_integration.py`          | ≥80%            | End-to-end workflows                    |

---

## Backends

| Backend  | Speed   | Precision | Use Case                     |
| -------- | ------- | --------- | ---------------------------- |
| `numpy`  | Fast    | Float64   | Default, array operations    |
| `math`   | Medium  | Float64   | Scalar, no numpy dependency  |
| `mpmath` | Slow    | Arbitrary | High-precision scientific    |
| `sympy`  | Slowest | Exact     | Symbolic (no numerical eval) |

---

## Code Languages

| Language  | Use Case                                 | Compiler Required |
| --------- | ---------------------------------------- | ----------------- |
| `C`       | High-performance, embedded               | gcc               |
| `Fortran` | Scientific computing, legacy integration | gfortran          |
| `Cython`  | Python extension modules                 | cython + gcc      |
| `Python`  | Debugging, prototyping                   | None              |

---

## Important Notes

1. **`docker-compose.yml` in this folder is STANDALONE** — NOT used by root L9 docker-compose
2. **SymPy is in main requirements.txt** — No separate install needed for L9 deployment
3. **Lazy loading** — If sympy fails to import, API still starts, tools return error gracefully
4. **Container has compilers** — gcc, g++, gfortran, OpenBLAS for testing codegen output

---

## Troubleshooting

### "sympy not installed" error

```bash
pip install sympy>=1.12
```

### Generated code won't compile

Ensure you're in the Docker container with compilers:

```bash
docker run --rm -it l9-symtest bash
which gcc gfortran  # Should show paths
```

### Cache issues

```bash
curl -X POST http://localhost:8000/symbolic/cache/clear
```

---

## License

Part of L9 Secure AI OS — Internal use only
