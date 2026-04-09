"""Allow ``python -m ff_kit.mcp`` to start the server."""

from ff_kit.mcp.server import run_stdio

if __name__ == "__main__":
    run_stdio()
