"""
Rate Limiter - Dual-Domain Rate Limiting for Multi-Account Gemini

Based on doctoral thesis research for 24/7 Gemini daemon operation.

Manages two constraint domains:
1. Time-Domain (RPM): Token bucket for requests per minute
2. Volume-Domain (Daily): Counter for daily quota limits

Features:
- Per-account usage tracking
- Automatic daily reset
- Round-robin account selection
- Configurable limits per model tier
- Persistent state (survives restarts)

Rate Limits (AI Pro + OAuth, per account):
| Model | Daily | RPM |
|-------|-------|-----|
| flash-lite | 1,500 | 60 |
| flash-3 | Unlimited | 60 |
| pro-3 | 100 | 30 |
| image | 1,000 | 10 |
"""

import time
import json
import os
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path


class ModelTier(Enum):
    """Model tiers with their identifiers."""
    FLASH_LITE = "flash-lite"
    FLASH_3 = "flash-3"
    PRO_3 = "pro-3"
    PRO_25 = "pro-25"
    IMAGE_PRO = "image-pro"
    IMAGE_FLASH = "image-flash"


# Model limits configuration
# daily: -1 = unlimited, rpm: requests per minute
MODEL_LIMITS = {
    ModelTier.FLASH_LITE: {"daily": 1500, "rpm": 60},
    ModelTier.FLASH_3: {"daily": -1, "rpm": 60},  # Unlimited daily
    ModelTier.PRO_3: {"daily": 100, "rpm": 30},
    ModelTier.PRO_25: {"daily": 100, "rpm": 60},
    ModelTier.IMAGE_PRO: {"daily": 1000, "rpm": 10},
    ModelTier.IMAGE_FLASH: {"daily": 1000, "rpm": 60},
}

# Map model IDs to tiers
MODEL_ID_TO_TIER = {
    "gemini-2.5-flash-lite": ModelTier.FLASH_LITE,
    "gemini-3-flash-preview": ModelTier.FLASH_3,
    "gemini-2.5-flash": ModelTier.FLASH_3,
    "gemini-3-pro-preview": ModelTier.PRO_3,
    "gemini-2.5-pro": ModelTier.PRO_25,
    "gemini-3-pro-image-preview": ModelTier.IMAGE_PRO,
    "gemini-2.5-flash-image": ModelTier.IMAGE_FLASH,
}


