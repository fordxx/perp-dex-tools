"""
Core alert manager for the price alert system.
Coordinates price monitoring, condition evaluation, and notifications.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from .alert_config import AlertConfig, AlertRule
from .alert_condition import ConditionEvaluator
from .alert_notifier import AlertNotifier
from .alert_storage import AlertStorage
from exchanges.factory import ExchangeFactory


logger = logging.getLogger(__name__)


class AlertManager:
    """Main manager for the price alert system."""

    def __init__(self, config: AlertConfig):
        """
        Initialize alert manager.

        Args:
            config: Alert system configuration
        """
        self.config = config
        self.evaluator = ConditionEvaluator()
        self.notifier = AlertNotifier()
        self.storage = AlertStorage()

        # Exchange clients
        self.exchange_clients: Dict[str, any] = {}
        self.price_cache: Dict[str, Decimal] = {}  # key: "exchange:ticker"

        # Runtime state
        self.running = False
        self.last_check_time = datetime.now()
        self.check_count = 0

        logger.info(f"Alert manager initialized with {len(config.alerts)} alerts")

    async def start(self):
        """Start the alert monitoring system."""
        if self.running:
            logger.warning("Alert manager is already running")
            return

        self.running = True
        logger.info("Starting alert manager...")

        try:
            # Initialize exchange clients for all monitored exchanges
            await self._initialize_exchange_clients()

            # Print startup summary
            self._print_startup_summary()

            # Start monitoring loop
            await self._monitoring_loop()

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Error in alert manager: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """Stop the alert monitoring system."""
        if not self.running:
            return

        logger.info("Stopping alert manager...")
        self.running = False

        # Disconnect from all exchanges
        for exchange_name, client in self.exchange_clients.items():
            try:
                await client.disconnect()
                logger.info(f"Disconnected from {exchange_name}")
            except Exception as e:
                logger.warning(f"Error disconnecting from {exchange_name}: {e}")

        # Cleanup notifier
        self.notifier.cleanup()

        # Print final summary
        self.storage.print_summary()

        logger.info("Alert manager stopped")

    async def _initialize_exchange_clients(self):
        """Initialize exchange clients for all monitored exchanges."""
        # Collect all unique exchanges from alerts
        exchanges = set()
        for alert in self.config.get_active_alerts():
            exchanges.update(alert.exchanges)

        logger.info(f"Initializing clients for exchanges: {', '.join(exchanges)}")

        # Create a minimal config for exchange clients
        from trading_bot import TradingConfig

        for exchange_name in exchanges:
            try:
                # Create a minimal config just for price fetching
                minimal_config = TradingConfig(
                    ticker="BTC",  # Dummy, will be overridden
                    contract_id="",
                    quantity=Decimal("0.1"),
                    take_profit=Decimal("0.02"),
                    tick_size=Decimal("0.01"),
                    direction="buy",
                    max_orders=1,
                    wait_time=1,
                    exchange=exchange_name.lower(),
                    grid_step=Decimal("-100"),
                    stop_price=Decimal("-1"),
                    pause_price=Decimal("-1"),
                    boost_mode=False
                )

                client = ExchangeFactory.create_exchange(exchange_name.lower(), minimal_config)
                await client.connect()

                self.exchange_clients[exchange_name.lower()] = client
                logger.info(f"Connected to {exchange_name}")

            except Exception as e:
                logger.error(f"Failed to initialize {exchange_name} client: {e}")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Starting monitoring loop...")

        while self.running:
            try:
                self.check_count += 1
                check_start = datetime.now()

                # Fetch prices for all monitored tickers
                await self._fetch_all_prices()

                # Evaluate all alerts
                await self._evaluate_all_alerts()

                # Update last check time
                self.last_check_time = datetime.now()
                check_duration = (self.last_check_time - check_start).total_seconds()

                logger.debug(f"Check #{self.check_count} completed in {check_duration:.2f}s")

                # Wait before next check
                await asyncio.sleep(self.config.check_interval)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.check_interval)

    async def _fetch_all_prices(self):
        """Fetch current prices for all monitored tickers."""
        # Collect all unique ticker-exchange pairs
        pairs = set()
        for alert in self.config.get_active_alerts():
            for exchange in alert.exchanges:
                pairs.add((exchange.lower(), alert.ticker.upper()))

        # Fetch prices concurrently
        tasks = []
        for exchange, ticker in pairs:
            if exchange in self.exchange_clients:
                tasks.append(self._fetch_price(exchange, ticker))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_price(self, exchange: str, ticker: str):
        """Fetch price for a specific ticker on an exchange."""
        try:
            client = self.exchange_clients.get(exchange)
            if not client:
                logger.warning(f"No client available for {exchange}")
                return

            # Get current market price
            price = await client.get_current_price(ticker)

            if price:
                key = f"{exchange}:{ticker}"
                self.price_cache[key] = Decimal(str(price))

                # Update price history for condition evaluator
                self.evaluator.update_price(exchange, ticker, Decimal(str(price)))

                logger.debug(f"Fetched {ticker} price from {exchange}: ${price:,.2f}")

        except Exception as e:
            logger.error(f"Error fetching {ticker} price from {exchange}: {e}")

    async def _evaluate_all_alerts(self):
        """Evaluate all active alerts."""
        active_alerts = self.config.get_active_alerts()

        for alert in active_alerts:
            try:
                await self._evaluate_alert(alert)
            except Exception as e:
                logger.error(f"Error evaluating alert '{alert.name}': {e}")

    async def _evaluate_alert(self, alert: AlertRule):
        """Evaluate a single alert rule."""
        # Check if alert can trigger (cooldown period)
        if not alert.can_trigger():
            return

        # Get prices for all exchanges in this alert
        prices = {}
        for exchange in alert.exchanges:
            key = f"{exchange.lower()}:{alert.ticker.upper()}"
            if key in self.price_cache:
                prices[exchange.lower()] = self.price_cache[key]

        if not prices:
            logger.debug(f"No prices available for alert '{alert.name}'")
            return

        # Use the first exchange as primary
        primary_exchange = alert.exchanges[0].lower()
        if primary_exchange not in prices:
            return

        current_price = prices[primary_exchange]

        # Evaluate all conditions
        all_conditions_met = True
        trigger_reasons = []

        for condition in alert.conditions:
            # Get comparison price if needed (for spread alerts)
            comparison_price = None
            if condition.comparison_exchange and condition.comparison_exchange.lower() in prices:
                comparison_price = prices[condition.comparison_exchange.lower()]

            # Evaluate condition
            met, reason = self.evaluator.evaluate(
                condition,
                current_price,
                alert.ticker,
                primary_exchange,
                comparison_price
            )

            if met:
                trigger_reasons.append(reason)
            else:
                all_conditions_met = False
                break  # All conditions must be met

        # If all conditions are met, trigger the alert
        if all_conditions_met and trigger_reasons:
            await self._trigger_alert(alert, primary_exchange, current_price, "; ".join(trigger_reasons))

    async def _trigger_alert(
        self,
        alert: AlertRule,
        exchange: str,
        current_price: Decimal,
        trigger_reason: str
    ):
        """Trigger an alert."""
        logger.info(f"🔔 ALERT TRIGGERED: {alert.name} - {trigger_reason}")

        # Mark as triggered
        alert.mark_triggered()

        # Record in storage
        self.storage.record_alert(
            alert_name=alert.name,
            exchange=exchange,
            ticker=alert.ticker,
            trigger_price=current_price,
            trigger_reason=trigger_reason
        )

        # Send notifications
        await self.notifier.notify(alert, trigger_reason, current_price, exchange)

        # If alert shouldn't repeat, disable it
        if not alert.repeat:
            alert.enabled = False
            logger.info(f"Alert '{alert.name}' disabled (repeat=False)")

    def _print_startup_summary(self):
        """Print startup summary."""
        print("\n" + "=" * 60)
        print("🚀 Price Alert System Started")
        print("=" * 60)

        active_alerts = self.config.get_active_alerts()
        print(f"\nActive Alerts: {len(active_alerts)}")
        print(f"Check Interval: {self.config.check_interval} seconds")
        print(f"Monitoring Exchanges: {', '.join(self.exchange_clients.keys())}")

        if active_alerts:
            print("\nAlert Configuration:")
            for alert in active_alerts:
                print(f"  • {alert.name}")
                print(f"    - Ticker: {alert.ticker}")
                print(f"    - Exchanges: {', '.join(alert.exchanges)}")
                print(f"    - Conditions: {len(alert.conditions)}")
                print(f"    - Actions: {len(alert.actions)}")
                print(f"    - Repeat: {'Yes' if alert.repeat else 'No'}")

        print("\n" + "=" * 60)
        print("Monitoring prices... Press Ctrl+C to stop\n")

    def add_alert(self, alert: AlertRule):
        """Add a new alert rule at runtime."""
        self.config.alerts.append(alert)
        logger.info(f"Added new alert: {alert.name}")

    def remove_alert(self, alert_name: str):
        """Remove an alert rule by name."""
        self.config.alerts = [a for a in self.config.alerts if a.name != alert_name]
        logger.info(f"Removed alert: {alert_name}")

    def enable_alert(self, alert_name: str):
        """Enable an alert by name."""
        for alert in self.config.alerts:
            if alert.name == alert_name:
                alert.enabled = True
                logger.info(f"Enabled alert: {alert_name}")
                return
        logger.warning(f"Alert not found: {alert_name}")

    def disable_alert(self, alert_name: str):
        """Disable an alert by name."""
        for alert in self.config.alerts:
            if alert.name == alert_name:
                alert.enabled = False
                logger.info(f"Disabled alert: {alert_name}")
                return
        logger.warning(f"Alert not found: {alert_name}")

    def get_status(self) -> Dict:
        """Get current status of the alert system."""
        return {
            'running': self.running,
            'active_alerts': len(self.config.get_active_alerts()),
            'total_alerts': len(self.config.alerts),
            'exchanges': list(self.exchange_clients.keys()),
            'check_count': self.check_count,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'cached_prices': len(self.price_cache)
        }
