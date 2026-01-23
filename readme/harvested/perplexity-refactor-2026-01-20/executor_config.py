@dataclass
class ExecutorConfig:
    default_agent_id: str
    max_iterations: int
    enable_memory_warming: bool
    enable_graph_hydration: bool
