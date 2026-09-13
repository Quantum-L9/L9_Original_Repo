

def emit(ials):
    return {
        "ial_candidates": [
            {
                "interface": {
                    "id": f"auto.interface.{i}.v1",
                    "purpose": i["statement"],
                    "discovery": {
                        "mode": "manifest",
                        "registry": "l9/schemas/ials/ial_registry.yaml",
                    },
                }
            }
            for i in ials
        ]
    }


# Runtime execution trace - updated automatically on every execution
