"""In-memory state so the mock services feel like a real system within a session."""

import itertools
import time

SESSIONS: dict[str, list] = {}

# emails of customers the agent has activated in this session
ACTIVATED: set[str] = set()

# discount codes created in this session: {code: {percent, segment, emails}}
DISCOUNTS: dict[str, dict] = {}

_campaign_counter = itertools.count(1)


def next_campaign_id() -> int:
    return next(_campaign_counter)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
