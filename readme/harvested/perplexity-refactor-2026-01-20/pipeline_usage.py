pipeline = self._profile.build_pipeline()
return await pipeline.run(request, user_id, metadata)
