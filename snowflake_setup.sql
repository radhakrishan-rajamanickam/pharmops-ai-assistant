-- =============================================================================
-- PharmOps AI Assistant — Snowflake Setup
-- Run this entire script once in a new worksheet
-- =============================================================================

-- Step 1: Create the database and schema
CREATE DATABASE IF NOT EXISTS PHARMOPS_DEMO;
USE DATABASE PHARMOPS_DEMO;
CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

-- Step 2: Create the warehouse (compute engine) if not exists
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;

USE WAREHOUSE COMPUTE_WH;

-- =============================================================================
-- Table 1: DIM_SUPPLIER
-- Master data for suppliers — sourced from Reltio MDM in real AZ context
-- GXP_EXPIRY_DATE is the critical field for the Lonza demo scenario
-- =============================================================================

CREATE OR REPLACE TABLE DIM_SUPPLIER (
    SUPPLIER_ID       VARCHAR(10)    NOT NULL PRIMARY KEY,
    LEGAL_NAME        VARCHAR(200)   NOT NULL,
    SITE_CODE         VARCHAR(10)    NOT NULL,
    COUNTRY_CODE      CHAR(2)        NOT NULL,
    SUPPLIER_TYPE     VARCHAR(30),
    GXP_CERTIFIED     BOOLEAN        NOT NULL DEFAULT FALSE,
    GXP_EXPIRY_DATE   DATE,
    PAYMENT_TERMS     VARCHAR(20),
    STATUS            VARCHAR(20)    NOT NULL DEFAULT 'APPROVED',
    LAST_UPDATED      TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);

-- =============================================================================
-- Table 2: FACT_OPEN_POS
-- Live purchase orders — the operational data the MCP tool queries
-- Lonza AG (SUP-005) has an open PO — this is the demo showstopper
-- =============================================================================

CREATE OR REPLACE TABLE FACT_OPEN_POS (
    PO_NUMBER           VARCHAR(15)    NOT NULL PRIMARY KEY,
    SUPPLIER_ID         VARCHAR(10)    NOT NULL,
    SITE_CODE           VARCHAR(10)    NOT NULL,
    MATERIAL_DESC       VARCHAR(200),
    TOTAL_VALUE_USD     NUMBER(12,2),
    PO_DATE             DATE           NOT NULL,
    EXPECTED_DELIVERY   DATE,
    STATUS              VARCHAR(20)    NOT NULL DEFAULT 'OPEN'
);

-- =============================================================================
-- Sample data: 8 suppliers across SITE-A and SITE-B
-- Key scenario: Lonza AG (SUP-005) has GXP_CERTIFIED=FALSE and lapsed cert
-- This is what the agent will find when asked about GxP issues at SITE-A
-- =============================================================================

INSERT INTO DIM_SUPPLIER VALUES
('SUP-001', 'Merck KGaA',           'SITE-A', 'DE', 'Raw Material',  TRUE,  '2027-03-01', 'Net 60',  'APPROVED',     CURRENT_TIMESTAMP()),
('SUP-002', 'Pfizer Ltd UK',        'SITE-A', 'GB', 'API Supplier',  TRUE,  '2027-01-15', 'Net 30',  'APPROVED',     CURRENT_TIMESTAMP()),
('SUP-003', 'Samsung Bioepis',      'SITE-B', 'KR', 'Biologics',     TRUE,  '2026-09-30', 'Net 45',  'APPROVED',     CURRENT_TIMESTAMP()),
('SUP-004', 'Evonik Industries',    'SITE-B', 'DE', 'Excipient',     TRUE,  '2026-12-01', 'Net 60',  'APPROVED',     CURRENT_TIMESTAMP()),
('SUP-005', 'Lonza AG',             'SITE-A', 'CH', 'CMO',           FALSE, '2026-02-01', 'Net 45',  'SUSPENDED',    CURRENT_TIMESTAMP()),
('SUP-006', 'Siegfried AG',         'SITE-B', 'CH', 'API Supplier',  TRUE,  '2026-05-15', 'Net 30',  'APPROVED',     CURRENT_TIMESTAMP()),
('SUP-007', 'Catalent Inc',         'SITE-A', 'US', 'CMO',           TRUE,  '2026-06-30', 'Net 45',  'APPROVED',     CURRENT_TIMESTAMP()),
('SUP-008', 'Recipharm AB',         'SITE-B', 'SE', 'CMO',           TRUE,  '2027-02-28', 'Net 60',  'APPROVED',     CURRENT_TIMESTAMP());

