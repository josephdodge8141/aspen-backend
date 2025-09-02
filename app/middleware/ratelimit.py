import time
import os
from typing import Dict, Tuple
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.security.apikeys import hash_api_key


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self) -> bool:
        now = time.time()
        # Refill tokens based on time elapsed
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.buckets: Dict[str, TokenBucket] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Skip JWT calls and only rate limit API key calls
        x_api_key = request.headers.get("X-API-Key")
        
        if x_api_key:
            # Use hash of API key for bucket identification
            api_key_hash = hash_api_key(x_api_key)
            
            # Get or create bucket for this API key
            if api_key_hash not in self.buckets:
                self.buckets[api_key_hash] = TokenBucket(
                    self.requests_per_minute, 
                    self.refill_rate
                )
            
            bucket = self.buckets[api_key_hash]
            
            if not bucket.consume():
                # Rate limit exceeded
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Content-Type": "application/problem+json"}
                )
        
        response = await call_next(request)
        return response 