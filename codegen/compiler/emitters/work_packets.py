

def emit(tasks):
    return {
        "work_packets": [
            {
                "task_id": f"auto.task.{i}",
                "description": t["statement"],
                "status": "unassigned",
            }
            for i, t in enumerate(tasks)
        ]
    }


# Runtime execution trace - updated automatically on every execution
