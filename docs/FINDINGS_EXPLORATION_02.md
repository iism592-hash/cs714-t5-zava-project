# Phase 02 — Exploration & BI Findings Document: Zava DIY Dataset
**Course:** COMPSCI 714 — Advanced Agentic Systems  
**Institution:** University of Auckland  
**Artifact:** Phase 02 Deliverable — Data Analysis & Candidate Problem Identification  
**Database:** PostgreSQL 17 + `pgvector` (`retail` schema) | 197,665 Orders | $47.25M Total Revenue  

---

## 1. Overview & Verification Summary

All infrastructure, database generation, and AI model endpoints are operational:
- **Core Entities Loaded:**
  - **Products:** 424 across 9 categories
  - **Stores:** 8 retail locations (7 physical Washington state stores + Online)
  - **Customers:** 50,000 registered accounts
  - **Orders:** 197,665 historical orders (2020–2026)
  - **Order Items:** 414,241 individual line items
  - **Inventory Records:** 3,392 store-SKU stock entries
  - **Vector Embeddings:** 1,536-dimensional text embeddings (`product_description_embeddings`) & 512-dimensional visual embeddings (`product_image_embeddings`)
- **Active Model Endpoints:** Azure AI Foundry `gpt-5.4-nano` (Chat/Agent) + `text-embedding-3-small` (Embeddings).

---

## 2. Five Core Empirical Observations

As required by the Phase 02 guide, each observation is backed by a reproducible SQL query, identifies business stakeholders, and evaluates whether an AI Agent provides genuine advantage over a static BI dashboard.

---

### Finding 1: Extreme Seasonal Velocity in Garden, Outdoor & Storage

- **Observation:**  
  `GARDEN & OUTDOOR` exhibits a **2.63x seasonal swing** (monthly unit demand surges from 3,489 in winter trough to 9,180 in summer peak). `STORAGE & ORGANIZATION` exhibits a **2.44x swing** (peaking in spring during home reorganizing). In contrast, `HAND TOOLS` remains relatively steady (1.24x swing).
- **Reproducible SQL Query:**
  ```sql
  WITH monthly AS (
      SELECT 
          c.category_name,
          EXTRACT(MONTH FROM o.order_date)::int as mo,
          SUM(oi.quantity) as qty
      FROM retail.categories c
      JOIN retail.products p ON c.category_id = p.category_id
      JOIN retail.order_items oi ON p.product_id = oi.product_id
      JOIN retail.orders o ON oi.order_id = o.order_id
      GROUP BY c.category_name, mo
  )
  SELECT 
      category_name,
      MIN(qty) as min_monthly_qty,
      MAX(qty) as max_monthly_qty,
      ROUND((MAX(qty)::numeric / NULLIF(MIN(qty), 0)), 2) as swing_ratio
  FROM monthly
  GROUP BY category_name
  ORDER BY swing_ratio DESC;
  ```
- **Who Cares & Impact:**  
  Supply Chain Director & Regional Warehouse Managers. A 2.6x swing requires supplier pre-orders 60–90 days in advance. Failure leads to widespread stockouts in peak spring/summer and costly dead-stock inventory holding costs over winter.
- **Agent vs. Static Report:**  
  **Agent Needed.** A static BI dashboard merely reports historical seasonality after the fact. An autonomous inventory agent can actively monitor supplier lead times, calculate store-level run rates, and proactively draft internal cross-dock transfer orders or initiate supplier Purchase Orders before stockout occurs.

---

### Finding 2: Store Disparity & Geographical Concentration

- **Observation:**  
  Sales volume is heavily concentrated. **Seattle Flagship Store** generates **$14.28M (30.2% of total retail revenue)** across 59,620 orders, followed by **Online ($8.02M)** and **Bellevue ($7.56M)**. In stark contrast, outlying satellite stores such as **Spokane ($2.35M)** and **Everett ($2.85M)** operate at less than one-fifth of Seattle's scale.
