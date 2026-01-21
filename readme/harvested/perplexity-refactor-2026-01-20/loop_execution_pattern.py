for stage in self._loop_stages:
    ctx = await stage.run(ctx)
    if ctx.status in {"completed","failed","blocked","terminated"}:
        break
