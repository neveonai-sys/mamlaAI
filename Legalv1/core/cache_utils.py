# For Django cache KEY_FUNCTION compatibility
def make_cache_key(key, key_prefix, version):
    """
    Constructs the key used by all other methods.
    """
    return f"{key_prefix}:{version}:{key}"
import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional, Union, List, Dict, Tuple
from datetime import timedelta
from django.core.cache import caches
from django.utils.timezone import now

logger = logging.getLogger('django')

def cache_result(
    key_prefix: str = '',
    timeout: int = 300,
    cache_name: str = 'default',
    key_params: Optional[List[str]] = None
):
    """
    Cache the result of a function or method.
    
    Args:
        key_prefix: Custom prefix for cache key. If None, uses function name.
        timeout: Cache timeout in seconds. Default 5 minutes.
        cache_name: Name of the cache backend to use. Defaults to 'default'.
        key_params: List of parameter names to include in cache key.
                   If None, all parameters are included.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get cache instance
            try:
                cache = caches[cache_name]
            except Exception as e:
                logger.warning(f"Failed to get cache '{cache_name}': {e}")
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_params is not None:
                # Only include specified parameters in key
                func_params = {}
                if args and len(args) > 0 and hasattr(args[0], func.__name__):
                    # Handle instance methods (skip 'self' or 'cls')
                    args = args[1:]
                
                # Get function signature
                sig = functools.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # Filter parameters
                for param in key_params:
                    if param in bound_args.arguments:
                        func_params[param] = bound_args.arguments[param]
            else:
                # Include all parameters in key
                func_params = {'args': args, 'kwargs': kwargs}
            
            # Create a stable string representation of parameters
            try:
                params_str = json.dumps(
                    func_params,
                    sort_keys=True,
                    default=str,  # Handle non-serializable objects
                    ensure_ascii=False
                ).encode('utf-8')
                
                # Generate cache key
                prefix = key_prefix or f"{func.__module__}.{func.__qualname__}"
                key = f"{prefix}:{hashlib.md5(params_str).hexdigest()}"
                
                # Try to get from cache
                result = cache.get(key)
                if result is not None:
                    logger.debug(f"Cache hit for {key}")
                    return result
                
                # Cache miss, call function
                logger.debug(f"Cache miss for {key}")
                result = func(*args, **kwargs)
                
                # Store result in cache
                if result is not None:
                    cache.set(key, result, timeout=timeout)
                
                return result
                
            except Exception as e:
                logger.error(f"Cache error in {func.__name__}: {e}")
                # If there's any error with caching, just call the function
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def invalidate_cache(
    key_prefix: str,
    cache_name: str = 'default',
    pattern: bool = False
) -> None:
    """
    Invalidate cache entries matching the given key prefix or pattern.
    
    Args:
        key_prefix: Prefix or pattern to match cache keys.
        cache_name: Name of the cache backend to use.
        pattern: If True, treat key_prefix as a pattern to match against all keys.
    """
    try:
        cache = caches[cache_name]
        
        if hasattr(cache, 'delete_pattern') and pattern:
            # Redis-specific pattern deletion
            cache.delete_pattern(f"*{key_prefix}*")
        else:
            # Fallback: try to delete the exact key
            cache.delete(key_prefix)
            
        logger.info(f"Cache invalidated for prefix: {key_prefix}")
    except Exception as e:
        logger.error(f"Error invalidating cache for {key_prefix}: {e}")


class CacheManager:
    """
    A class to manage cache operations with namespacing and bulk operations.
    """
    def __init__(self, namespace: str, cache_name: str = 'default'):
        self.namespace = namespace
        self.cache_name = cache_name
        self.cache = caches[cache_name]
    
    def make_key(self, key: str) -> str:
        """Create a namespaced cache key."""
        return f"{self.namespace}:{key}"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        return self.cache.get(self.make_key(key), default)
    
    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None
    ) -> None:
        """Set a value in cache."""
        self.cache.set(self.make_key(key), value, timeout=timeout)
    
    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        self.cache.delete(self.make_key(key))
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        prefixed_keys = [self.make_key(key) for key in keys]
        results = self.cache.get_many(prefixed_keys)
        
        # Return results with original keys (without namespace)
        return {
            key.replace(f"{self.namespace}:", '', 1): value
            for key, value in results.items()
        }
    
    def set_many(
        self,
        data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> None:
        """Set multiple values in cache."""
        prefixed_data = {
            self.make_key(key): value
            for key, value in data.items()
        }
        self.cache.set_many(prefixed_data, timeout=timeout)
    
    def clear_namespace(self) -> None:
        """Clear all keys in this namespace."""
        if hasattr(self.cache, 'delete_pattern'):
            self.cache.delete_pattern(f"{self.namespace}:*")
        else:
            logger.warning("delete_pattern not available, cannot clear namespace")
    
    def get_or_set(
        self,
        key: str,
        default: Union[Callable, Any],
        timeout: Optional[int] = None
    ) -> Any:
        """
        Get a value from cache, or set it with the default if not found.
        
        Args:
            key: Cache key
            default: Default value or callable that returns the default value
            timeout: Cache timeout in seconds
        """
        value = self.get(key)
        if value is None:
            value = default() if callable(default) else default
            if value is not None:
                self.set(key, value, timeout=timeout)
        return value


# Common cache timeouts (in seconds)
class CacheTimeouts:
    SHORT = 60 * 5      # 5 minutes
    MEDIUM = 60 * 30    # 30 minutes
    LONG = 60 * 60 * 2  # 2 hours
    DAY = 60 * 60 * 24  # 24 hours
    WEEK = 60 * 60 * 24 * 7  # 1 week


# Example usage:
# user_cache = CacheManager('user_profile')
# 
# @cache_result(key_prefix='user_profile', timeout=CacheTimeouts.MEDIUM)
# def get_user_profile(user_id: int) -> Dict:
#     # Expensive database query here
#     return db.query(User).get(user_id).to_dict()
# 
# # Later, to invalidate:
# invalidate_cache('user_profile')
