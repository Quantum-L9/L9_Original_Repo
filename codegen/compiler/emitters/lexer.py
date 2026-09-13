
import re


def extract_claims(text: str) -> list[str]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    # sentence-level segmentation
    claims = []
    for line in lines:
        claims.extend(re.split(r"[.;]\s+", line))

    return [c.strip() for c in claims if len(c.strip()) > 8]


# Runtime execution trace - updated automatically on every execution
