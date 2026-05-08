"""
Lightweight router for directing queries to appropriate agents.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Simple router that directs queries to appropriate agents based on keywords.
    """

    def __init__(self):
        """Initialize the router with keyword mappings."""
        self.agent_keywords = {
            "document_assistant": [
                "document", "pdf", "manual", "guide", "policy", "faq", "help",
                "support", "return", "terms", "how to", "explain", "search"
            ],
            "data_analyst": [
                "sales", "revenue", "analytics", "report", "dashboard", "kpi",
                "top product", "best selling", "category", "stock", "inventory",
                "order", "customer", "performance", "metrics"
            ],
            "ml_expert": [
                "forecast", "predict", "demand", "future", "trend", "anomaly",
                "model", "accuracy", "machine learning", "ml", "prediction",
                "anomalies", "unusual", "spike"
            ]
        }

    def route_query(self, query: str) -> Dict:
        """
        Route a query to the most appropriate agent.

        Args:
            query: User's query

        Returns:
            Agent response dictionary
        """
        query_lower = query.lower().strip()

        if not query_lower:
            return {
                "agent": "System",
                "response": "Please provide a question or query.",
                "confidence": 0.0
            }

        # Score each agent based on keyword matches
        scores = {}
        for agent, keywords in self.agent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            scores[agent] = score

        # Find the agent with the highest score
        best_agent = max(scores, key=scores.get)
        max_score = scores[best_agent]

        # If no keywords match, default to the document assistant so RAG can answer
        # general knowledge questions once documents have been uploaded.
        if max_score == 0:
            best_agent = "document_assistant"

        logger.info(f"Routed query '{query[:50]}...' to {best_agent} (score: {max_score})")

        # Route to the appropriate agent
        try:
            if best_agent == "document_assistant":
                from app.services.agents.document_agent import document_agent
                return document_agent.answer_question(query)
            elif best_agent == "data_analyst":
                from app.services.agents.data_analyst_agent import data_analyst_agent
                return data_analyst_agent.answer_question(query)
            elif best_agent == "ml_expert":
                from app.services.agents.ml_expert_agent import ml_expert_agent
                return ml_expert_agent.answer_question(query)
            else:
                return {
                    "agent": "System",
                    "response": "Unable to route your query to an appropriate agent.",
                    "confidence": 0.0
                }
        except Exception as e:
            logger.error(f"Error routing to {best_agent}: {e}")
            return {
                "agent": "System",
                "response": f"Sorry, I encountered an error processing your query: {str(e)}",
                "confidence": 0.0
            }

    def get_agent_info(self) -> Dict:
        """
        Get information about available agents.

        Returns:
            Dictionary with agent information
        """
        return {
            "agents": {
                "document_assistant": {
                    "purpose": "Handles document search and FAQ retrieval using RAG",
                    "keywords": self.agent_keywords["document_assistant"]
                },
                "data_analyst": {
                    "purpose": "Answers analytics questions using database queries",
                    "keywords": self.agent_keywords["data_analyst"]
                },
                "ml_expert": {
                    "purpose": "Explains ML forecasts and anomaly detection",
                    "keywords": self.agent_keywords["ml_expert"]
                }
            }
        }


# Global instance
agent_router = AgentRouter()
