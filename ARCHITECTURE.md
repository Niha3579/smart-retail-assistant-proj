"""
MAISON Smart Retail Assistant - Refactored Architecture
========================================================

This is a complete refactor of the Smart Retail Assistant AI architecture.
The system now uses a pure Python, modular, production-friendly design.

ARCHITECTURE OVERVIEW
====================

1. AGENTS
---------
The system uses three specialized agents:

- DocumentAssistantAgent: Handles PDF search and Q&A using RAG
  Location: app/services/agents/document_agent.py
  
- DataAnalystAgent: Answers analytics questions using database queries
  Location: app/services/agents/data_analyst_agent.py
  
- MLExpertAgent: Explains ML forecasts and anomaly detection
  Location: app/services/agents/ml_expert_agent.py


2. ROUTING
----------
A lightweight keyword-based router directs queries to appropriate agents.
Location: app/services/agents/router.py

No autonomous orchestration, no complex frameworks - just simple routing.


3. RAG IMPLEMENTATION
--------------------
The RAG system uses:

- PDFProcessor: Extracts text from PDFs using PyMuPDF
  Location: app/services/rag/pdf_processor.py
  
- Embedder: Generates embeddings using sentence-transformers (all-MiniLM-L6-v2)
  Location: app/services/rag/embedder.py
  
- FAISSStore: Manages vector store for semantic search
  Location: app/services/rag/faiss_store.py
  
- DocumentAssistantAgent: Orchestrates the pipeline
  Location: app/services/agents/document_agent.py


4. FILE STRUCTURE
-----------------
app/
  services/
    agents/                    # Agent implementations
      __init__.py
      document_agent.py        # DocumentAssistantAgent
      data_analyst_agent.py    # DataAnalystAgent
      ml_expert_agent.py       # MLExpertAgent
      router.py                # Query router
    rag/                       # RAG pipeline components
      __init__.py
      embedder.py              # Text embeddings
      pdf_processor.py         # PDF text extraction
      faiss_store.py           # Vector store

uploads/
  pdfs/                        # Uploaded PDF documents

vectorstore/
  faiss_index/                 # FAISS index and metadata
    index.faiss
    metadata.json


5. API ENDPOINTS
----------------
POST /api/agent-chat          # Route query to appropriate agent
POST /api/upload-document     # Upload PDF for RAG
DELETE /api/delete-document/  # Remove document from vector store


6. FEATURES
-----------
✓ Multi-agent system with keyword-based routing
✓ RAG with FAISS vector store
✓ PDF text extraction and chunking
✓ Semantic search with sentence-transformers
✓ Predefined analytics functions (no dynamic SQL)
✓ ML model explanation
✓ Azure OpenAI integration (fallback to OpenAI)
✓ SQLite local (Azure SQL ready)
✓ Production-friendly, easy to debug


7. TECH STACK
-------------
- Flask
- SQLAlchemy
- scikit-learn (ML models)
- FAISS (vector search)
- sentence-transformers (embeddings)
- PyMuPDF (PDF processing)
- OpenAI/Azure OpenAI API


8. INSTALLATION
---------------
1. Install dependencies:
   pip install -r requirements.txt

2. Set environment variables:
   - EMBEDDING_MODEL=all-MiniLM-L6-v2 (optional, default)
   - AZURE_OPENAI_API_KEY (optional for Azure)
   - OPENAI_API_KEY (fallback)

3. Create upload directories:
   mkdir -p uploads/pdfs
   mkdir -p vectorstore/faiss_index

4. Run the application:
   python run.py


9. USAGE
--------
Users/Admins can interact with the AI system via:

- /api/agent-chat (POST): Send a query to the AI system
  Request: {"message": "What are the top selling products?"}
  Response: {"agent": "Data Analyst", "response": "...", "confidence": 0.9}

- /api/upload-document (POST): Upload a PDF
  Form-data: {"document": <PDF file>}
  
- /api/delete-document/<filename> (DELETE): Delete a document


10. EXAMPLE FLOWS
-----------------

Query: "What's our Q4 revenue forecast?"
→ Router identifies "forecast" keyword
→ Routes to MLExpertAgent
→ Returns demand forecast explanation

Query: "How do I return an item?"
→ Router identifies "return" keyword
→ Routes to DocumentAssistantAgent
→ Searches vector store for return policy PDFs
→ Generates answer using OpenAI

Query: "Show me low stock products"
→ Router identifies "stock" keyword
→ Routes to DataAnalystAgent
→ Runs predefined analytics function
→ Returns low stock alerts


11. DEPLOYMENT NOTES
--------------------
- Local: Uses SQLite and local FAISS index
- Azure: Update DATABASE_URL for Azure SQL, vectorstore paths can stay local or use Azure Storage
- FAISS is CPU-based and works well for 1M+ vectors
- For larger deployments (10M+ vectors), consider Azure Cognitive Search


12. CUSTOMIZATION
------------------
To add new agents:
1. Create app/services/agents/new_agent.py
2. Implement agent class with answer_question() method
3. Add keywords in router.py
4. Router will automatically use new agent

To modify analytics functions:
1. Edit app/services/analytics_service.py
2. Add new predefined functions (avoid dynamic SQL)
3. Reference in DataAnalystAgent.answer_question()


13. NOTES
---------
- No LangChain, CrewAI, Autogen, LangGraph, or MCP
- No async/await complexity
- No Redis or caching layer (can add later if needed)
- All components are synchronous and easy to debug
- Vector store supports full Azure migration
- FAISS vectors persist locally (production-ready)
"""
