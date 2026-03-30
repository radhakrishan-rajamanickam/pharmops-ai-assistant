# =============================================================================
# snowflake_tools.py — Live Data Query Functions
# Architecture layer: Snowflake (live data layer)
# These functions connect to Snowflake and return live supplier and PO data.
# They are called by mcp_server.py which exposes them as MCP tools to the agent.
# Test this file standalone: python src/snowflake_tools.py
# =============================================================================

import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


def get_snowflake_connection():
    """
    Create and return a Snowflake connection using credentials from .env file.
    Called by both query functions below.
    """
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE")
    )


def query_suppliers(site_code: str = None, gxp_expiring_days: int = None) -> str:
    """
    Query DIM_SUPPLIER table for supplier information.

    Architecture role: MCP Tool 1 — exposed to the agent via mcp_server.py.
    The agent calls this when the user asks about supplier status, GxP
    certification, or wants to know which suppliers are at risk.

    Args:
        site_code: Optional — filter by site e.g. 'SITE-A' or 'SITE-B'
        gxp_expiring_days: Optional — return suppliers whose GxP cert
                           expires within this many days from today

    Returns:
        Formatted string of supplier results for the agent to read
    """
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    # Build the WHERE clause dynamically based on what filters are provided
    # This makes the function flexible — agent can call it with any combination
    conditions = []
    params = []

    if site_code:
        conditions.append("SITE_CODE = %s")
        params.append(site_code.upper())

    if gxp_expiring_days:
        # Find suppliers whose cert expires within the specified number of days
        # OR whose cert has already lapsed (expiry date in the past)
        conditions.append(
            "GXP_EXPIRY_DATE <= DATEADD(day, %s, CURRENT_DATE())"
        )
        params.append(int(gxp_expiring_days))

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT
            SUPPLIER_ID,
            LEGAL_NAME,
            SITE_CODE,
            COUNTRY_CODE,
            SUPPLIER_TYPE,
            GXP_CERTIFIED,
            GXP_EXPIRY_DATE,
            PAYMENT_TERMS,
            STATUS
        FROM DIM_SUPPLIER
        {where_clause}
        ORDER BY GXP_EXPIRY_DATE ASC
    """

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return "No suppliers found matching the given criteria."

    # Format results as readable text for the agent
    lines = ["SUPPLIER QUERY RESULTS:"]
    lines.append("-" * 50)
    for row in rows:
        (supplier_id, legal_name, site, country, sup_type,
         gxp_certified, gxp_expiry, payment_terms, status) = row
        lines.append(f"Supplier ID:    {supplier_id}")
        lines.append(f"Name:           {legal_name}")
        lines.append(f"Site:           {site}")
        lines.append(f"Country:        {country}")
        lines.append(f"Type:           {sup_type}")
        lines.append(f"GxP Certified:  {gxp_certified}")
        lines.append(f"GxP Expiry:     {gxp_expiry}")
        lines.append(f"Payment Terms:  {payment_terms}")
        lines.append(f"Status:         {status}")
        lines.append("-" * 50)

    return "\n".join(lines)


def query_open_pos(supplier_id: str = None, site_code: str = None) -> str:
    """
    Query FACT_OPEN_POS table for open purchase orders.

    Architecture role: MCP Tool 2 — exposed to the agent via mcp_server.py.
    The agent calls this when the user asks about open orders, procurement
    exposure, or wants to know which POs are at risk due to supplier issues.

    Args:
        supplier_id: Optional — filter by supplier e.g. 'SUP-005'
        site_code: Optional — filter by site e.g. 'SITE-A'

    Returns:
        Formatted string of open PO results for the agent to read
    """
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    # Build WHERE clause dynamically
    conditions = ["p.STATUS = 'OPEN'"]
    params = []

    if supplier_id:
        conditions.append("p.SUPPLIER_ID = %s")
        params.append(supplier_id.upper())

    if site_code:
        conditions.append("p.SITE_CODE = %s")
        params.append(site_code.upper())

    where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            p.PO_NUMBER,
            p.SUPPLIER_ID,
            s.LEGAL_NAME,
            p.SITE_CODE,
            p.MATERIAL_DESC,
            p.TOTAL_VALUE_USD,
            p.PO_DATE,
            p.EXPECTED_DELIVERY,
            p.STATUS,
            s.GXP_CERTIFIED,
            s.STATUS AS SUPPLIER_STATUS
        FROM FACT_OPEN_POS p
        JOIN DIM_SUPPLIER s ON p.SUPPLIER_ID = s.SUPPLIER_ID
        {where_clause}
        ORDER BY p.TOTAL_VALUE_USD DESC
    """

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return "No open purchase orders found matching the given criteria."

    # Format results as readable text for the agent
    lines = ["OPEN PURCHASE ORDER RESULTS:"]
    lines.append("-" * 50)
    for row in rows:
        (po_number, supplier_id, legal_name, site, material,
         value, po_date, delivery, status,
         gxp_certified, supplier_status) = row
        lines.append(f"PO Number:        {po_number}")
        lines.append(f"Supplier ID:      {supplier_id}")
        lines.append(f"Supplier Name:    {legal_name}")
        lines.append(f"Site:             {site}")
        lines.append(f"Material:         {material}")
        lines.append(f"Value (USD):      ${value:,.2f}")
        lines.append(f"PO Date:          {po_date}")
        lines.append(f"Expected Delivery:{delivery}")
        lines.append(f"PO Status:        {status}")
        lines.append(f"Supplier GxP:     {gxp_certified}")
        lines.append(f"Supplier Status:  {supplier_status}")
        lines.append("-" * 50)

    return "\n".join(lines)


# Test block — runs when you execute: python src/snowflake_tools.py
if __name__ == "__main__":
    print("=== Snowflake Tools Test ===\n")

    # Test 1 — all SITE-A suppliers
    print("[Test 1] All suppliers at SITE-A:")
    print(query_suppliers(site_code="SITE-A"))

    print("\n")

    # Test 2 — suppliers with GxP expiring within 90 days or lapsed
    print("[Test 2] Suppliers with GxP expiring within 90 days:")
    print(query_suppliers(gxp_expiring_days=90))

    print("\n")

    # Test 3 — open POs for Lonza AG (the demo showstopper)
    print("[Test 3] Open POs for Lonza AG (SUP-005):")
    print(query_open_pos(supplier_id="SUP-005"))

    print("\n")

    # Test 4 — all open POs at SITE-A
    print("[Test 4] All open POs at SITE-A:")
    print(query_open_pos(site_code="SITE-A"))