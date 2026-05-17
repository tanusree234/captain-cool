"""Captain Cool — The Multi-Agent IPL Match Strategist."""
try:
    from captain_cool.agent import root_agent
    __all__ = ["root_agent"]
except ImportError:
    __all__ = []

