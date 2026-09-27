# The Loop — Commerce Copilot (Track T6: all four platforms, one agent)

> **Track T6 — Composable commerce orchestration:** close the full loop. All four
> platforms. One agent. Gemini orchestrates; Databricks supplies intelligence; Shopify
> supplies commerce actions; **Bloomreach connects through the Loomi Connect MCP server**
> (`brx.connect.loomi.ai/mcp`, 109 tools, OAuth SSO) with your existing REST fallback; Google Cloud
> Run is the deployment surface.

> **The thesis, answered:** four platforms generate signals about the same customer from
> different vantage points. The missing piece is the agentic layer that connects them.
> **This project is that layer.** Ask "who is ava@example.com and what should we do for
> her?" and the agent stitches all vantage points into one profile, surfaces where they
> *disagree* (churned by recency, but still clicking emails → nudge, don't discount),
> and executes the treatment.

A chat agent that runs the full loop:

```
        ┌──────────────────────────────────────────────┐
        │            🤖 GEMINI AGENT (the Loop)        │
        │        function-calling · plans & acts       │
        └───────┬───────────────┬──────────────┬───────┘
                │               │              │
        ┌───────▼──────┐ ┌──────▼───────┐ ┌────▼─────────┐
        │  Databricks  │ │    Shopify   │ │  Bloomreach  │
        │ intelligence │ │   commerce   │ │  activation  │
        │  (segments,  │ │ (orders,     │ │ (campaigns,  │
        │   RFM, SQL)  │ │  discounts)  │ │  email send) │
        └──────────────┘ └──────────────┘ └──────────────┘
                  hosted on Google Cloud (Cloud Run)
```

**What it does (one sentence):** you type *"win back customers who haven't ordered in 90 days"*, the agent queries Databricks for that segment, checks their Shopify order history, creates a discount code, launches the Bloomreach email campaign, and reports back with proof.

This maps to **T5 (Behavioral signal and intervention agents)** in the reference tracks, and is the baseline for **T6 (all four platforms, one agent)**.

---

## ✅ Run in 10 minutes (MOCK MODE — no accounts needed)

```bash
# 1. Get a Gemini API key: https://aistudio.google.com/api-keys
export GEMINI_API_KEY="your-key-here"      # Windows: setx GEMINI_API_KEY "your-key"

# 2. Install & run
pip install -r requirements.txt
uvicorn app.main:app --reload

# 3. Open http://127.0.0.1:8000
```

Databricks / Shopify / Bloomreach all default to **mock mode** (`USE_MOCKS=true` in `.env`),
so the full loop works today. Flip each one to live as you get credentials.

## 🟢 Demo configuration (as submitted)

Three of the four integration surfaces run **live** in the demo — and all four *platforms*
are live, because Bloomreach is reached through the Loomi Connect MCP server. Receipts in
the UI show the mode of every call (`databricks[live]`, `shopify[live]`,
`loomi_*`, and the mock REST fallback only if MCP campaign creation doesn't fit):

| Platform | Mode | Proof in demo |
|---|---|---|
| Databricks | **live** | SQL over `workspace.default.loop_segments` — real segments (VIP / churn_risk) |
| Shopify | **live** | Real orders + catalog from the dev store; `create_discount` makes a real code visible in Admin → Discounts |
| Bloomreach | **live (via Loomi MCP)** | Agent chains `loomi_list_cloud_organizations` → `loomi_list_projects` → `loomi_search_email_campaigns` against real Bloomreach projects, and creates the win-back email campaign through MCP tools |
| Bloomreach REST fallback | mock | Legacy hand-written `trigger_campaign` used only if no MCP campaign tool fits; MCP is the live path |

Run `python tests/live_check.py` (credential doctor) and `python -m tests.mcp_check`
(SSO + tool probe) to reproduce.

---

## 🔌 Going live, platform by platform

### 1. Google Cloud / Gemini (agent brain)
- Option A (fast): AI Studio key → https://aistudio.google.com/api-keys
- Option B (enterprise): Vertex AI → `gcloud services enable aiplatform.googleapis.com`
- Deploy: `gcloud run deploy --source .` (Dockerfile included, region `us-central1`)

### 2. Databricks (intelligence)
1. Create a **SQL Warehouse** (Serverless works).
2. Settings → **Access tokens** → generate a PAT.
3. Run `sql/setup.sql` in a notebook / SQL editor to create + seed tables.
4. Env: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_HTTP_PATH`
   (SQL Warehouses → your warehouse → Connection details → HTTP path), and
   `DATABRICKS_TABLE=workspace.default.loop_segments`. All queries are guarded to
   SELECT/WITH only.

### 3. Shopify (commerce)
1. Shopify Admin (the **store** admin, not the partner dashboard) → **Settings → Apps and sales channels → Develop apps** → create an app.
2. Scopes needed: `read_orders, read_products, write_discounts`.
3. Install → copy the **Admin API access token** (`shpat_...`, shown once — the
   `shpss_` secret from partner-dashboard apps is NOT this token).
4. Seed for the demo: 2–3 products, a few test orders (Orders → Create order →
   Mark as paid), emails matching the seeded customers.
5. Env: `SHOPIFY_SHOP` (e.g. `loop-xxxx.myshopify.com`), `SHOPIFY_TOKEN`.
   Discounts use the current `discountCodeBasicCreate` mutation with required
   `context` (verified on API 2026-07).

### 4. Bloomreach (activation)
1. In Engagement → **Campaigns**, create an email campaign with a *trigger* node.
2. Copy the campaign ID; create an **API token** (Settings → Access management).
3. Env: `BLOOMREACH_PROJECT_ID`, `BLOOMREACH_API_KEY_ID`, `BLOOMREACH_API_SECRET`,
   `BLOOMREACH_CAMPAIGN_ID`. The REST layer may stay on mock — the agent prefers the
   live Loomi MCP tools for all Bloomreach work (see rule 8 in `app/agent.py`), so the
   platform runs live regardless.

Then set `USE_MOCKS=false` (or per-service: `SHOPIFY_MOCK=false`, etc.).

---

## 📅 The 1-day plan

| Time | Task | Done when |
|------|------|-----------|
| 09:00–10:00 | Gemini key, `pip install`, run mock loop | chat replies, tools fire |
| 10:00–12:00 | Databricks: run `sql/setup.sql`, wire live query | real segments in chat |
| 13:00–15:00 | Shopify dev app, wire orders + discount | agent creates real code |
| 15:00–17:00 | Bloomreach campaign + trigger | email arrives in inbox |
| 17:00–18:00 | Deploy to Cloud Run, record demo | public URL + 2-min Loom |

## 🎬 Demo beats (see `submission/video_script.md` for the full 4:30 script)
1. *"Show me my VIP customers."* → `databricks[live]` rows appear.
2. *"Win back churn-risk customers with a 15% discount and email them."* →
   receipts: `query_customers databricks[live]` → `create_discount shopify[live]`
   (real code in Shopify Admin → Discounts) → `trigger_campaign`.
3. Loomi MCP beat: the agent autonomously explores the live MCP server
   (`loomi_list_cloud_organizations` → `loomi_list_projects` →
   `loomi_search_email_campaigns`) and returns real Bloomreach campaigns.
4. *"What did you just do?"* → the agent summarizes the loop with tool receipts.

## 🧱 Repo map
```
app/
  main.py            FastAPI server + chat UI + /api/profile
  agent.py           Gemini function-calling loop (THE LOOP)
  tools.py           tool declarations the agent can call
  profile_tool.py    UNIFIED PROFILE: stitches the 3 vantage points
  shopify_tool.py    orders / products / discounts   (mock + live)
  databricks_tool.py SQL over segments               (mock + live)
  bloomreach_tool.py campaign trigger + engagement   (mock + live)
  mcp_bridge.py      Loomi Connect MCP: 109 Bloomreach tools, OAuth SSO (T6)
  mcp_oauth.py       Browser SSO for Loomi MCP (token cache ~30 days)
  config.py, state.py, mock_data.py, mock_signals.py
sql/setup.sql        Databricks tables + seed data
Dockerfile           Cloud Run deploy
```

## 🔌 Loomi Connect MCP (the T6 differentiator)

Instead of only two hand-written Bloomreach REST functions, the agent dynamically gains
Bloomreach's full MCP surface — campaigns, segments, analytics, predictions, scenarios:

1. `pip install -r requirements.txt` (pins `mcp>=1.9,<2` per Loomi docs — SDK 2.x is
   not certified and breaks `streamablehttp_client`)
2. `python -m tests.mcp_check` — **run interactively once**: a browser opens for
   Bloomreach SSO; the session then persists ~30 days. No API keys.
3. `.env`: `MCP_ENABLED=true` (+ `LOOMI_MCP_URL` if not the demo server)
4. Restart the server. The agent now sees `loomi_*` tools alongside the built-ins and
   can mix them freely (e.g. Databricks segment → MCP analytics → MCP campaign draft).

Notes: MCP is the **live** Bloomreach path; auth uses browser SSO (token cache ~30
days), so run the check once on the demo machine beforehand. The REST `trigger_campaign`
remains only as a mock fallback.

## 🧭 The judge-facing story

1. **One customer, three vantage points.** `resolve_customer` shows the same email as
   Databricks sees it (spend, segment), as Shopify sees it (orders, open cart), and as
   Bloomreach sees it (opens, clicks, views) — in one side panel.
2. **Signals disagree — the agent notices.** Ava is `churn_risk` by recency yet clicked
   the win-back email two days later. Discounting her burns margin; a personal nudge
   converts her. The recommendation engine surfaces this; the agent articulates it.
3. **Then it acts.** "Execute it" → discount created in Shopify, campaign triggered in
   Bloomreach, receipts shown. That's the loop: intelligence → decision → activation.

## 🎯 Track fit
- **T5 (Behavioral signal and intervention agents):** core demo — behavior → intervention.
- **T6 (Composable orchestration, all four):** the unified profile + chat actions ARE the
  orchestration; deploy on Cloud Run and all four boxes of the diagram are live.
