# backend/microservices/news_storage.py

import os
import datetime
from supabase import create_client, Client  # Make sure you're using supabase-py or your preferred client
from dotenv import load_dotenv

load_dotenv('../../.env')

# Use your service key here for secure server-side operations.
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def store_article_in_supabase(article):
    """
    Inserts a news article into the Supabase news_articles table if it doesn't already exist.
    Uniqueness is enforced by the URL field (which is UNIQUE in the table).
    """
    # Check if the article already exists using the URL as unique identifier.
    existing = supabase.table("news_articles").select("*").eq("url", article["url"]).execute()
    if existing.data and len(existing.data) > 0:
        # Article already exists; return its id.
        return existing.data[0]["id"]
    else:
        # Insert a new article.
        result = supabase.table("news_articles").insert({
            "title": article["title"],
            "summary": article.get("summary", ""),
            "content": article.get("content", ""),
            # The source can be a dict (from API) or a plain string.
            "source": article["source"]["name"] if isinstance(article.get("source"), dict) else article["source"],
            "published_at": article["publishedAt"],
            "url": article["url"],
            "image": article.get("urlToImage", "")
        }).execute()
        return result.data[0]["id"]

def log_user_search(user_id, news_id, session_id):
    """
    Logs a search event by inserting a record into the user_search_history join table.
    """
    result = supabase.table("user_search_history").insert({
        "user_id": user_id,
        "news_id": news_id,
        "searched_at": datetime.datetime.utcnow().isoformat(),
        "session_id": session_id,
    }).execute()
    return result