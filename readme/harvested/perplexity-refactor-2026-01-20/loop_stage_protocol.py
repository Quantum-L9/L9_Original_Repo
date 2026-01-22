class LoopStage(Protocol):
    async def run(self, ctx: LoopContext) -> LoopContext: ...


@dataclass
class LoopContext:
    instance: AgentInstance
    aios_result: Optional[AIOSResult] = None
    status: str = "running"
    error: Optional[str] = None
    final_result: Optional[str] = None
    iteration: int = 0
