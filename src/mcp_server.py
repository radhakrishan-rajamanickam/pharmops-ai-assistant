# =============================================================================
# mcp_server.py — MCP Tool Server
# Architecture layer: MCP (Model Context Protocol layer)
# This file wraps the Snowflake query functions as MCP tools.
# The agent discovers and calls these tools via the MCP protocol.
# This is the JD requirement: "Implement Model Context Protocol (MCP) to
# bridge the gap between local development environments and LLM assistants."
# =============================================================================

from mcp.server.fastmcp import FastMCP
from snowflake_tools import query_suppliers, query_open_pos

# Create the MCP server instance
# The name "pharmops-tools" is how the agent identifies this server
mcp = FastMCP("pharmops-tools")


@mcp.tool()
def get_supplier_info(
    site_code: str = None,
    gxp_expiring_days: int = None
) -> str:
    """
    Query live supplier data from Snowflake DIM_SUPPLIER table.
    Use this tool when the user asks about:
    - Supplier GxP certification status or expiry
    - Which suppliers are suspended or at risk
    - Supplier information for a specific site (SITE-A or SITE-B)
    - Suppliers with expiring or lapsed certifications

    Args:
        site_code: Filter by site - use 'SITE-A' or 'SITE-B'
        gxp_expiring_days: Return suppliers whose GxP cert expires
                           within this many days (e.g. 90 for 90 days)
    """
    return query_suppliers(
        site_code=site_code,
        gxp_expiring_days=gxp_expiring_days
    )


@mcp.tool()
def get_open_purchase_orders(
    supplier_id: str = None,
    site_code: str = None
) -> str:
    """
    Query live purchase order data from Snowflake FACT_OPEN_POS table.
    Use this tool when the user asks about:
    - Open purchase orders for a specific supplier
    - Open POs at a specific site (SITE-A or SITE-B)
    - Financial exposure on open orders
    - Which POs might be at risk due to supplier issues

    Args:
        supplier_id: Filter by supplier ID (e.g. 'SUP-005' for Lonza AG)
        site_code: Filter by site - use 'SITE-A' or 'SITE-B'
    """
    return query_open_pos(
        supplier_id=supplier_id,
        site_code=site_code
    )


# Run the MCP server when this file is executed directly
if __name__ == "__main__":
    print("=== PharmOps MCP Server starting ===")
    print("Tools available:")
    print("  - get_supplier_info")
    print("  - get_open_purchase_orders")
    print("Server running — waiting for agent connections...")
    mcp.run()
