from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Config:
    # Base paths
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # API Configuration
    API_HOST = os.getenv('API_HOST', 'localhost')
    API_PORT = int(os.getenv('API_PORT', 8080))
    
    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    
    # File paths relative to project root
    NEWS_DATA_DIR = BASE_DIR / 'data' / 'news'
    SUMMARIZED_NEWS_DIR = BASE_DIR / 'data' / 'summarized'
    
    # API Keys
    NEWS_API_KEY = os.getenv('NEWS_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    

    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    print("CORS_ORIGINS", CORS_ORIGINS)
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def get_news_data_path(cls) -> Path:
        """Returns the path to news data directory, creating it if it doesn't exist"""
        cls.NEWS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return cls.NEWS_DATA_DIR
    
    @classmethod
    def get_summarized_news_path(cls) -> Path:
        """Returns the path to summarized news directory, creating it if it doesn't exist"""
        cls.SUMMARIZED_NEWS_DIR.mkdir(parents=True, exist_ok=True)
        return cls.SUMMARIZED_NEWS_DIR