- **Reproducible SQL Query:**
  ```sql
  SELECT 
      s.store_name,
      COUNT(DISTINCT o.order_id) as total_orders,
      ROUND(SUM(oi.unit_price * oi.quantity)::numeric, 2) as total_revenue,
      ROUND((SUM(oi.unit_price * oi.quantity)::numeric / 
          (SELECT SUM(unit_price * quantity) FROM retail.order_items) * 100), 2) as revenue_share_pct
  FROM retail.stores s
  JOIN retail.orders o ON s.store_id = o.store_id
  JOIN retail.order_items oi ON o.order_id = oi.order_id
  GROUP BY s.store_name
  ORDER BY total_revenue DESC;
  ```
- **Who Cares & Impact:**  
  Retail VP of Operations and Store General Managers. Smaller stores cannot justify stocking identical SKU depth as Seattle. Allocating uniform inventory across all 8 branches ties up critical working capital in slow-moving Spokane inventory.
- **Agent vs. Static Report:**  
  **Agent Needed.** Multi-agent coordination: store-level agent nodes communicate with a regional hub agent to dynamically reallocate excess inventory from low-velocity stores to high-velocity hubs.

---

### Finding 3: Diagnostic of the 2023 Revenue Anomaly ("The Wobble")

- **Observation:**  
  Across 2020–2026, total business revenue grew predictably year-over-year (~$5.46M in 2020 to ~$8.43M in 2026), **except for 2023**, which contracted by **-1,094 orders (-3.96%) and -$77,981 in revenue** compared to 2022 ($6.51M in 2022 vs. $6.43M in 2023). Deep monthly inspection reveals that this was driven by acute crashes in **June 2023 (-11.5% YoY)** and **October 2023 (-12.0% YoY)**.
- **Reproducible SQL Query:**
  ```sql
  SELECT 
      EXTRACT(YEAR FROM o.order_date)::int as yr,
      COUNT(DISTINCT o.order_id) as total_orders,
      ROUND(SUM(oi.unit_price * oi.quantity)::numeric, 2) as annual_revenue
  FROM retail.orders o
  JOIN retail.order_items oi ON o.order_id = oi.order_id
  GROUP BY yr ORDER BY yr;
  ```
  *(Monthly drill-down query executed in `deep_dive_02.py`).*
- **Who Cares & Impact:**  
  Executive Leadership & CFO. Understanding the anatomy of sudden contractions helps insulate the business against supply chain halts, seasonal weather anomalies, or localized economic headwinds.
- **Agent vs. Static Report:**  
  **Report for Diagnosis; Agent for Real-Time Alerting.** While forensic analysis of past dips can be presented via reports, an agent system continuously monitors rolling 30-day velocity deltas against historical baseline trends, triggering early-warning countermeasures.

---

### Finding 4: Multi-Product Project Bundling & Basket Affinities

- **Observation:**  
  Customers rarely buy single isolated items; transactions follow distinct DIY project groupings (e.g., electrical work, carpentry/filing, precision measurement). Top frequent co-purchases include:
  - *Wire Stripping Pliers + Folding Rule 6-foot* (90 transactions)
  - *Riffler File Set + SAE Hex Key Set* (90 transactions)
  - *Needle-Nose Pliers 6-inch + Locking Pliers 10-inch* (88 transactions)
  - *Coping Saw + Riffler File Set* (87 transactions)
- **Reproducible SQL Query:**
  ```sql
  SELECT 
      p1.product_name as product_a,
      p2.product_name as product_b,
      COUNT(*) as basket_co_occurrences
  FROM retail.order_items oi1
  JOIN retail.order_items oi2 
    ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
  JOIN retail.products p1 ON oi1.product_id = p1.product_id
  JOIN retail.products p2 ON oi2.product_id = p2.product_id
  GROUP BY p1.product_name, p2.product_name
  ORDER BY basket_co_occurrences DESC
  LIMIT 5;
  ```
- **Who Cares & Impact:**  
  Retail Merchandising & E-Commerce Product Teams. In DIY, incomplete purchases cause immediate project failure or customer frustration (e.g., buying drywall without joint compound or drywall screws).
