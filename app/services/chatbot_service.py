import logging
from typing import Dict

from flask_login import AnonymousUserMixin

from app.services import analytics_service, order_service, product_service

logger = logging.getLogger(__name__)


class ChatbotService:
    """Intent-based chatbot for FAQ, support, and database questions."""

    def __init__(self):
        self.faq_map = {
            "return": "Our standard return window is 7 days from delivery for unused products with original packaging.",
            "refund": "Refunds are initiated after return verification and usually reflect in 5-7 business days.",
            "delivery": "Standard delivery usually takes 3-5 business days depending on location.",
            "shipping": "Standard delivery usually takes 3-5 business days depending on location.",
            "payment": "We currently support secure checkout with mock payment flow in this demo app.",
            "cancel": "If an order is still in Pending status, it can be cancelled by contacting support from your account email.",
            "exchange": "Exchanges are supported for eligible products within the return period, subject to stock availability.",
            "account": "You can create an account from Register and sign in from Login to manage cart and orders.",
        }
        self.faq_keywords = set(self.faq_map.keys()) | {
            "policy", "faq", "help", "how", "what", "when", "where"
        }
        self.support_keywords = {
            "support", "issue", "problem", "not working", "failed", "error",
            "track", "status", "complaint", "agent", "representative", "speak"
        }
        self.database_keywords = {
            "database", "sales", "revenue", "kpi", "analytics", "order", "orders",
            "stock", "inventory", "product", "products", "top", "category", "trend"
        }

    def answer(self, query: str, user=None) -> Dict:
        query_lower = (query or "").strip().lower()
        if not query_lower:
            return self._response("Support Assistant", "Please ask a question so I can help you.", 0.0, "system")

        intent = self._detect_intent(query_lower)
        try:
            if intent == "faq":
                return self._answer_faq(query_lower)
            if intent == "support":
                return self._answer_support(query_lower, user)
            if intent == "database":
                return self._answer_database(query_lower)
            return self._response("Support Assistant", "I can help with FAQs, support queries, and database insights. Please ask one of these.", 0.5, "fallback")
        except Exception as exc:
            logger.error(f"ChatbotService failed for intent '{intent}': {exc}")
            return self._response("System", "Sorry, I ran into an issue while processing your query. Please try again.", 0.0, "error")

    def _detect_intent(self, query_lower: str) -> str:
        faq_score = sum(1 for kw in self.faq_keywords if kw in query_lower)
        support_score = sum(1 for kw in self.support_keywords if kw in query_lower)
        db_score = sum(1 for kw in self.database_keywords if kw in query_lower)
        if max(faq_score, support_score, db_score) == 0:
            return "fallback"
        if db_score >= support_score and db_score >= faq_score:
            return "database"
        if support_score >= faq_score:
            return "support"
        return "faq"

    def _answer_faq(self, query_lower: str) -> Dict:
        for key, answer in self.faq_map.items():
            if key in query_lower:
                return self._response("FAQ Assistant", answer, 0.9, "faq")
        return self._response(
            "FAQ Assistant",
            "I can help with returns, refunds, shipping, delivery, cancellation, exchange, and account questions.",
            0.5,
            "fallback",
        )

    def _answer_support(self, query_lower: str, user=None) -> Dict:
        user_is_logged_in = bool(user) and not isinstance(user, AnonymousUserMixin) and getattr(user, "is_authenticated", False)
        if "track" in query_lower or "status" in query_lower:
            if user_is_logged_in:
                orders = order_service.get_user_orders(user.id)
                if not orders:
                    return self._response("Support Assistant", "I could not find any past orders for your account.", 0.85, "support")
                latest = orders[0]
                return self._response(
                    "Support Assistant",
                    f"Your latest order is #{latest.id} and its current status is {latest.status}. You can view all orders in My Orders.",
                    0.9,
                    "support",
                )
            return self._response("Support Assistant", "Please log in to track your order status.", 0.9, "support")

        if "cancel" in query_lower:
            return self._response("Support Assistant", "To cancel an order, contact support with your order ID while it is still Pending.", 0.8, "support")

        if "refund" in query_lower or "return" in query_lower:
            return self._response("Support Assistant", "For refund or return support, share your order ID and reason. The support team can guide the next steps.", 0.8, "support")

        return self._response(
            "Support Assistant",
            "I can help with order tracking, cancellation, returns, and login issues. Tell me your issue and order ID if available.",
            0.5,
            "fallback",
        )

    def _answer_database(self, query_lower: str) -> Dict:
        if "top" in query_lower and ("product" in query_lower or "products" in query_lower):
            products = product_service.get_all_products(sort="rating")[:5]
            if not products:
                return self._response("Database Assistant", "No products found in the database.", 0.7, "database")
            msg = "Top products right now: " + ", ".join([p.name for p in products])
            return self._response("Database Assistant", msg, 0.85, "database")

        if "stock" in query_lower or "inventory" in query_lower:
            low_stock = product_service.get_low_stock_products()
            if not low_stock:
                return self._response("Database Assistant", "No low-stock alerts currently.", 0.8, "database")
            sample = ", ".join([f"{p.name} ({p.stock_quantity})" for p in low_stock[:5]])
            return self._response("Database Assistant", f"Low-stock products: {sample}.", 0.88, "database")

        if "revenue" in query_lower or "sales" in query_lower or "kpi" in query_lower:
            kpis = analytics_service.get_dashboard_kpis()
            return self._response(
                "Database Assistant",
                f"Current KPIs: Total revenue Rs. {kpis['total_revenue']:,.2f}, total orders {kpis['total_orders']}, low stock products {kpis['low_stock_count']}, top product {kpis['top_product']}.",
                0.9,
                "database",
            )

        trend = analytics_service.get_sales_trend(30)
        total_recent = sum(trend.get("revenue", [])) if trend else 0
        return self._response(
            "Database Assistant",
            f"From the last 30 days, tracked revenue is Rs. {total_recent:,.2f}. Ask for top products, stock alerts, or category insights for more detail.",
            0.5,
            "fallback",
        )

    @staticmethod
    def _response(agent: str, response: str, confidence: float, source: str) -> Dict:
        return {
            "agent": agent,
            "response": response,
            "confidence": confidence,
            "source": source,
        }


chatbot_service = ChatbotService()
