import redis
import requests
from bs4 import BeautifulSoup
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
CACHE_EXPIRY = int(os.getenv("CACHE_EXPIRY_HOURS", 24)) * 3600  # Convert hours to seconds

# Initialize Redis client (will be None if Redis is not available)
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=2
    )
    # Test connection
    redis_client.ping()
    print("Redis connected successfully")
except Exception as e:
    print(f"Redis not available: {e}. Caching disabled.")
    redis_client = None


def scrape_website(url: str, use_cache: bool = True) -> str:
    """
    Scrape a website and cache the result in Redis.
    
    Args:
        url: The URL to scrape
        use_cache: Whether to use cached data if available
    
    Returns:
        Scraped text content
    """
    cache_key = f"scrape:{url}"
    
    # Try to get from cache if Redis is available and caching is enabled
    if redis_client and use_cache:
        try:
            cached_content = redis_client.get(cache_key)
            if cached_content:
                print(f"Cache hit for {url}")
                return cached_content
        except Exception as e:
            print(f"Redis get error: {e}")
    
    # Scrape the website
    try:
        print(f"Scraping {url}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Cache the result if Redis is available
        if redis_client:
            try:
                redis_client.setex(cache_key, CACHE_EXPIRY, text)
                print(f"Cached content for {url} (expires in {CACHE_EXPIRY/3600} hours)")
            except Exception as e:
                print(f"Redis set error: {e}")
        
        return text
        
    except requests.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error scraping {url}: {e}")
        return ""


def clear_cache(url: str = None):
    """
    Clear cached content for a specific URL or all cached content.
    
    Args:
        url: Specific URL to clear, or None to clear all scrape cache
    """
    if not redis_client:
        print("Redis not available")
        return
    
    try:
        if url:
            cache_key = f"scrape:{url}"
            redis_client.delete(cache_key)
            print(f"Cleared cache for {url}")
        else:
            # Clear all scrape cache
            keys = redis_client.keys("scrape:*")
            if keys:
                redis_client.delete(*keys)
                print(f"Cleared {len(keys)} cached entries")
            else:
                print("No cached entries found")
    except Exception as e:
        print(f"Error clearing cache: {e}")


def get_cache_info():
    """Get information about cached entries"""
    if not redis_client:
        return {"status": "Redis not available", "cached_urls": []}
    
    try:
        keys = redis_client.keys("scrape:*")
        cached_urls = []
        for key in keys:
            ttl = redis_client.ttl(key)
            url = key.replace("scrape:", "")
            cached_urls.append({
                "url": url,
                "expires_in_seconds": ttl
            })
        
        return {
            "status": "connected",
            "total_cached": len(cached_urls),
            "cached_urls": cached_urls
        }
    except Exception as e:
        return {"status": f"Error: {e}", "cached_urls": []}
