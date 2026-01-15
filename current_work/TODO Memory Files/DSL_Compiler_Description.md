# DSL Compiler - Markdown to FOL JSON

## Purpose:
Compile markdown governance rules written in natural language or FOL into machine-readable JSON.

## Example Input:
```md
∀x. Agent(x) → DefaultAgent(x) = Mack
```

## Compiled Output:
```json
{
  "rule_id": "R001",
  "logic": "FORALL x (Agent(x) => DefaultAgent(x) = Mack)",
  "type": "hardgate",
  "enforced_by": "Governance Kernel v2.0"
}
```

## Usage:
Drop `.md` files with rules into `/rules/` and run the compiler to produce `.json`.

#GovernanceRuntime #DSLCompiler
