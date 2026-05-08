import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///retail.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280}
    
    # AI & Analytics Config
    AI_MODE = os.environ.get("AI_MODE", "mock")
    POWER_BI_URL = os.environ.get("POWER_BI_URL", "")
    
    # Azure OpenAI
    AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")

    # OpenAI (fallback chat only)
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

    # Azure AI Search — field names must match your index schema
    AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY", "")
    AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "")
    AZURE_SEARCH_VECTOR_FIELD = os.environ.get("AZURE_SEARCH_VECTOR_FIELD", "contentVector")
    AZURE_SEARCH_CONTENT_FIELD = os.environ.get("AZURE_SEARCH_CONTENT_FIELD", "content")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("AZURE_SQL_URL") or os.environ.get("DATABASE_URL")

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
