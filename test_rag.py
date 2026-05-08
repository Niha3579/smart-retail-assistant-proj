import os
from app import create_app
from app.services.rag_service import rag_service
from app.services.ai_service import ai_service

app = create_app()

with app.app_context():
    print("Testing RAG Add Document...")
    rag_service.add_document("test.txt", "This is a test document containing the return policy: Items can be returned within 30 days.")
    
    print("Testing RAG Search...")
    results = rag_service.search("return policy")
    print(f"RAG Search Results: {results}")
    
    print("Testing AI Service Chat (mock RAG route)...")
    chat_resp = ai_service.chat("What is the return policy?")
    print(f"Chat Response: {chat_resp}")

    print("Testing AI Service Chat (mock Database route)...")
    chat_resp_db = ai_service.chat("What are the top selling products?")
    print(f"Chat Response DB: {chat_resp_db}")
