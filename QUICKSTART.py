"""
Quick Start Guide for the Smart Retail Assistant AI System
===========================================================
"""

# 1. SETUP
# --------
# Install dependencies:
# pip install -r requirements.txt

# Create upload directories:
# mkdir -p uploads/pdfs
# mkdir -p vectorstore/faiss_index

# Run the app:
# python run.py


# 2. ADMIN PORTAL - UPLOAD A DOCUMENT
# ------------------------------------
# 1. Go to http://localhost:5000/admin/assistant
# 2. Upload a PDF file (e.g., return_policy.pdf, faq.pdf)
# 3. The DocumentAssistantAgent will:
#    - Extract text using PyMuPDF
#    - Split into chunks (500 words, 100 word overlap)
#    - Generate embeddings using sentence-transformers
#    - Store in FAISS vector index
#    - Save metadata to metadata.json


# 3. QUERY THE SYSTEM
# -------------------
# Send a POST request to /api/agent-chat:

import requests
import json

# Example 1: Analytics Query
response = requests.post(
    "http://localhost:5000/api/agent-chat",
    json={"message": "What are our top selling products?"}
)
print("Analytics Response:")
print(json.dumps(response.json(), indent=2))

# Example 2: Forecast Query
response = requests.post(
    "http://localhost:5000/api/agent-chat",
    json={"message": "What's the demand forecast for Q4?"}
)
print("\nForecast Response:")
print(json.dumps(response.json(), indent=2))

# Example 3: Document Query (RAG)
response = requests.post(
    "http://localhost:5000/api/agent-chat",
    json={"message": "How do I return a product?"}
)
print("\nRAG Response:")
print(json.dumps(response.json(), indent=2))


# 4. API UPLOAD DOCUMENT
# ----------------------
# Upload via API:

with open("return_policy.pdf", "rb") as f:
    files = {"document": f}
    response = requests.post(
        "http://localhost:5000/api/upload-document",
        files=files
    )
print("\nUpload Response:")
print(json.dumps(response.json(), indent=2))


# 5. AGENT RESPONSES
# ------------------
# All agents return responses in this format:
#
# {
#     "agent": "Data Analyst" | "Document Assistant" | "ML Expert",
#     "response": "...",
#     "confidence": 0.0 to 1.0,
#     "sources": [...] (optional, for RAG)
# }


# 6. FOLDER STRUCTURE AFTER SETUP
# --------------------------------
# smart_retail_assistant_new/
#   ├── app/
#   │   ├── services/
#   │   │   ├── agents/
#   │   │   │   ├── __init__.py
#   │   │   │   ├── document_agent.py
#   │   │   │   ├── data_analyst_agent.py
#   │   │   │   ├── ml_expert_agent.py
#   │   │   │   └── router.py
#   │   │   ├── rag/
#   │   │   │   ├── __init__.py
#   │   │   │   ├── embedder.py
#   │   │   │   ├── pdf_processor.py
#   │   │   │   └── faiss_store.py
#   │   │   ├── ai_service.py
#   │   │   └── ...other services...
#   │   └── ...rest of app...
#   ├── uploads/
#   │   └── pdfs/
#   │       └── return_policy.pdf
#   ├── vectorstore/
#   │   └── faiss_index/
#   │       ├── index.faiss
#   │       └── metadata.json
#   ├── requirements.txt (updated)
#   ├── ARCHITECTURE.md (new)
#   └── ...


# 7. TESTING THE AGENTS
# ---------------------

# Test data analyst agent directly:
from app.services.agents.data_analyst_agent import data_analyst_agent
response = data_analyst_agent.answer_question("What are our sales this month?")
print("Direct Agent Response:")
print(json.dumps(response, indent=2))

# Test document agent directly:
from app.services.agents.document_agent import document_agent
# (requires uploaded documents first)
results = document_agent.search_documents("return policy")
print("Document Search Results:")
print(json.dumps(results, indent=2, default=str))

# Test router:
from app.services.agents.router import agent_router
response = agent_router.route_query("What's the revenue breakdown by category?")
print("Router Response:")
print(json.dumps(response, indent=2))


# 8. CUSTOMIZATION EXAMPLES
# -------------------------

# Add a new agent:
# 1. Create app/services/agents/custom_agent.py
# 2. Implement CustomAgent class with answer_question() method
# 3. Update router.py to include keywords for CustomAgent
# 4. The system will automatically route matching queries

# Add new analytics functions:
# 1. Add function to app/services/analytics_service.py
# 2. Call it from DataAnalystAgent.answer_question()
# 3. No need to modify anything else

# Use Azure OpenAI instead of OpenAI:
# 1. Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
# 2. DocumentAssistantAgent will automatically use Azure OpenAI
# 3. Configure EMBEDDING_MODEL if using Azure Embedding API


# 9. PRODUCTION DEPLOYMENT
# -------------------------

# Local (SQLite + FAISS):
# - No setup needed, everything works out of the box
# - FAISS index stored in vectorstore/faiss_index/
# - Database stored in instance/retail.db

# Azure (Azure SQL + Azure Storage):
# 1. Update DATABASE_URL to Azure SQL connection string
# 2. Move vectorstore/ to Azure Blob Storage (optional, but recommended)
# 3. Set Azure OpenAI credentials
# 4. Deploy Flask app to Azure App Service
# 5. All agents will work seamlessly


# 10. MONITORING & DEBUGGING
# ---------------------------

# Check FAISS index stats:
from app.services.agents.document_agent import document_agent
stats = document_agent.get_stats()
print("Vector Store Stats:")
print(stats)

# Enable logging to see what's happening:
import logging
logging.basicConfig(level=logging.DEBUG)
