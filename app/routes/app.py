import logging
import os
import uuid

from flask import Blueprint, jsonify, request
from flask_login import login_required
from werkzeug.utils import secure_filename

from app import db
from app.models.document_model import Document
from app.services.agents.document_agent import document_agent

logger = logging.getLogger(__name__)
rag_bp = Blueprint("rag", __name__)


@rag_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    """Upload a document; chunks are embedded (Azure OpenAI) and indexed in Azure AI Search."""
    file = request.files.get("file") or request.files.get("document")
    if not file:
        return jsonify({"logs": ["Error: No file provided."]}), 400

    if not file.filename:
        return jsonify({"logs": ["Error: Empty filename."]}), 400

    supported_exts = {".pdf", ".txt", ".csv"}
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in supported_exts:
        return jsonify({"logs": ["Error: Only PDF, TXT, and CSV files are supported by the RAG pipeline."]}), 400

    try:
        upload_dir = os.path.join("uploads", "documents")
        os.makedirs(upload_dir, exist_ok=True)

        original_name = secure_filename(file.filename)
        stored_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
        file_path = os.path.join(upload_dir, stored_name)
        file.save(file_path)

        success = document_agent.upload_document(file_path, stored_name)
        if not success:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"logs": [f"Failed to process {stored_name}."]}), 500

        doc = Document(
            filename=stored_name,
            content=f"{ext.lstrip('.').upper()} uploaded and indexed at {stored_name}",
        )
        db.session.add(doc)
        db.session.commit()

        return jsonify({
            "logs": [
                f"Processing: {stored_name}",
                "Extracted and indexed successfully.",
            ],
            "chunks": document_agent.get_stats().get("total_vectors", 0),
            "filename": stored_name,
        })
    except Exception as exc:
        logger.error(f"Error uploading document: {exc}")
        return jsonify({"logs": [f"Error: {exc}"]}), 500


@rag_bp.route("/chat", methods=["POST"])
def chat():
    """Answer a question using Azure AI Search retrieval and Azure OpenAI chat."""
    payload = request.get_json(silent=True) or {}
    user_query = payload.get("message", "").strip()
    if not user_query:
        return jsonify({"answer": "Please provide a message.", "logs": ["Chat Error: missing message"]}), 400

    try:
        result = document_agent.answer_question(user_query)
        return jsonify({
            "answer": result.get("response", ""),
            "agent": result.get("agent", "Document Assistant"),
            "confidence": result.get("confidence", 0.0),
            "sources": result.get("sources", []),
            "logs": [
                f"User Question: {user_query}",
                "Querying Azure AI Search index...",
                "Generating response...",
            ],
        })
    except Exception as exc:
        logger.error(f"Chat Error: {exc}")
        return jsonify({
            "answer": "I encountered an error processing your request.",
            "logs": [f"Chat Error: {exc}"],
        }), 500
