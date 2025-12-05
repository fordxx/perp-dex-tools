"""
Configuration models for the price alert system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from decimal import Decimal
from enum import Enum
from datetime import datetime


class ConditionType(str, Enum):
    """Types of alert conditions."""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_RANGE = "price_range"
    PERCENT_CHANGE = "percent_change"
    PRICE_SPREAD = "price_spread"
    VOLUME_SPIKE = "volume_spike"
    VOLATILITY = "volatility"


class ActionType(str, Enum):
    """Types of actions to take when alert triggers."""
    NOTIFY = "notify"
    EXECUTE_BOT = "execute_bot"
    SOUND = "sound"
    WEBHOOK = "webhook"
    LOG_ONLY = "log_only"


@dataclass
class AlertCondition:
    """Defines a condition that triggers an alert."""
    type: ConditionType
    value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    percent: Optional[Decimal] = None
    timeframe: Optional[str] = None  # e.g., "1h", "24h"
    comparison_exchange: Optional[str] = None  # For spread alerts

    def __post_init__(self):
        """Convert string values to appropriate types."""
        if isinstance(self.type, str):
            self.type = ConditionType(self.type)
        if self.value is not None and not isinstance(self.value, Decimal):
            self.value = Decimal(str(self.value))
        if self.min_value is not None and not isinstance(self.min_value, Decimal):
            self.min_value = Decimal(str(self.min_value))
        if self.max_value is not None and not isinstance(self.max_value, Decimal):
            self.max_value = Decimal(str(self.max_value))
        if self.percent is not None and not isinstance(self.percent, Decimal):
            self.percent = Decimal(str(self.percent))


@dataclass
class AlertAction:
    """Defines an action to take when alert triggers."""
    type: ActionType
    channels: List[str] = field(default_factory=list)
    message: Optional[str] = None
    command: Optional[str] = None
    webhook_url: Optional[str] = None
    sound_file: Optional[str] = None
    enabled: bool = True

    def __post_init__(self):
        """Convert string type to ActionType enum."""
        if isinstance(self.type, str):
            self.type = ActionType(self.type)


@dataclass
class AlertRule:
    """A complete alert rule with conditions and actions."""
    name: str
    exchange: Optional[str] = None
    exchanges: List[str] = field(default_factory=list)
    ticker: str = ""
    conditions: List[AlertCondition] = field(default_factory=list)
    actions: List[AlertAction] = field(default_factory=list)
    enabled: bool = True
    cooldown: int = 300  # Seconds between repeated alerts
    repeat: bool = False  # Whether to repeat after cooldown
    priority: int = 0  # Higher priority alerts processed first

    # Runtime state
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def __post_init__(self):
        """Ensure single exchange is added to exchanges list."""
        if self.exchange and self.exchange not in self.exchanges:
            self.exchanges = [self.exchange] + self.exchanges

        # Convert dict conditions to AlertCondition objects
        self.conditions = [
            AlertCondition(**c) if isinstance(c, dict) else c
            for c in self.conditions
        ]

        # Convert dict actions to AlertAction objects
        self.actions = [
            AlertAction(**a) if isinstance(a, dict) else a
            for a in self.actions
        ]

    def can_trigger(self) -> bool:
        """Check if alert can trigger based on cooldown."""
        if not self.enabled:
            return False

        if not self.repeat and self.trigger_count > 0:
            return False

        if self.last_triggered is None:
            return True

        elapsed = (datetime.now() - self.last_triggered).total_seconds()
        return elapsed >= self.cooldown

    def mark_triggered(self):
        """Mark alert as triggered."""
        self.last_triggered = datetime.now()
        self.trigger_count += 1


@dataclass
class AlertConfig:
    """Configuration for the entire alert system."""
    alerts: List[AlertRule] = field(default_factory=list)
    default_exchanges: List[str] = field(default_factory=list)
    default_channels: List[str] = field(default_factory=lambda: ["telegram"])
    check_interval: int = 5  # Seconds between price checks
    enable_sound: bool = True
    enable_terminal_ui: bool = True
    log_level: str = "INFO"

    def __post_init__(self):
        """Convert dict alerts to AlertRule objects."""
        self.alerts = [
            AlertRule(**a) if isinstance(a, dict) else a
            for a in self.alerts
        ]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertConfig':
        """Create AlertConfig from dictionary."""
        return cls(**data)

    def get_active_alerts(self) -> List[AlertRule]:
        """Get all enabled alerts."""
        return [alert for alert in self.alerts if alert.enabled]

    def get_alerts_by_ticker(self, ticker: str) -> List[AlertRule]:
        """Get all alerts for a specific ticker."""
        return [alert for alert in self.alerts if alert.ticker.upper() == ticker.upper()]

    def get_alerts_by_exchange(self, exchange: str) -> List[AlertRule]:
        """Get all alerts for a specific exchange."""
        return [alert for alert in self.alerts if exchange.lower() in [e.lower() for e in alert.exchanges]]
