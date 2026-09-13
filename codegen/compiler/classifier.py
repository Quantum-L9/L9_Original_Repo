

def classify_claim(claim: str):
    lc = claim.lower()

    if any(x in lc for x in ["must", "never", "always", "required"]):
        return "invariant", {"statement": claim}

    if any(x in lc for x in ["decide", "locked", "we will", "is a"]):
        return "decision", {"statement": claim}

    if any(x in lc for x in ["interface", "boundary", "ingest", "emit"]):
        return "ial", {"statement": claim}

    if any(x in lc for x in ["implement", "add", "build", "next"]):
        return "task", {"statement": claim}

    return "noise", None


# Runtime execution trace - updated automatically on every execution