class RateLimiter:
    """
    Dual-domain rate limiter for multi-account Gemini usage.

    Tracks both RPM (requests per minute) and daily quotas per account.
    Provides intelligent account selection to maximize throughput.
    """

    def __init__(
        self,
        state_file: Optional[str] = None,
        num_accounts: int = 2,
        safety_factor: float = 0.9
    ):
        """
        Initialize the rate limiter.

        Args:
            state_file: Path to state persistence file
            num_accounts: Number of Gemini accounts (default: 2)
            safety_factor: Fraction of limits to use (0.9 = 90%)
        """
        if state_file is None:
            state_file = os.path.expanduser("~/.gemini/rate_limits.json")

        self.state_file = state_file
        self.num_accounts = num_accounts
        self.safety_factor = safety_factor
        self.accounts = list(range(1, num_accounts + 1))

        # Ensure directory exists
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

        self._load_state()

    def _load_state(self):
        """Load state from file or initialize fresh."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)

                # Check for day rollover
                if self.state.get("date") != time.strftime("%Y-%m-%d"):
                    self._reset_state()
            except (json.JSONDecodeError, KeyError):
                self._reset_state()
        else:
            self._reset_state()

    def _reset_state(self):
        """Reset state for new day."""
        self.state = {
            "date": time.strftime("%Y-%m-%d"),
            "accounts": {
                str(acc): {
                    "daily_usage": {tier.value: 0 for tier in ModelTier},
                    "last_request_time": {tier.value: 0 for tier in ModelTier}
                }
                for acc in self.accounts
            }
        }
        self._save_state()

    def _save_state(self):
        """Persist state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _get_tier(self, model_pref: str) -> ModelTier:
        """Convert model preference string to ModelTier."""
        # Check if it's a model ID
        if model_pref in MODEL_ID_TO_TIER:
            return MODEL_ID_TO_TIER[model_pref]

        # Check if it's already a tier value
        try:
            return ModelTier(model_pref)
        except ValueError:
            # Default to flash-lite for unknown
            return ModelTier.FLASH_LITE

    def acquire_slot(self, model_pref: str) -> Optional[int]:
        """
        Acquire a slot for making a request.

        Args:
            model_pref: Model tier or model ID

        Returns:
            Account ID if available, None if rate limited
        """
        self._load_state()  # Sync for multi-process safety
        tier = self._get_tier(model_pref)
        limits = MODEL_LIMITS[tier]
        now = time.time()

        # Round-robin with availability check
        # Prefer the account that was used longer ago
        preferred_order = sorted(
            self.accounts,
            key=lambda acc: self.state["accounts"][str(acc)]["last_request_time"].get(tier.value, 0)
        )

        for acc in preferred_order:
            acc_str = str(acc)
            usage = self.state["accounts"][acc_str]

            # Check daily limit (skip if unlimited)
            daily_limit = limits["daily"]
            if daily_limit > 0:
                effective_limit = int(daily_limit * self.safety_factor)
                if usage["daily_usage"].get(tier.value, 0) >= effective_limit:
                    continue

            # Check RPM (token bucket lite)
            rpm_limit = limits["rpm"]
            min_gap = 60.0 / (rpm_limit * self.safety_factor)
            last_req = usage["last_request_time"].get(tier.value, 0)

            if now - last_req < min_gap:
                continue

            # Account is available
            return acc

        return None

    def record_usage(
        self,
        account_id: int,
        model_pref: str,
        tokens: int = 0
    ):
        """
        Record a successful request.

        Args:
            account_id: The account that made the request
            model_pref: Model tier or model ID
            tokens: Optional token count (for future cost tracking)
        """
        tier = self._get_tier(model_pref)
        acc_str = str(account_id)

        self.state["accounts"][acc_str]["daily_usage"][tier.value] = \
            self.state["accounts"][acc_str]["daily_usage"].get(tier.value, 0) + 1

        self.state["accounts"][acc_str]["last_request_time"][tier.value] = time.time()

        self._save_state()

    def get_remaining_quota(self, model_pref: str) -> Dict[str, int]:
        """
        Get remaining daily quota per account.

        Args:
            model_pref: Model tier or model ID

        Returns:
            Dict mapping account ID to remaining quota
        """
        self._load_state()
        tier = self._get_tier(model_pref)
        limits = MODEL_LIMITS[tier]
        daily_limit = limits["daily"]

        result = {}
        for acc in self.accounts:
            acc_str = str(acc)
            used = self.state["accounts"][acc_str]["daily_usage"].get(tier.value, 0)

            if daily_limit < 0:
                result[acc_str] = -1  # Unlimited
            else:
                result[acc_str] = max(0, daily_limit - used)

        return result

    def get_total_remaining(self, model_pref: str) -> int:
        """
        Get total remaining quota across all accounts.

        Args:
            model_pref: Model tier or model ID

        Returns:
            Total remaining quota (-1 if unlimited)
        """
        remaining = self.get_remaining_quota(model_pref)

        if any(v < 0 for v in remaining.values()):
            return -1  # At least one account is unlimited

        return sum(remaining.values())

    def can_request_now(self, model_pref: str) -> bool:
        """
        Check if a request can be made immediately.

        Args:
            model_pref: Model tier or model ID

        Returns:
            True if at least one account can handle the request
        """
        return self.acquire_slot(model_pref) is not None

    def get_wait_time(self, model_pref: str) -> float:
        """
        Get estimated wait time until a request can be made.

        Args:
            model_pref: Model tier or model ID

        Returns:
            Seconds to wait (0 if can request now)
        """
        if self.can_request_now(model_pref):
            return 0

        tier = self._get_tier(model_pref)
        limits = MODEL_LIMITS[tier]
        now = time.time()

        # Find the shortest wait time across accounts
        min_wait = float('inf')

        for acc in self.accounts:
            acc_str = str(acc)
            usage = self.state["accounts"][acc_str]

            # Check if daily quota exhausted
            daily_limit = limits["daily"]
            if daily_limit > 0:
                if usage["daily_usage"].get(tier.value, 0) >= daily_limit:
                    continue  # This account is exhausted for the day

            # Calculate RPM wait
            rpm_limit = limits["rpm"]
            min_gap = 60.0 / (rpm_limit * self.safety_factor)
            last_req = usage["last_request_time"].get(tier.value, 0)
            wait = max(0, min_gap - (now - last_req))

            min_wait = min(min_wait, wait)

        return min_wait if min_wait != float('inf') else 3600  # 1 hour if all exhausted

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        self._load_state()

        stats = {
            "date": self.state["date"],
            "accounts": {}
        }

        for acc in self.accounts:
            acc_str = str(acc)
            acc_stats = {"tiers": {}}

            for tier in ModelTier:
                limits = MODEL_LIMITS[tier]
                used = self.state["accounts"][acc_str]["daily_usage"].get(tier.value, 0)

                if limits["daily"] < 0:
                    remaining = -1
                    pct_used = 0
                else:
                    remaining = max(0, limits["daily"] - used)
                    pct_used = (used / limits["daily"]) * 100 if limits["daily"] > 0 else 0

                acc_stats["tiers"][tier.value] = {
                    "used": used,
                    "remaining": remaining,
                    "limit": limits["daily"],
                    "percent_used": round(pct_used, 1)
                }

            stats["accounts"][acc_str] = acc_stats

        return stats

    def print_status(self):
        """Print a formatted status report."""
        stats = self.get_stats()

        print(f"\n=== Rate Limiter Status ({stats['date']}) ===\n")

        for acc_id, acc_stats in stats["accounts"].items():
            print(f"Account {acc_id}:")
            for tier_name, tier_stats in acc_stats["tiers"].items():
                if tier_stats["limit"] < 0:
                    status = f"  {tier_name}: {tier_stats['used']} used (unlimited)"
                else:
                    status = f"  {tier_name}: {tier_stats['used']}/{tier_stats['limit']} ({tier_stats['percent_used']}%)"
                print(status)
            print()
