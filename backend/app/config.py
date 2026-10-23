from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database and File Storage
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "./uploads"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # LLM (Ollama)
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1:8"

    # Auth: No default for the secret so the app will refuse to start without one
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