- **Agent vs. Static Report:**  
  **Strongest Agent Use Case.** A static report cannot converse with a DIY homeowner about their specific home repair job. An interactive AI Project Advisor understands natural-language project intent, queries vector embeddings for semantic matches, checks real-time inventory, and automatically suggests requisite complementary tools and mandatory PPE safety equipment.

---

### Finding 5: Row-Level Security (RLS) as an Architectural Isolation Boundary

- **Observation:**  
  PostgreSQL Row-Level Security (`retail.store_tenant_isolation`) strictly isolates store managers by their assigned GUID (`app.current_rls_user_id`). For example:
  - **Super Admin (`00000000-0000-0000-0000-000000000000`):** Views all 197,665 orders.
  - **Spokane Manager (`Store ID: 4`):** Restricted to exactly 9,831 orders (**4.97% of total dataset**).
- **Reproducible Verification Query:**
  ```sql
  -- Session A: Super Admin
  SET app.current_rls_user_id = '00000000-0000-0000-0000-000000000000';
  SELECT count(*) FROM retail.orders; -- Returns 197,665

  -- Session B: Spokane Store Manager
  SET app.current_rls_user_id = '<SPOKANE_MANAGER_GUID>';
  SELECT count(*) FROM retail.orders; -- Returns 9,831
  ```
- **Who Cares & Impact:**  
  System Architects, Enterprise Compliance Officers, and Security Engineers. Retail franchise and distributed store systems must prevent cross-tenant data leaks and unauthorized pricing/sales visibility.
- **Agent vs. Static Report:**  
  **Agent Architectural Necessity.** Agents must propagate security context across tool calls (MCP protocol). A store-level agent must execute SQL queries scoped to its authenticated tenant token, preventing prompt injection attacks from bypassing enterprise authorization boundaries.

---

## 3. Shortlist of Three Candidate Problems (Phase 03 Preparation)

Per the course requirements, three distinct problems have been formulated from the empirical data:

| # | Candidate Problem | Problem Statement & Value Proposition | Core Agent Capabilities |
|---|---|---|---|
| **1** | **Intelligent DIY Project Scoping & Tool/PPE Advisor (Customer-Facing)** | **Customer Pain:** DIYers frequently buy the primary tool but lack required accessories, fasteners, or mandatory safety gear, leading to project abandonment or injury.<br>**Business Value:** Increases Average Order Value (AOV), drives multi-category attach rates, and provides 24/7 expert conversational advice. | • Semantic search via `pgvector` embeddings.<br>• Real-time stock lookup via MCP tools.<br>• Proactive safety/PPE recommendation engine. *(Currently implemented in our web app!)* |
| **2** | **Dynamic Multi-Store Inventory Balancing & Seasonal Stockout Mitigation (Internal Ops)** | **Ops Pain:** Fast-moving categories (`Garden & Outdoor`, `Storage`) experience extreme seasonal swings (up to 2.63x). Seattle risks stockouts while satellite stores (e.g. Spokane) hold idle inventory.<br>**Business Value:** Minimizes stockout lost revenue, reduces warehouse holding costs, and balances stock across the 8 Washington stores. | • Time-series run-rate analysis.<br>• Multi-agent store-to-store negotiation.<br>• Automated stock transfer requisition generator. |
| **3** | **Anomalous Sales Contraction Diagnostic & Margin Optimization Engine (Executive/BI)** | **Executive Pain:** Unexplained localized volume contractions (such as the 2023 dip where June and October crashed by >11%) erode corporate profitability.<br>**Business Value:** Rapid root-cause diagnosis across macro categories, customer segments, and store tiers with automated remediation playbooks. | • Automated SQL query synthesis & anomaly detection.<br>• Cross-table root-cause correlation.<br>• Margin impact modeling (holding constant 33% gross margin). |

---

## 4. Phase 02 Completion Checklist

- [x] `--show-stats` row counts verified against all core tables
- [x] Custom exploratory SQL queries executed across stores, categories, and inventory
- [x] Documented findings with 5 detailed observations following required structure
- [x] Shortlist of 3 candidate problems formulated and ready for Phase 03 Decision Matrix
