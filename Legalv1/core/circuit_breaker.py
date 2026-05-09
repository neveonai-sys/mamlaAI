"""
core/circuit_breaker.py — Redis-backed circuit breaker for LLM providers.

Tracks error rates per provider over a rolling window.  Opens the circuit
when too many failures occur, preventing cascading LLM call failures and
giving the provider time to recover.

States:
  CLOSED  — normal operation, calls go through.
  OPEN    — provider is failing; calls are blocked for *cooldown_seconds*.
  HALF-OPEN — one test call is allowed after cooldown; success closes, failure re-opens.

Usage::

    from core.circuit_breaker import CircuitBreaker, CircuitOpenError

    cb = CircuitBreaker(provider='openrouter')
    try:
        cb.before_call()
        result = make_llm_call(...)
        cb.on_success()
    except CircuitOpenError:
        # fast-fail — use fallback provider
        ...
    except Exception as exc:
        cb.on_failure(exc)
        raise
"""

import logging
import time

logger = logging.getLogger('django')

# ---------------------------------------------------------------------------
# Constants (tuneable via constructor kwargs)
# ---------------------------------------------------------------------------
_DEFAULT_ERROR_THRESHOLD   = 0.5   # open circuit if error_rate >= 50 %
_DEFAULT_MIN_CALLS         = 4     # need at least 4 calls before evaluating rate
_DEFAULT_WINDOW_SECONDS    = 60    # rolling window for error counting
_DEFAULT_COOLDOWN_SECONDS  = 30    # how long to stay open before half-open test


class CircuitOpenError(Exception):
    """Raised when a call is blocked because the circuit is open."""


class CircuitBreaker:
    """
    Redis-backed (Django cache) circuit breaker for a single LLM provider.

    Keys used in cache::

        cb:{provider}:errors   INT   errors in current window (TTL = window_seconds)
        cb:{provider}:calls    INT   calls in current window  (TTL = window_seconds)
        cb:{provider}:open     INT   1 = circuit is open      (TTL = cooldown_seconds)
        cb:{provider}:halfopen INT   1 = half-open test slot  (TTL = cooldown_seconds)
    """

    def __init__(
        self,
        provider: str,
        error_threshold: float = _DEFAULT_ERROR_THRESHOLD,
        min_calls: int = _DEFAULT_MIN_CALLS,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
        cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS,
    ):
        self.provider         = provider
        self.error_threshold  = error_threshold
        self.min_calls        = min_calls
        self.window_seconds   = window_seconds
        self.cooldown_seconds = cooldown_seconds

        self._key_errors   = f'cb:{provider}:errors'
        self._key_calls    = f'cb:{provider}:calls'
        self._key_open     = f'cb:{provider}:open'
        self._key_halfopen = f'cb:{provider}:halfopen'

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache(self):
        from core.init_clients import db_clients
        return db_clients.cache

    def _increment(self, key: str, timeout: int) -> int:
        cache = self._cache()
        current = cache.get(key)
        if current is None:
            cache.set(key, 1, timeout=timeout)
            return 1
        new_val = current + 1
        cache.set(key, new_val, timeout=timeout)
        return new_val

    def _is_open(self) -> bool:
        return bool(self._cache().get(self._key_open))

    def _is_half_open(self) -> bool:
        return bool(self._cache().get(self._key_halfopen))

    def _open_circuit(self):
        cache = self._cache()
        cache.set(self._key_open, 1, timeout=self.cooldown_seconds)
        # After cooldown, allow one half-open test request
        cache.set(self._key_halfopen, 1, timeout=self.cooldown_seconds + self.window_seconds)
        logger.error(
            '[CIRCUIT_BREAKER] OPEN provider=%s cooldown=%ds',
            self.provider, self.cooldown_seconds,
        )

    def _close_circuit(self):
        cache = self._cache()
        cache.delete(self._key_open)
        cache.delete(self._key_halfopen)
        cache.delete(self._key_errors)
        cache.delete(self._key_calls)
        logger.info('[CIRCUIT_BREAKER] CLOSED provider=%s', self.provider)

    def _check_and_maybe_open(self):
        cache = self._cache()
        errors = cache.get(self._key_errors) or 0
        calls  = cache.get(self._key_calls)  or 0
        if calls >= self.min_calls:
            error_rate = errors / calls
            if error_rate >= self.error_threshold:
                self._open_circuit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def before_call(self):
        """
        Call before every LLM request.  Raises CircuitOpenError if the
        circuit is open and no half-open test slot is available.
        """
        if self._is_open():
            if self._is_half_open():
                # Allow one test through; consume the half-open slot
                self._cache().delete(self._key_halfopen)
                logger.info('[CIRCUIT_BREAKER] HALF-OPEN test allowed provider=%s', self.provider)
                return
            logger.warning('[CIRCUIT_BREAKER] BLOCKED provider=%s', self.provider)
            raise CircuitOpenError(
                f'LLM provider "{self.provider}" is temporarily unavailable. '
                f'Retry in {self.cooldown_seconds} seconds.'
            )
        self._increment(self._key_calls, timeout=self.window_seconds)

    def on_success(self):
        """Call after a successful LLM response. Resets failure counters."""
        if self._is_half_open():
            # Successful half-open test — close the circuit
            self._close_circuit()
        # Reset error count on success (sliding approach — just delete counters)
        # We keep the window to allow partial recovery tracking
        cache = self._cache()
        errors = cache.get(self._key_errors) or 0
        if errors > 0:
            cache.set(self._key_errors, max(0, errors - 1), timeout=self.window_seconds)

    def on_failure(self, exc: Exception):
        """
        Call after an LLM error.  Records the failure and potentially opens
        the circuit.

        Only counts *retriable* errors (rate limits, connection failures);
        auth/bad-request errors are not recorded so they don't trip the breaker.
        """
        # Import openai lazily to avoid circular imports at module load time
        try:
            from openai import AuthenticationError, BadRequestError
            if isinstance(exc, (AuthenticationError, BadRequestError)):
                return  # don't count non-transient errors
        except ImportError:
            pass

        self._increment(self._key_errors, timeout=self.window_seconds)
        self._check_and_maybe_open()
        logger.warning(
            '[CIRCUIT_BREAKER] failure recorded provider=%s error=%s',
            self.provider, type(exc).__name__,
        )

    def get_status(self) -> dict:
        """Return a status dict for observability / health endpoints."""
        cache = self._cache()
        errors = cache.get(self._key_errors) or 0
        calls  = cache.get(self._key_calls)  or 0
        is_open = self._is_open()
        return {
            'provider':    self.provider,
            'state':       'open' if is_open else 'closed',
            'calls_window': calls,
            'errors_window': errors,
            'error_rate':  round(errors / calls, 3) if calls else 0.0,
        }


# ---------------------------------------------------------------------------
# Module-level singletons (one per provider)
# ---------------------------------------------------------------------------

_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Return the module-level CircuitBreaker singleton for *provider*."""
    if provider not in _breakers:
        _breakers[provider] = CircuitBreaker(provider=provider)
    return _breakers[provider]
