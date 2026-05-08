import os
import logging
from app.models.document_model import Document
from config import config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.mode = os.environ.get("AI_MODE", "mock").lower()

        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

        self.client = None
        if self.api_key and self.endpoint:
            try:
                from openai import AzureOpenAI

                self.client = AzureOpenAI(
                    api_key=self.api_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint=self.endpoint,
                )
            except ImportError:
                logger.error("openai package is not installed. Please install it using 'pip install openai'.")
            except TypeError as exc:
                logger.error("Azure OpenAI client could not be created (dependency mismatch?): %s", exc)
                self.client = None

    def chat(self, query: str) -> dict:
        if self.mode == "azure":
            return self._azure_chat(query)
        return self._mock_chat(query)

    def _mock_chat(self, query: str) -> dict:
        query_lower = query.lower()
        db_keywords = ["product", "price", "sales", "revenue", "top", "sell", "stock", "forecast", "order"]
        rag_keywords = ["policy", "return", "document", "terms", "guide"]

        route = "fallback"
        if any(kw in query_lower for kw in db_keywords):
            route = "database"
        elif any(kw in query_lower for kw in rag_keywords):
            route = "documents"

        return self._route_chat(query, route, is_mock=True)

    def _azure_chat(self, query: str) -> dict:
        if not self.client or not self.deployment_name:
            logger.error("Azure OpenAI is not configured properly.")
            return {
                "response": "Error: Azure OpenAI is not configured.",
                "agent": "System Error",
                "confidence": 0.0,
                "source": "system"
            }

        query_lower = query.lower()
        db_keywords = ["product", "price", "sales", "revenue", "top", "sell", "stock", "forecast", "order"]
        rag_keywords = ["policy", "return", "document", "terms", "guide"]

        route = "fallback"
        if any(kw in query_lower for kw in db_keywords):
            route = "database"
        elif any(kw in query_lower for kw in rag_keywords):
            route = "documents"

        return self._route_chat(query, route, is_mock=False)

    def _route_chat(self, query: str, route: str, is_mock: bool) -> dict:
        if route == "database":
            agent = "data"
            source = "database"
            from app.services import order_service, product_service
            summary = order_service.get_orders_summary()
            products = product_service.get_all_products()
            top_products = sorted(products, key=lambda x: x.popularity_score, reverse=True)[:5]
            
            context = f"Database Summary: {summary}.\nTop Products: " + ", ".join([f"{p.name} (${p.discounted_price or p.price})" for p in top_products])
            
            if is_mock:
                response = f"[Mock] Data Context: {context}. Question: {query}"
            else:
                prompt = f"Answer the user's question based on the following database information.\n\nContext: {context}\n\nQuestion: {query}"
                response = self._call_llm(prompt, "You are a helpful database-aware retail assistant. Do not mention that you are an AI or using a database explicitly.")

        elif route == "documents":
            agent = "rag"
            source = "documents"
            from app.services.agents.document_agent import document_agent
            result = document_agent.answer_question(query, use_openai=not is_mock)
            response = result.get("response", "I searched the uploaded documents but couldn't find an answer to your query.")
            if is_mock and response:
                response = f"[Mock] {response}"

        else:
            agent = "general"
            source = "fallback"
            if is_mock:
                response = "I'm your mock assistant. Try asking about 'sales', 'products', or a 'return policy'."
            else:
                response = self._call_llm(query, "You are a helpful retail assistant.")

        return {
            "agent": agent,
            "response": response,
            "source": source
        }

    def _call_llm(self, prompt: str, system_message: str) -> str:
        try:
            logger.info("Calling Azure OpenAI...")
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"

ai_service = AIService()
