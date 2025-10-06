"""
TMDB API 代理配置文件
"""
import os
from dotenv import load_dotenv
load_dotenv()

TMDB_BASE_URL = "https://api.themoviedb.org"

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 