"""
Legacy agent router - replaced by services/agents/router.py
This file is kept for backward compatibility but now delegates to the new router.
"""
import logging
from app.services.agents.router import agent_router

logger = logging.getLogger(__name__)


def route_query(query: str) -> dict:
    """
    Route query using the new agent router system.
    """
    return agent_router.route_query(query)
