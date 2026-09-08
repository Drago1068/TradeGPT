from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..market_data import QuoteSnapshot
from .base import ProviderUnavailable


@dataclass(frozen=True)
class HttpSnapshotConfig:
    """Configuration for a provider endpoint that returns a QuoteSnapshot payload."""

    base_url: str
    api_key_env: str | None = None
    timeout_seconds: float = 5.0


class HttpSnapshotProvider:
    """Minimal authenticated HTTP adapter with a strict provider boundary.

    The adapter expects JSON fields matching QuoteSnapshot. It does not contain
    vendor-specific strategy logic and never manufactures market values.
    """

    def __init__(self, config: HttpSnapshotConfig, *, environ: dict[str, str] | None = None,
                 opener: Callable = urlopen) -> None:
        self.config = config
        self._environ = environ
        self._opener = opener

    def snapshot(self, symbol: str) -> QuoteSnapshot:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ProviderUnavailable("symbol is required")
        url = self.config.base_url.rstrip("/") + "/" + symbol
        headers = {"Accept": "application/json"}
        if self.config.api_key_env:
            import os
            env = self._environ if self._environ is not None else os.environ
            key = env.get(self.config.api_key_env)
            if not key:
                raise ProviderUnavailable(f"missing provider credential: {self.config.api_key_env}")
            headers["Authorization"] = f"Bearer {key}"
        request = Request(url, headers=headers, method="GET")
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise ProviderUnavailable(f"provider request failed for {symbol}") from exc
        try:
            return self._snapshot_from_payload(payload, symbol)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderUnavailable(f"provider returned invalid snapshot for {symbol}") from exc

    @staticmethod
    def _snapshot_from_payload(payload: object, symbol: str) -> QuoteSnapshot:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        timestamp = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return QuoteSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            last_price=float(payload["last_price"]),
            vwap=float(payload["vwap"]),
            rvol=float(payload["rvol"]),
            relative_strength=float(payload["relative_strength"]),
            adv_shares=float(payload["adv_shares"]),
            adv_dollars=float(payload["adv_dollars"]),
            verified=bool(payload.get("verified", True)),
            verification_reasons=tuple(str(x) for x in payload.get("verification_reasons", ())),
            source=str(payload.get("source", "http")),
            latency_ms=float(payload["latency_ms"]) if payload.get("latency_ms") is not None else None,
        )
