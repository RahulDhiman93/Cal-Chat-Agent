"""Configuration settings for the CalBolt Chat Agent."""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings configuration."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="OpenAI API key for GPT function calling"
    )
    
    # Cal.com Configuration
    calcom_api_key: str = Field(
        default_factory=lambda: os.getenv("CALCOM_API_KEY", ""),
        description="Cal.com API key for calendar operations"
    )
    calcom_base_url: str = Field(
        default="https://api.cal.com/v2",
        description="Base URL for Cal.com API"
    )
    
    # User Configuration
    user_email: str = Field(
        default_factory=lambda: os.getenv("USER_EMAIL", ""),
        description="User email for calendar operations"
    )
    
    # Application Configuration
    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true",
        description="Debug mode flag"
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host for the web server"
    )
    port: int = Field(
        default=8000,
        description="Port for the web server"
    )
    
    # Model Configuration
    openai_model: str = Field(
        default="gpt-4",
        description="OpenAI model to use for chat completions"
    )
    temperature: float = Field(
        default=0.7,
        description="Temperature for OpenAI model responses"
    )
    max_tokens: int = Field(
        default=1000,
        description="Maximum tokens for OpenAI model responses"
    )
    
    class Config:
        """Pydantic config."""
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

    def validate_required_settings(self) -> None:
        """Validate that all required settings are provided."""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if not self.calcom_api_key:
            errors.append("CALCOM_API_KEY is required")
            
        if not self.user_email:
            errors.append("USER_EMAIL is required")
        
        if errors:
            raise ValueError(f"Missing required configuration: {', '.join(errors)}")


# Global settings instance
settings = Settings()
