blocked = await self._prompt_defense.check(task)
if blocked:
    return blocked

await self._memory_warm_policy.warm(task)
await self._graph_hydration_policy.hydrate(task, instance)
...
await self._reflection_policy.run(task, result, instance)
