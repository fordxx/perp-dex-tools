"""
Condition evaluation logic for price alerts.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from .alert_config import AlertCondition, ConditionType


logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluates alert conditions against market data."""

    def __init__(self):
        """Initialize the condition evaluator."""
        self.price_history: Dict[str, list] = {}  # ticker -> [(timestamp, price)]
        self.max_history_size = 1000

    def evaluate(
        self,
        condition: AlertCondition,
        current_price: Decimal,
        ticker: str,
        exchange: str,
        comparison_price: Optional[Decimal] = None
    ) -> tuple[bool, str]:
        """
        Evaluate if a condition is met.

        Args:
            condition: The condition to evaluate
            current_price: Current market price
            ticker: Ticker symbol
            exchange: Exchange name
            comparison_price: Optional price for comparison (e.g., for spread alerts)

        Returns:
            Tuple of (condition_met, reason_message)
        """
        try:
            if condition.type == ConditionType.PRICE_ABOVE:
                return self._check_price_above(condition, current_price)

            elif condition.type == ConditionType.PRICE_BELOW:
                return self._check_price_below(condition, current_price)

            elif condition.type == ConditionType.PRICE_RANGE:
                return self._check_price_range(condition, current_price)

            elif condition.type == ConditionType.PERCENT_CHANGE:
                return self._check_percent_change(condition, current_price, ticker, exchange)

            elif condition.type == ConditionType.PRICE_SPREAD:
                return self._check_price_spread(condition, current_price, comparison_price)

            elif condition.type == ConditionType.VOLUME_SPIKE:
                # TODO: Implement when volume data is available
                return False, "Volume spike detection not yet implemented"

            elif condition.type == ConditionType.VOLATILITY:
                return self._check_volatility(condition, ticker, exchange)

            else:
                logger.warning(f"Unknown condition type: {condition.type}")
                return False, f"Unknown condition type: {condition.type}"

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False, f"Error: {e}"

    def _check_price_above(self, condition: AlertCondition, price: Decimal) -> tuple[bool, str]:
        """Check if price is above threshold."""
        if condition.value is None:
            return False, "No value specified for price_above condition"

        if price >= condition.value:
            return True, f"Price ${price:,.2f} is above ${condition.value:,.2f}"
        return False, ""

    def _check_price_below(self, condition: AlertCondition, price: Decimal) -> tuple[bool, str]:
        """Check if price is below threshold."""
        if condition.value is None:
            return False, "No value specified for price_below condition"

        if price <= condition.value:
            return True, f"Price ${price:,.2f} is below ${condition.value:,.2f}"
        return False, ""

    def _check_price_range(self, condition: AlertCondition, price: Decimal) -> tuple[bool, str]:
        """Check if price is within a range."""
        if condition.min_value is None or condition.max_value is None:
            return False, "Min and max values required for price_range condition"

        if condition.min_value <= price <= condition.max_value:
            return True, f"Price ${price:,.2f} is in range [${condition.min_value:,.2f}, ${condition.max_value:,.2f}]"
        return False, ""

    def _check_percent_change(
        self,
        condition: AlertCondition,
        current_price: Decimal,
        ticker: str,
        exchange: str
    ) -> tuple[bool, str]:
        """Check if price has changed by a certain percentage."""
        if condition.percent is None:
            return False, "No percent specified for percent_change condition"

        # Get historical price based on timeframe
        key = f"{exchange}:{ticker}"
        if key not in self.price_history or not self.price_history[key]:
            # Store current price and wait for next check
            self._store_price(key, current_price)
            return False, "Insufficient price history"

        # Parse timeframe (e.g., "1h", "24h", "5m")
        timeframe = condition.timeframe or "1h"
        reference_time = self._parse_timeframe(timeframe)

        # Find the closest historical price
        reference_price = self._get_historical_price(key, reference_time)
        if reference_price is None:
            return False, "No reference price found for timeframe"

        # Calculate percentage change
        if reference_price == 0:
            return False, "Reference price is zero"

        percent_change = ((current_price - reference_price) / reference_price) * 100

        # Check against condition
        if condition.percent >= 0:
            # Positive threshold - check for increase
            if percent_change >= condition.percent:
                return True, f"Price increased by {percent_change:.2f}% in {timeframe} (from ${reference_price:,.2f} to ${current_price:,.2f})"
        else:
            # Negative threshold - check for decrease
            if percent_change <= condition.percent:
                return True, f"Price decreased by {abs(percent_change):.2f}% in {timeframe} (from ${reference_price:,.2f} to ${current_price:,.2f})"

        return False, ""

    def _check_price_spread(
        self,
        condition: AlertCondition,
        price1: Decimal,
        price2: Optional[Decimal]
    ) -> tuple[bool, str]:
        """Check if price spread between exchanges exceeds threshold."""
        if price2 is None:
            return False, "No comparison price provided for spread check"

        if condition.value is None:
            return False, "No minimum spread value specified"

        spread = abs(price1 - price2)
        if spread >= condition.value:
            percent = (spread / min(price1, price2)) * 100
            return True, f"Price spread ${spread:,.2f} ({percent:.2f}%) exceeds ${condition.value:,.2f}"
        return False, ""

    def _check_volatility(
        self,
        condition: AlertCondition,
        ticker: str,
        exchange: str
    ) -> tuple[bool, str]:
        """Check if price volatility exceeds threshold."""
        if condition.percent is None:
            return False, "No volatility threshold specified"

        key = f"{exchange}:{ticker}"
        if key not in self.price_history or len(self.price_history[key]) < 10:
            return False, "Insufficient price history for volatility calculation"

        # Calculate volatility from recent prices
        timeframe = condition.timeframe or "1h"
        reference_time = self._parse_timeframe(timeframe)
        recent_prices = self._get_recent_prices(key, reference_time)

        if len(recent_prices) < 2:
            return False, "Not enough price data for volatility calculation"

        # Calculate standard deviation as percentage of mean
        mean_price = sum(recent_prices) / len(recent_prices)
        if mean_price == 0:
            return False, "Mean price is zero"

        variance = sum((p - mean_price) ** 2 for p in recent_prices) / len(recent_prices)
        std_dev = Decimal(str(variance ** 0.5))
        volatility_percent = (std_dev / mean_price) * 100

        if volatility_percent >= condition.percent:
            return True, f"Volatility {volatility_percent:.2f}% exceeds {condition.percent}% threshold in {timeframe}"
        return False, ""

    def _store_price(self, key: str, price: Decimal):
        """Store price in history."""
        if key not in self.price_history:
            self.price_history[key] = []

        timestamp = datetime.now()
        self.price_history[key].append((timestamp, price))

        # Limit history size
        if len(self.price_history[key]) > self.max_history_size:
            self.price_history[key] = self.price_history[key][-self.max_history_size:]

    def _parse_timeframe(self, timeframe: str) -> datetime:
        """Parse timeframe string to datetime."""
        now = datetime.now()
        timeframe = timeframe.lower().strip()

        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            return now - timedelta(minutes=minutes)
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            return now - timedelta(hours=hours)
        elif timeframe.endswith('d'):
            days = int(timeframe[:-1])
            return now - timedelta(days=days)
        else:
            # Default to 1 hour
            return now - timedelta(hours=1)

    def _get_historical_price(self, key: str, reference_time: datetime) -> Optional[Decimal]:
        """Get historical price closest to reference time."""
        if key not in self.price_history:
            return None

        history = self.price_history[key]
        if not history:
            return None

        # Find closest price to reference time
        closest = min(history, key=lambda x: abs((x[0] - reference_time).total_seconds()))
        return closest[1]

    def _get_recent_prices(self, key: str, since: datetime) -> list[Decimal]:
        """Get all prices since a specific time."""
        if key not in self.price_history:
            return []

        return [price for timestamp, price in self.price_history[key] if timestamp >= since]

    def update_price(self, exchange: str, ticker: str, price: Decimal):
        """Update price history with new price data."""
        key = f"{exchange}:{ticker}"
        self._store_price(key, price)