-- =============================================================================
-- Sample data: 12 open purchase orders
-- Key scenario: SUP-005 (Lonza AG) has an open PO worth $89,500
-- This creates the conflict — suspended supplier with active open PO
-- =============================================================================

INSERT INTO FACT_OPEN_POS VALUES
('PO-2026-001', 'SUP-001', 'SITE-A', 'Active Pharmaceutical Ingredient — Batch A',  142000.00, '2026-02-15', '2026-04-15', 'OPEN'),
('PO-2026-002', 'SUP-001', 'SITE-A', 'Raw Material — Excipient Grade',               38500.00,  '2026-03-01', '2026-04-30', 'OPEN'),
('PO-2026-003', 'SUP-002', 'SITE-A', 'Bulk API — Formulation Grade',                220000.00, '2026-02-20', '2026-05-01', 'OPEN'),
('PO-2026-004', 'SUP-002', 'SITE-A', 'Packaging Components — Batch 2',               45000.00,  '2026-03-10', '2026-04-20', 'OPEN'),
('PO-2026-005', 'SUP-005', 'SITE-A', 'Contract Manufacturing — Batch LZ-4421',       89500.00,  '2026-01-15', '2026-04-01', 'OPEN'),
('PO-2026-006', 'SUP-007', 'SITE-A', 'Fill and Finish Services — Q2 Batch',          67000.00,  '2026-03-05', '2026-05-15', 'OPEN'),
('PO-2026-007', 'SUP-003', 'SITE-B', 'Biologic Drug Substance — Lot BB-221',        185000.00, '2026-02-10', '2026-06-01', 'OPEN'),
('PO-2026-008', 'SUP-003', 'SITE-B', 'Biologic Raw Material — Culture Media',        29000.00,  '2026-03-15', '2026-04-25', 'OPEN'),
('PO-2026-009', 'SUP-004', 'SITE-B', 'Excipient Supply — Mannitol Grade A',          52000.00,  '2026-02-28', '2026-04-10', 'OPEN'),
('PO-2026-010', 'SUP-006', 'SITE-B', 'API Intermediate — Synthesis Batch',           94000.00,  '2026-03-01', '2026-05-30', 'OPEN'),
('PO-2026-011', 'SUP-008', 'SITE-B', 'Contract Manufacturing — Oral Solid',          73500.00,  '2026-02-25', '2026-05-10', 'OPEN'),
('PO-2026-012', 'SUP-007', 'SITE-A', 'Sterile Fill — Vial Batch Q2',                 58000.00,  '2026-03-20', '2026-06-15', 'OPEN');

-- =============================================================================
-- Verify everything loaded correctly
-- =============================================================================

SELECT 'Suppliers loaded:' AS check_item, COUNT(*) AS count FROM DIM_SUPPLIER
UNION ALL
SELECT 'Open POs loaded:', COUNT(*) FROM FACT_OPEN_POS;

-- Preview the Lonza scenario — this is what the agent will find
SELECT
    s.SUPPLIER_ID,
    s.LEGAL_NAME,
    s.GXP_CERTIFIED,
    s.GXP_EXPIRY_DATE,
    s.STATUS,
    p.PO_NUMBER,
    p.TOTAL_VALUE_USD,
    p.MATERIAL_DESC
FROM DIM_SUPPLIER s
JOIN FACT_OPEN_POS p ON s.SUPPLIER_ID = p.SUPPLIER_ID
WHERE s.GXP_CERTIFIED = FALSE
   OR s.STATUS = 'SUSPENDED';
