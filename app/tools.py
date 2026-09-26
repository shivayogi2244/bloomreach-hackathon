"""Tool declarations for the Gemini agent. Schemas mirror the python wrappers."""

QUERY_CUSTOMERS = {
    "name": "query_customers",
    "description": (
        "Query the customer data warehouse (Databricks). Returns customers with email, "
        "name, total_spent, order_count, last_order_at and their segment. "
        "Use before any campaign to build the audience."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "segment": {
                "type": "string",
                "enum": ["vip", "churn_risk", "new", "active"],
                "description": "Optional segment filter. Omit for all customers.",
            },
            "limit": {"type": "integer", "description": "Max rows to return (default 20)"},
        },
        "required": [],
    },
}

RUN_READONLY_SQL = {
    "name": "run_readonly_sql",
    "description": (
        "Run a read-only SELECT/WITH query against Databricks. Customer segments "
        "table (email, first_name, last_name, total_spent, order_count, "
        "last_order_at, segment). Only SELECT allowed."
    ),
    "parameters": {
        "type": "object",
        "properties": {"sql": {"type": "string", "description": "The SELECT query to run"}},
        "required": ["sql"],
    },
}

LIST_ORDERS = {
    "name": "list_orders",
    "description": "List recent Shopify orders, optionally filtered to one customer email.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Filter to this customer's orders"},
            "limit": {"type": "integer", "description": "Max orders (default 20)"},
        },
        "required": [],
    },
}

LIST_PRODUCTS = {
    "name": "list_products",
    "description": "List products in the Shopify catalog with prices.",
    "parameters": {
        "type": "object",
        "properties": {"limit": {"type": "integer", "description": "Max products (default 10)"}},
        "required": [],
    },
}

CREATE_DISCOUNT = {
    "name": "create_discount",
    "description": (
        "Create a Shopify percent-off discount code for a named audience. "
        "Returns the code the customer can redeem."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "percent": {"type": "integer", "description": "Discount percent, e.g. 15"},
            "segment": {"type": "string", "description": "Audience label, e.g. churn_risk"},
            "customer_emails": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Emails the discount is intended for",
            },
        },
        "required": ["percent", "segment", "customer_emails"],
    },
}

TRIGGER_CAMPAIGN = {
    "name": "trigger_campaign",
    "description": (
        "Send/trigger the Bloomreach email campaign to a list of customer emails, "
        "with an optional discount code to include in the email."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "customer_emails": {"type": "array", "items": {"type": "string"}},
            "message": {"type": "string", "description": "Personalized message for the email"},
            "discount_code": {"type": "string", "description": "Optional Shopify discount code"},
        },
        "required": ["customer_emails", "message"],
    },
}

RESOLVE_CUSTOMER = {
    "name": "resolve_customer",
    "description": (
        "Unify one customer across all platforms: Databricks aggregates, Shopify "
        "orders + open cart, Bloomreach engagement signals. Returns one profile "
        "with vantage points, a recommendation (action + why + channel). Use for "
        "'who is this customer', 'what should we do for X', or before deciding "
        "treatment for a specific person."
    ),
    "parameters": {
        "type": "object",
        "properties": {"email": {"type": "string", "description": "Customer email"}},
        "required": ["email"],
    },
}

ALL_TOOLS = [
    QUERY_CUSTOMERS,
    RUN_READONLY_SQL,
    LIST_ORDERS,
    LIST_PRODUCTS,
    CREATE_DISCOUNT,
    TRIGGER_CAMPAIGN,
    RESOLVE_CUSTOMER,
]
