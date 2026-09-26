# Minting credentials — exact click-paths

The agent talks to every platform over plain HTTPS APIs, so **one credential per platform
is all it needs**. No vendor SDKs, no connectors. Sandbox/trial/dev instances issue the
exact same tokens as production — mint once, paste into `.env`, run the doctor.

Check yourself anytime:

```bash
python -m tests.live_check
# [OK] = live & working   [--] = missing vars   [XX] = creds rejected
```

---

## 1. Gemini (Google AI Studio) — 2 minutes

1. Go to **https://aistudio.google.com/api-keys** (sign in with any Google account).
2. **Create API key** → pick/create a project → copy the key (`AIza...`).
3. `.env` → `GEMINI_API_KEY=AIza...` (no quotes, no spaces).

Enterprise alternative: Vertex AI in the Cloud Console — enable
`aiplatform.googleapis.com`, then in `.env` set `GOOGLE_CLOUD_PROJECT`,
`GOOGLE_CLOUD_LOCATION=global` and `GOOGLE_GENAI_USE_ENTERPRISE=True`
(instead of the AI Studio key) and authenticate with
`gcloud auth application-default login`.

## 2. Databricks — 10 minutes

You need three values: **HOST**, **TOKEN**, **WAREHOUSE_ID**.

1. Log in. Your browser URL is the host: `https://dbc-xxxx.cloud.databricks.com`
   (AWS) or `https://adb-xxxx.azuredatabricks.net` (Azure). → `DATABRICKS_HOST`
   *(scheme + host only, no trailing slash, no `/sql/...`)*
2. **Token:** top-right avatar → **Settings** → **Developer** → **Access tokens** →
   **Generate new token** → set a lifetime (e.g. 90 days) → copy the `dapi...` string.
   → `DATABRICKS_TOKEN`
3. **Warehouse:** left nav → **Compute** (or **SQL Warehouses**) → **Create SQL
   warehouse** → *Serverless*, size Small → open **Connection details** tab → copy
   the **Server hostname** check ✔, the **HTTP path** contains the **Warehouse ID**
   (the long hex after the last dot, e.g. `a1b2c3d4...`). → `DATABRICKS_WAREHOUSE_ID`
4. **Load the data:** left nav → **SQL Editor** → paste all of `sql/setup.sql` → Run.
   You should see 6 customers.
5. `.env` gets the three values → run `python -m tests.live_check`.
   Expect: `token OK, N warehouse(s) visible; yours is RUNNING; loop_segments has 6 rows`.

> No Databricks account? **databricks.com/try-databricks** — the free trial includes SQL
> warehouses. (Community Edition does **not** — use the trial.) Your existing login works
> if your org's workspace lets you create a token; if "Access tokens" is greyed out, ask
> your admin to allow personal access tokens for the workspace.

## 3. Shopify — 15 minutes

You need two values: **SHOP** domain and **Admin API TOKEN**.

**If you don't have a store — free dev store:**
1. **https://partners.shopify.com** → log in → **Stores** → **Add store → Create dev
   store** (free, fully functional APIs).
2. Place 3–4 test orders from the dev store's storefront (enable test payments:
   Settings → Payments → activate "Bogus Gateway" / test mode) so `list_orders`
   has data.

**Mint the token (same for dev or real store):**
1. Store admin → **Settings** → **Apps and sales channels** → **Develop apps** →
   **Allow custom app development** (one-time) → **Create an app**.
2. **Configuration** tab → **Admin API integration** → **Configure** → tick scopes:
   - `read_orders`
   - `read_products`
   - `read_customers` (optional, helps audience checks)
   - `write_discounts`
   → **Save**.
3. **API credentials** tab → **Install app** → the **Admin API access token**
   (`shpat_...`) is shown **once** — copy it. → `SHOPIFY_TOKEN`
4. The store domain (`yourstore.myshopify.com`) → `SHOPIFY_SHOP`
5. `.env` → run `python -m tests.live_check`.
   Expect: `connected to '<store name>' (<store>.myshopify.com)`.

> GraphQL discount creation (`write_discounts`) works on dev stores. If you see
> `ACCESS_DENIED`, re-check the scope, then **reinstall** the app so the token
> picks up new scopes.

## 4. Bloomreach (Engagement) — 15 minutes

You need three values: **PROJECT_ID**, **API_KEY**, **CAMPAIGN_ID**.

1. Log in to Engagement (`app.exponea.com` or your regional domain).
2. **Project ID:** top-left project switcher → **Settings → Project configuration**
   (or copy from the URL) — a UUID. → `BLOOMREACH_PROJECT_ID`
3. **API key:** **Settings → Access management → API** → **+ New API token** →
   grant groups **Campaign manager** and **Data manager** (minimum: campaign
   trigger + customer events read) → create → copy the token (a long base64
   string). → `BLOOMREACH_API_KEY`
4. **Campaign (the one the agent triggers):**
   **Campaigns → + Create campaign → Email** →
   - Add a **Trigger** node of type **Ad-hoc** (API trigger) and copy its
     **Action ID** (in the trigger node settings — a UUID). → `BLOOMREACH_CAMPAIGN_ID`
   - Add an **Email** node; in the template use Jinja variables the agent sends:
     `{{ message }}` and `{{ discount_code }}`.
   - **Con**figure → Save → **Start** the campaign.
5. `.env` → `BLOOMREACH_BASE_URL=https://api.exponea.com` unless your project is on
   another regional domain (check your login URL / docs).
6. Run `python -m tests.live_check` → expect `token + project valid`.
   Then send one real trigger (chat: "email ava@example.com with a nudge") and
   confirm the email lands (use your own email as a test contact:
   **Customers → search ava@example.com → change email to yours**).

> Field names shift occasionally between Engagement versions — if a step looks
> different, cross-check **developers.bloomreach.com** → Engagement → APIs →
> *Campaigns* and *Customer events*. The payload shape lives in
> `app/bloomreach_tool.py` (single place to adjust).

---

## 5. Flip to live

```bash
# in .env
USE_MOCKS=false          # or per-service: DATABRICKS_MOCK=false, etc.

# restart the server (env is read at startup)
uvicorn app.main:app --reload
```

Receipts in the chat will now show `databricks[live]`, `shopify[live]`, `bloomreach[live]`.
Flip **one platform at a time** — mocks keep the rest of the demo working regardless.
