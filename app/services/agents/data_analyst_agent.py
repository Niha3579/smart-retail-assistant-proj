"""
Data Analyst Agent for answering admin analytics questions using predefined functions.
"""
import logging
from typing import Dict
from app.services.analytics_service import (
    get_dashboard_kpis,
    get_sales_trend,
    get_revenue_by_category,
    get_anomalies
)
from app.services import product_service, order_service

logger = logging.getLogger(__name__)


class DataAnalystAgent:
    """
    Agent for answering analytics questions using database queries and predefined functions.
    """

    def answer_question(self, query: str) -> Dict:
        """
        Answer analytics questions using predefined functions.

        Args:
            query: User's analytics question

        Returns:
            Response dictionary with answer and metadata
        """
        query_lower = query.lower()

        try:
            if self._is_revenue_question(query_lower):
                return self._answer_revenue_question(query_lower)
            elif self._is_top_products_question(query_lower):
                return self._answer_top_products_question(query_lower)
            elif self._is_stock_question(query_lower):
                return self._answer_stock_question(query_lower)
            elif self._is_category_question(query_lower):
                return self._answer_category_question(query_lower)
            elif self._is_sales_trend_question(query_lower):
                return self._answer_sales_trend_question(query_lower)
            elif self._is_anomaly_question(query_lower):
                return self._answer_anomaly_question(query_lower)
            else:
                return self._answer_general_analytics_question(query_lower)

        except Exception as e:
            logger.error(f"Error in data analyst agent: {e}")
            return {
                "agent": "Data Analyst",
                "response": f"Sorry, I encountered an error while analyzing the data: {str(e)}",
                "confidence": 0.0
            }

    def _is_revenue_question(self, query: str) -> bool:
        """Check if query is about revenue."""
        keywords = ["revenue", "sales", "income", "earnings", "money", "amount"]
        return any(kw in query for kw in keywords)

    def _is_top_products_question(self, query: str) -> bool:
        """Check if query is about top/best selling products."""
        keywords = ["top", "best", "selling", "popular", "most"]
        return any(kw in query for kw in keywords)

    def _is_stock_question(self, query: str) -> bool:
        """Check if query is about stock/inventory."""
        keywords = ["stock", "inventory", "low", "out of stock", "available"]
        return any(kw in query for kw in keywords)

    def _is_category_question(self, query: str) -> bool:
        """Check if query is about categories."""
        keywords = ["category", "categories", "by category", "segment"]
        return any(kw in query for kw in keywords)

    def _is_sales_trend_question(self, query: str) -> bool:
        """Check if query is about sales trends."""
        keywords = ["trend", "over time", "monthly", "weekly", "daily"]
        return any(kw in query for kw in keywords)

    def _is_anomaly_question(self, query: str) -> bool:
        """Check if query is about anomalies."""
        keywords = ["anomaly", "unusual", "spike", "outlier", "abnormal"]
        return any(kw in query for kw in keywords)

    def _answer_revenue_question(self, query: str) -> Dict:
        """Answer revenue-related questions."""
        kpis = get_dashboard_kpis()
        trend = get_sales_trend(days=30)

        if "monthly" in query or "month" in query:
            # Calculate monthly totals from trend data
            if trend and trend["revenue"]:
                total_monthly = sum(trend["revenue"])
                avg_monthly = total_monthly / len(trend["revenue"]) if trend["revenue"] else 0
                response = f"Monthly revenue analysis: Total revenue over last 30 days: ₹{total_monthly:,.2f}. Average daily revenue: ₹{avg_monthly:,.2f}."
            else:
                response = f"Total revenue: ₹{kpis['total_revenue']:,.2f}. Monthly breakdown not available."
        else:
            response = f"Current revenue metrics: Total revenue: ₹{kpis['total_revenue']:,.2f}, Total orders: {kpis['total_orders']}. Top revenue driver: {kpis['top_product']}."

        return {
            "agent": "Data Analyst",
            "response": response,
            "confidence": 0.9
        }

    def _answer_top_products_question(self, query: str) -> Dict:
        """Answer questions about top products."""
        kpis = get_dashboard_kpis()
        products = product_service.get_all_products()

        # Sort by popularity score (assuming this correlates with sales)
        top_products = sorted(products, key=lambda p: p.popularity_score, reverse=True)[:5]

        response_parts = [f"Top 5 products by popularity:"]
        for i, product in enumerate(top_products, 1):
            response_parts.append(f"{i}. {product.name} - Popularity: {product.popularity_score}")

        response = " ".join(response_parts)

        return {
            "agent": "Data Analyst",
            "response": response,
            "confidence": 0.85
        }

    def _answer_stock_question(self, query: str) -> Dict:
        """Answer stock/inventory questions."""
        kpis = get_dashboard_kpis()
        products = product_service.get_all_products()

        low_stock_products = [p for p in products if p.stock_quantity <= 20 and p.is_active]

        if "low" in query or "out" in query:
            if low_stock_products:
                response = f"Low stock alert: {len(low_stock_products)} products need attention. "
                examples = low_stock_products[:3]
                response += "Examples: " + ", ".join([f"{p.name} ({p.stock_quantity} left)" for p in examples])
            else:
                response = "All products are well-stocked. No low inventory alerts."
        else:
            total_stock = sum(p.stock_quantity for p in products if p.is_active)
            response = f"Inventory summary: {len(products)} active products, {total_stock} total units in stock, {len(low_stock_products)} products low on stock."

        return {
            "agent": "Data Analyst",
            "response": response,
            "confidence": 0.9
        }

    def _answer_category_question(self, query: str) -> Dict:
        """Answer category-related questions."""
        category_data = get_revenue_by_category()

        if category_data and category_data["labels"]:
            total_rev = sum(category_data["amounts"])
            response_parts = [f"Revenue by category (Total: ₹{total_rev:,.2f}):"]

            for label, amount in zip(category_data["labels"], category_data["amounts"]):
                percentage = (amount / total_rev * 100) if total_rev > 0 else 0
                response_parts.append(f"• {label}: ₹{amount:,.2f} ({percentage:.1f}%)")

            response = " ".join(response_parts)
        else:
            response = "Category revenue data not available."

        return {
            "agent": "Data Analyst",
            "response": response,
            "confidence": 0.85
        }

    def _answer_sales_trend_question(self, query: str) -> Dict:
        """Answer sales trend questions."""
        trend = get_sales_trend(days=30)

        if trend and trend["labels"]:
            revenues = trend["revenue"]
            avg_revenue = sum(revenues) / len(revenues) if revenues else 0
            max_revenue = max(revenues) if revenues else 0
            min_revenue = min(revenues) if revenues else 0

            response = f"Sales trend (last 30 days): Average daily revenue: ₹{avg_revenue:,.2f}, Peak: ₹{max_revenue:,.2f}, Lowest: ₹{min_revenue:,.2f}."
        else:
            response = "Sales trend data not available for the requested period."

        return {
            "agent": "Data Analyst",
            "response": response,
            "confidence": 0.8
        }

    def _answer_anomaly_question(self, query: str) -> Dict:
        """Answer anomaly-related questions."""
        anomalies = get_anomalies()

        if anomalies:
            high_severity = [a for a in anomalies if a["severity"] == "High"]
            response = f"Found {len(anomalies)} sales anomalies. {len(high_severity)} high-severity events detected. "

            if high_severity:
                example = high_severity[0]
                response += f"Example: {example['product_name']} on {example['date']} - ₹{example['revenue']:,.2f} revenue."
        else:
            response = "No significant sales anomalies detected in recent data."

        return {
            "agent": "Data Analyst",
            "response": response,
            "confidence": 0.8
        }

    def _answer_general_analytics_question(self, query: str) -> Dict:
        """Answer general analytics questions."""
        kpis = get_dashboard_kpis()

        response = f"Retail analytics overview: ₹{kpis['total_revenue']:,.2f} total revenue, {kpis['total_orders']} orders, {kpis['low_stock_count']} products low on stock. Top product: {kpis['top_product']}."

        return {
            "agent": "Data Analyst",
            "response": response,
            "confidence": 0.7
        }


# Global instance
data_analyst_agent = DataAnalystAgent()