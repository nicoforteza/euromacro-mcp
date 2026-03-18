"""FastMCP server entry point."""

from fastmcp import FastMCP

mcp = FastMCP("eurodata")


@mcp.tool()
async def search_series(query: str) -> list[dict]:
    """Search for series in the catalog by keyword."""
    # TODO: Implement search logic
    return []


@mcp.tool()
async def get_series(series_id: str) -> dict:
    """Fetch time series data by ID."""
    # TODO: Implement fetch logic
    return {}


@mcp.tool()
async def describe_series(series_id: str) -> dict:
    """Get metadata and description for a series."""
    # TODO: Implement describe logic
    return {}


@mcp.tool()
async def list_categories() -> list[str]:
    """List all available data categories."""
    # TODO: Implement list logic
    return []


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
