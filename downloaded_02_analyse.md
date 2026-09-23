---
title: "02 - Analyse: Explore the Zava Dataset"
description: "Set up the Zava DIY project, explore the retail dataset, and find real problems worth solving with evidence to back them."
date: 2026-08-04
lastmod: 2026-08-04
author: "Class Notes"
tags: ["agents", "COMPSCI 714", "Zava DIY", "data analysis"]
category: "Agents Class"
slug: "02-analyse"
layout: "page"
draft: false
related: ["01-learn", "03-decide"]
---

# 02 - Analyse: Explore the Zava Dataset

**Phase 2 of 5.** Explore the Zava DIY retail dataset and find a real problem worth solving.

> **What you will have at the end of this phase:** the Zava project running locally, a documented set of findings from your own exploration, and a shortlist of three candidate problems that the data can actually evidence.

**Do not skip to phase 3.** The most common cause of a weak project is a team that chose a use case in a meeting room and then went looking for data to support it. Explore first.

---

## ✅ Step 1: Fork, clone and open

Fork [github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp), then:

```bash
git clone https://github.com/<your-username>/ai-tour-26-zava-diy-dataset-plus-mcp.git
cd ai-tour-26-zava-diy-dataset-plus-mcp
code .
```

---

## ✅ Step 2: Reopen in the dev container

**Start Docker Desktop first.** This is the failure everybody hits.

In VS Code, either click **Reopen in Container** when prompted, or press `Ctrl+Shift+P` and select **Dev Containers: Reopen in Container**.

The container builds an environment with PostgreSQL, the pgvector extension, Python and every dependency already installed.

> **⚠️ Do not install PostgreSQL and pgvector by hand.** It is an entire evening, it teaches you nothing relevant to this paper, and the container exists precisely so you do not have to.

---

## ✅ Step 3: Generate the database

Inside the container terminal:

```bash
cd data/database
pip install -r requirements.txt
python generate_zava_postgres.py
python generate_zava_postgres.py --show-stats
```

Other useful options:

```bash
python generate_zava_postgres.py --verify-seasonal    # confirm seasonal patterns loaded
python generate_zava_postgres.py --help               # all options
```

---

## ✅ Step 4 (optional): Deploy Azure AI models

Only needed if your use case will use semantic or vector search. You can come back to this in phase 4 once you know.

```bash
az login --use-device-code
cd infra && ./deploy.sh
```

This deploys `gpt-4o-mini` and `text-embedding-3-small`, and writes the configuration into `src/python/workshop/.env`.

---

## 🗄️ What is in the dataset

Zava DIY is a fictional home improvement retailer with eight locations across Washington State, seven physical stores plus online.

| Component | Scale |
|---|---|
| Customers | 50,000+ |
| Products | 400+ across 9 categories |
| Order line items | 200,000+, spanning 2020 to 2026 |
| Stores | 8 |
| Inventory records | 3,000+ |
| Vector embeddings | Product descriptions (1536-dim) and images (512-dim) |

**Core tables**, all in the `retail` schema:

| Table | Contains |
|---|---|
| `customers` | Demographic profiles, primary store assignment |
| `stores` | 8 locations with traffic weights and order value multipliers |
| `categories`, `product_types`, `products` | Product hierarchy, SKUs, cost and price |
| `orders`, `order_items` | Transaction headers and line items, 2020 to 2026 |
| `inventory` | Store-specific stock levels |
| `product_description_embeddings` | 1536-dim vectors for semantic text search |
| `product_image_embeddings` | 512-dim vectors for visual similarity |

---

## 🔍 What to go looking for

Four things are deliberately built into this data. Each one is a potential use case. Go and verify them yourself rather than taking my word for it.

### 1. Seasonality, and it is strong

| Category | Pattern |
|---|---|
| Paint and Finishes | Peaks in April at 2.2x normal volume, sustained March to August |
| Power Tools | Peaks June to July at 2.0-2.1x, drops to 0.8x December to February |
| Lumber and Building Materials | Peaks June to July at 2.1-2.2x, drops to 0.7x November to February |
| Garden and Outdoor | Extreme. Falls to 50% of normal in winter |
| Hand Tools | Peaks May to August at 1.4-1.6x |

That is a forecasting and inventory problem sitting there waiting for you.

### 2. Store variation

Seattle, Bellevue and Online behave completely differently from Spokane, Everett, Redmond and Kirkland, in both order frequency and order value. Seattle carries 30% of customers with a 3.0x order frequency multiplier. Spokane carries 8% at 2.0x.

### 3. A wobble nobody has explained

Growth is steady year on year from 2020 to 2026, **except 2023, which dips**. The data does not tell you why. That is an invitation.

### 4. Row Level Security as a real constraint

Each store manager has a unique identity and can see only their own store's orders, order items, inventory and customers. The all zeros identity `00000000-0000-0000-0000-000000000000` is the super manager and bypasses all restrictions.

Most teams will use the super manager identity and never think about it again. For an architecture and design paper, this is the most interesting thing in the repository. It means your agent operates inside a real authorisation boundary, which raises genuinely hard questions you can write about.

Also note: gross margin is a consistent 33% across all products, with the JSON price data representing wholesale cost. Selling price is cost divided by 0.67.

---

## 📝 Step 5: Do the exploration

Spend an afternoon in a notebook with pandas or a SQL client. Answer questions like these, and **write down what you find**:

- Which category has the sharpest seasonal swing, and how far ahead would you need to act on it?
- Which stores are most and least aligned to the national seasonal pattern?
- What actually happened in 2023? Which categories, which stores, which months?
- Which products are frequently bought together, and does that differ by store or season?
- Where is inventory misaligned with demand? Are there stores holding stock that another store needs?
- Which products have the widest gap between inventory levels and sales velocity?
- How different does the data look when you query as a single store manager rather than the super manager?

> **💡 Tip:** Ask GitHub Copilot to explain the schema and write your first exploratory queries. Pointing an agent at an unfamiliar codebase is the fastest way to understand it, and it is good practice for the thing you are about to build.

---

## 📋 What to record

Keep a findings document. You will need it for your report, and it becomes the evidence base for your use case justification in phase 3.

For each finding, capture:

- **The observation**, stated plainly
- **The query or analysis** that produced it, so it is reproducible
- **Who would care**, and what they might do differently
- **Whether an agent would help**, or whether a report would do the job

---

## 🏁 Checkpoint

Do not move to phase 3 until all of these are true.

- [ ] `--show-stats` returns sensible row counts across customers, products, orders and inventory
- [ ] You have run your own queries, not just the samples
- [ ] You have a findings document with at least five observations, each backed by a query
- [ ] **You have three candidate problems, each one evidenced by something you found in the data**

Three candidates, not one. In phase 3 you will test them against each other.

---

## 🔧 If you get stuck

| Symptom | Fix |
|---|---|
| Dev container will not start | Docker Desktop is not running, or has insufficient memory. Allow 4 GB or more |
| Database generation fails | Confirm you are inside the container, and that `product_data.json` and `reference_data.json` are present |
| Queries return no rows | Your RLS user ID is scoped to a store with no matching data. Use the all zeros super manager identity |
| Semantic search returns nothing | You have not deployed the embedding model. Run `infra/deploy.sh`, or use a non-semantic approach |

---

## ➡️ Next step

With three evidenced candidates in hand, go to **[03 - Decide](03-decide.md)**.

---

*The opinions expressed herein are my own personal opinions and do not represent my employer's view in any way. Presentation and Content Resources are provided as is with no guarantees or warranties of any kind.*
