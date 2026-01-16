from typing import Dict, Any
import yaml
from jsonschema import validate as json_validate


class ArchitecturePatternOrchestrator:
    """Universal orchestrator for the 9-node architecture pipeline."""

    def __init__(self, pattern_file: str, subsystem_config_file: str):
        with open(pattern_file) as f:
            self.pattern = yaml.safe_load(f)
        with open(subsystem_config_file) as f:
            self.subsystem_config = yaml.safe_load(f)

        self.trace_id = None
        self.context = {}

    async def execute(self) -> Dict[str, Any]:
        """Execute the pipeline for the subsystem."""
        import uuid

        self.trace_id = str(uuid.uuid4())
        self.context = {
            "subsystem": self.subsystem_config["metadata"]["name"],
            "trace_id": self.trace_id,
        }

        print(
            f"[{self.trace_id}] Starting architecture pipeline for {self.context['subsystem']}"
        )

        for node in self.pattern["nodes"]:
            try:
                result = await self._execute_node(node)
                self.context[node["id"]] = result
                print(f"[{self.trace_id}] ✓ Node {node['id']} complete")
            except Exception as e:
                print(f"[{self.trace_id}] ✗ Node {node['id']} failed: {e}")
                return {
                    "status": "failure",
                    "failed_node": node["id"],
                    "error": str(e),
                    "trace_id": self.trace_id,
                }

        print(f"[{self.trace_id}] ✓ Pipeline complete")
        return {
            "status": "success",
            "artifacts": self.context,
            "trace_id": self.trace_id,
        }

    async def _execute_node(self, node: Dict) -> Dict:
        """Execute a single node in the pipeline."""
        # Assemble input
        input_data = self._assemble_input(node)

        # Load prompt template
        prompt = self._load_prompt_template(node["id"])

        # Call agent (placeholder - integrate with actual agent)
        print(f"[{self.trace_id}] Calling {node['role']} for {node['id']}")
        output = await self._call_agent(node["role"], prompt, input_data)

        # Validate output
        schema = node.get("output_contract", {}).get("schema", {})
        if schema:
            json_validate(instance=output, schema=schema)

        return output

    def _assemble_input(self, node: Dict) -> Dict:
        """Assemble input for a node."""
        input_data = {}

        for field in node.get("input_contract", []):
            field_name = field["name"]
            if field_name in self.context:
                input_data[field_name] = self.context[field_name]
            elif field.get("required"):
                raise ValueError(f"Required input missing: {field_name}")

        input_data["subsystem_metadata"] = self.subsystem_config["metadata"]
        input_data["subsystem_goals"] = self.subsystem_config.get("goals", [])

        return input_data

    def _load_prompt_template(self, node_id: str) -> str:
        """Load prompt template for node."""
        # For now, return generic template
        # TODO: Load from l9/patterns/prompt_templates/{node_id}.txt
        return f"You are executing node {node_id} for {self.subsystem_config['metadata']['name']}."

    async def _call_agent(self, role: str, prompt: str, input_data: Dict) -> Dict:
        """Call agent with prompt and input."""
        # Placeholder - integrate with actual agent invocation
        # TODO: Call AgentRegistry.get(role).invoke(prompt, input_data)
        return {"status": "pending", "agent": role}
