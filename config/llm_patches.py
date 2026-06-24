"""
Small runtime patches needed to run CrewAI against Groq.
Idempotent; safe to call multiple times.
"""


def patch_groq_cache() -> None:
    """Groq rejects the `cache_breakpoint` field CrewAI adds to messages."""
    try:
        import crewai.llms.cache as _c
        _c.mark_cache_breakpoint = lambda msg: msg
    except Exception:
        pass
