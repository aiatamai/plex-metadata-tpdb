"""Token bucket rate limiter for outgoing API requests."""

import asyncio
from datetime import datetime
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for controlling API request rates.

    This implementation uses a token bucket algorithm to limit the rate
    of outgoing requests to external APIs like ThePornDB.

    Attributes:
        rate: Number of requests allowed per second
        burst_size: Maximum number of tokens (burst capacity)
        tokens: Current number of available tokens
        last_update: Timestamp of the last token update
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: int = 5,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            requests_per_second: Maximum sustained request rate
            burst_size: Maximum burst capacity (tokens)
        """
        self.rate = requests_per_second
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens from the bucket, waiting if necessary.

        This method will block until the requested number of tokens
        are available. It returns the time spent waiting.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            Time in seconds spent waiting for tokens
        """
        async with self._lock:
            wait_time = 0.0

            # Refill tokens based on elapsed time
            now = datetime.now()
            elapsed = (now - self.last_update).total_seconds()
            self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Check if we have enough tokens
            if self.tokens < tokens:
                # Calculate wait time needed
                deficit = tokens - self.tokens
                wait_time = deficit / self.rate

                # Wait for tokens to become available
                await asyncio.sleep(wait_time)

                # Refill after waiting
                now = datetime.now()
                elapsed = (now - self.last_update).total_seconds()
                self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
                self.last_update = now

            # Consume tokens
            self.tokens -= tokens
            return wait_time

    async def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            # Refill tokens based on elapsed time
            now = datetime.now()
            elapsed = (now - self.last_update).total_seconds()
            self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    @property
    def available_tokens(self) -> float:
        """Get the current number of available tokens."""
        now = datetime.now()
        elapsed = (now - self.last_update).total_seconds()
        return min(self.burst_size, self.tokens + elapsed * self.rate)
