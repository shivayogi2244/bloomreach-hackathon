"""THE LOOP: Gemini agent that plans, calls tools across platforms, and answers."""

import json
from typing import Any

from google import genai
from google.genai import types

from . import bloomreach_tool, databricks_tool, profile_tool, shopify_tool
from .config import GEMINI_API_KEY, GEMINI_MODEL
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """You are the Loop Copilot for an e-commerce brand. You operate the full loop:
- Databricks: customer intelligence (segments, spend, recency)
- Shopify: commerce (orders, catalog, discount codes)
- Bloomreach: activation (email campaigns)

Operating rules:
1. Understand the goal, then act: segment customers -> build the offer -> activate.
2. For "win back churned customers" requests: query the churn_risk segment, create a
   discount, and trigger the campaign — then summarize exactly what you did, including
   the discount code and who was contacted.
3. Always ground claims in tool results; show real emails/codes/numbers.
4. Data source notes: say whether data came from mock or live mode.
5. Be concise: short paragraphs or bullet lists, receipts included.
6. The platforms see the SAME customer from different vantage points — your job is to
   connect them. For questions about one person, call resolve_customer: it stitches
   Databricks aggregates + Shopify behavior + Bloomreach engagement and recommends an
   action. Respect its reasoning, but override when the human asks for something else.
7. Signals can disagree (churned by recency but still clicking emails). Surface the
   conflict explicitly and let it change the treatment — attention is cheaper than
   discounts.
"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _dispatch_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Route a Gemini function call to the right platform wrapper."""
    try:
        if name == "query_customers":
            return databricks_tool.query_customers(**args)
        if name == "run_readonly_sql":
            return databricks_tool.run_readonly_sql(**args)
        if name == "list_orders":
            return shopify_tool.list_orders(**args)
        if name == "list_products":
            return shopify_tool.list_products(**args)
        if name == "create_discount":
            return shopify_tool.create_discount(**args)
        if name == "trigger_campaign":
            return bloomreach_tool.trigger_campaign(**args)
        if name == "resolve_customer":
            return profile_tool.resolve_customer(**args)
        return {"error": f"unknown tool: {name}"}
    except Exception as exc:  # surface tool failures to the model, don't crash
        return {"error": str(exc)}


def run_agent(history: list[dict[str, str]]) -> dict[str, Any]:
    """Run the full agent loop until the model produces a final answer.

    history: [{role: 'user'|'model', text: ...}, ...] (last message is the new one)
    Returns {'reply': str, 'tool_events': [...], 'mode': ...}.
    """
    client = _get_client()
    contents: list[types.Content] = []
    for msg in history:
        role = "model" if msg["role"] == "model" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["text"])]))

    tool_events: list[dict[str, Any]] = []

    for _ in range(8):  # hard cap on tool-call rounds
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=ALL_TOOLS)],
                temperature=0.3,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts if candidate.content else []
        function_calls = [p.function_call for p in parts if p.function_call]

        if not function_calls:
            reply = response.text or "(empty response)"
            return {"reply": reply, "tool_events": tool_events}

        # Append the model's turn containing its function calls
        contents.append(candidate.content)

        # Execute every requested call, then feed results back
        result_parts: list[types.Part] = []
        for call in function_calls:
            args = dict(call.args or {})
            result = _dispatch_tool(call.name, args)
            tool_events.append({"tool": call.name, "args": args, "result": result})
            result_parts.append(
                types.Part.from_function_response(name=call.name, response=result)
            )
        contents.append(types.Content(role="user", parts=result_parts))

    return {
        "reply": "I stopped after too many tool rounds — try narrowing the request.",
        "tool_events": tool_events,
    }
