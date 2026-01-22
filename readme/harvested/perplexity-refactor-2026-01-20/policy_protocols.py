class PromptDefensePolicy(Protocol):
    async def check(self, task: AgentTask) -> ExecutionResult | None: ...


class MemoryWarmPolicy(Protocol):
    async def warm(self, task: AgentTask) -> None: ...


class GraphHydrationPolicy(Protocol):
    async def hydrate(self, task: AgentTask, instance: AgentInstance) -> None: ...


class ReflectionPolicy(Protocol):
    async def run(
        self, task: AgentTask, result: ExecutionResult, instance: AgentInstance
    ) -> None: ...
