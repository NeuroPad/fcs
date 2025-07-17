import redis
import json
import hashlib
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service for improved performance"""
    
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour
        self.connect()
    
    def connect(self):
        """Initialize Redis connection"""
        try:
            # Try to connect to Redis
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory cache.")
            self.redis_client = None
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate a consistent cache key"""
        key_data = f"{prefix}:{'|'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
            
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Cache get error for key {key}: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis_client:
            return False
            
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            return self.redis_client.setex(key, ttl, serialized_value)
        except (redis.RedisError, json.JSONEncodeError) as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
            
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
            
        try:
            return bool(self.redis_client.exists(key))
        except redis.RedisError as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except redis.RedisError as e:
            logger.error(f"Cache clear pattern error for pattern {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected", "type": "fallback"}
            
        try:
            info = self.redis_client.info()
            return {
                "status": "connected",
                "type": "redis",
                "used_memory": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0)
            }
        except redis.RedisError as e:
            logger.error(f"Cache stats error: {e}")
            return {"status": "error", "type": "redis", "error": str(e)}


class ChatCacheService(CacheService):
    """Specialized cache service for chat operations"""
    
    def __init__(self):
        super().__init__()
        self.chat_ttl = 1800  # 30 minutes for chat responses
        self.session_ttl = 7200  # 2 hours for session data
    
    def get_chat_response(self, query: str, user_id: int, mode: str) -> Optional[Dict[str, Any]]:
        """Get cached chat response"""
        key = self._generate_key("chat_response", query, user_id, mode)
        return self.get(key)
    
    def set_chat_response(self, query: str, user_id: int, mode: str, response: Dict[str, Any]) -> bool:
        """Cache chat response"""
        key = self._generate_key("chat_response", query, user_id, mode)
        return self.set(key, response, self.chat_ttl)
    
    def get_session_data(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached session data"""
        key = self._generate_key("session_data", session_id, user_id)
        return self.get(key)
    
    def set_session_data(self, session_id: int, user_id: int, session_data: Dict[str, Any]) -> bool:
        """Cache session data"""
        key = self._generate_key("session_data", session_id, user_id)
        return self.set(key, session_data, self.session_ttl)
    
    def invalidate_user_cache(self, user_id: int) -> int:
        """Invalidate all cache entries for a user"""
        pattern = f"*{user_id}*"
        return self.clear_pattern(pattern)
    
    def invalidate_session_cache(self, session_id: int) -> int:
        """Invalidate cache entries for a specific session"""
        pattern = f"*{session_id}*"
        return self.clear_pattern(pattern)


# Global cache instance
chat_cache = ChatCacheService()


# Fallback in-memory cache for when Redis is unavailable
class InMemoryCache:
    """Simple in-memory cache as fallback"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = 3600
    
    def _is_expired(self, key: str) -> bool:
        if key not in self._timestamps:
            return True
        return datetime.now() > self._timestamps[key]
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache and not self._is_expired(key):
            return self._cache[key]
        elif key in self._cache:
            # Clean up expired entry
            del self._cache[key]
            del self._timestamps[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        ttl = ttl or self.default_ttl
        self._cache[key] = value
        self._timestamps[key] = datetime.now() + timedelta(seconds=ttl)
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            return True
        return False
    
    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()


# Fallback cache instance
fallback_cache = InMemoryCache()