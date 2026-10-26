from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # Database and File Storage
    database_url: str = "sqlite:///./app.db"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    CHROMA_PATH: str = os.environ.get("CHROMA_PATH", "/chroma_data")
    COLLECTION_NAME: str = os.environ.get("COLLECTION_NAME", "documents_cosine")

    # RAG Configuration
    MAX_RESULTS: int = int(os.environ.get("MAX_RESULTS", "5"))
    MAX_DISTANCE: float = float(os.environ.get("MAX_DISTANCE", "0.9"))
    CONFIDENCE_THRESHOLD: float = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.5"))
    MEDIUM_CONFIDENCE_THRESHOLD: float = float(
        os.environ.get("MEDIUM_CONFIDENCE_THRESHOLD", "0.8")
    )

    # LLM (Ollama)
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:14b"

    # Auth: No default for the secret so the app will refuse to start without one
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
