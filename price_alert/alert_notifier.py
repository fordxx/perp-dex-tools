"""
Notification handler for price alerts.
Sends notifications through various channels (Telegram, Lark, Console, etc.)
"""

import os
import logging
import asyncio
import subprocess
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from .alert_config import AlertAction, ActionType, AlertRule
from helpers.telegram_bot import TelegramBot
from helpers.lark_bot import LarkBot


logger = logging.getLogger(__name__)


class AlertNotifier:
    """Handles sending notifications through various channels."""

    def __init__(self):
        """Initialize notifier with available notification channels."""
        self.telegram_bot: Optional[TelegramBot] = None
        self.lark_bot: Optional[LarkBot] = None
        self._setup_bots()

    def _setup_bots(self):
        """Setup notification bots from environment variables."""
        # Setup Telegram
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if telegram_token and telegram_chat_id:
            try:
                self.telegram_bot = TelegramBot(telegram_token, telegram_chat_id)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram bot: {e}")

        # Setup Lark
        lark_webhook = os.getenv('LARK_WEBHOOK_URL')
        if lark_webhook:
            try:
                self.lark_bot = LarkBot(lark_webhook)
                logger.info("Lark bot initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Lark bot: {e}")

    async def notify(
        self,
        alert_rule: AlertRule,
        trigger_reason: str,
        current_price: Decimal,
        exchange: str
    ):
        """
        Send notifications for a triggered alert.

        Args:
            alert_rule: The alert rule that was triggered
            trigger_reason: Reason why the alert was triggered
            current_price: Current market price
            exchange: Exchange name
        """
        for action in alert_rule.actions:
            if not action.enabled:
                continue

            try:
                if action.type == ActionType.NOTIFY:
                    await self._send_notification(action, alert_rule, trigger_reason, current_price, exchange)

                elif action.type == ActionType.SOUND:
                    self._play_sound(action)

                elif action.type == ActionType.EXECUTE_BOT:
                    await self._execute_bot_command(action, alert_rule, current_price)

                elif action.type == ActionType.WEBHOOK:
                    await self._send_webhook(action, alert_rule, trigger_reason, current_price, exchange)

                elif action.type == ActionType.LOG_ONLY:
                    logger.info(f"[LOG_ONLY] Alert: {alert_rule.name} - {trigger_reason}")

            except Exception as e:
                logger.error(f"Error executing action {action.type} for alert {alert_rule.name}: {e}")

    async def _send_notification(
        self,
        action: AlertAction,
        alert_rule: AlertRule,
        trigger_reason: str,
        current_price: Decimal,
        exchange: str
    ):
        """Send notification through configured channels."""
        message = self._format_message(action, alert_rule, trigger_reason, current_price, exchange)

        channels = action.channels if action.channels else ["console"]

        for channel in channels:
            try:
                if channel.lower() == "telegram" and self.telegram_bot:
                    self._send_telegram(message)

                elif channel.lower() == "lark" and self.lark_bot:
                    self._send_lark(message)

                elif channel.lower() == "console":
                    self._send_console(message)

                else:
                    logger.warning(f"Unknown or unavailable notification channel: {channel}")

            except Exception as e:
                logger.error(f"Error sending notification to {channel}: {e}")

    def _format_message(
        self,
        action: AlertAction,
        alert_rule: AlertRule,
        trigger_reason: str,
        current_price: Decimal,
        exchange: str
    ) -> str:
        """Format alert message."""
        if action.message:
            # Use custom message from config
            message = action.message
        else:
            # Generate default message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"""
🔔 价格提醒触发

名称: {alert_rule.name}
交易所: {exchange.upper()}
币种: {alert_rule.ticker}
当前价格: ${current_price:,.2f}
触发原因: {trigger_reason}
时间: {timestamp}
            """.strip()

        # Replace placeholders
        message = message.replace("{ticker}", alert_rule.ticker)
        message = message.replace("{exchange}", exchange.upper())
        message = message.replace("{price}", f"${current_price:,.2f}")
        message = message.replace("{reason}", trigger_reason)

        return message

    def _send_telegram(self, message: str):
        """Send message via Telegram."""
        if not self.telegram_bot:
            logger.warning("Telegram bot not initialized")
            return

        try:
            self.telegram_bot.send_text(message)
            logger.info("Telegram notification sent")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    def _send_lark(self, message: str):
        """Send message via Lark."""
        if not self.lark_bot:
            logger.warning("Lark bot not initialized")
            return

        try:
            self.lark_bot.send_text(message)
            logger.info("Lark notification sent")
        except Exception as e:
            logger.error(f"Failed to send Lark notification: {e}")

    def _send_console(self, message: str):
        """Print message to console with formatting."""
        border = "=" * 60
        print(f"\n{border}")
        print(message)
        print(f"{border}\n")

    def _play_sound(self, action: AlertAction):
        """Play alert sound."""
        try:
            # Try to play system beep or custom sound
            if action.sound_file and os.path.exists(action.sound_file):
                # Play custom sound file (requires external player)
                if os.name == 'posix':  # Linux/Mac
                    subprocess.run(['aplay', action.sound_file], check=False, capture_output=True)
                elif os.name == 'nt':  # Windows
                    import winsound
                    winsound.PlaySound(action.sound_file, winsound.SND_FILENAME)
            else:
                # Play system beep
                print('\a', flush=True)  # Terminal bell
            logger.info("Alert sound played")
        except Exception as e:
            logger.warning(f"Failed to play alert sound: {e}")

    async def _execute_bot_command(
        self,
        action: AlertAction,
        alert_rule: AlertRule,
        current_price: Decimal
    ):
        """Execute trading bot command."""
        if not action.command:
            logger.warning("No command specified for execute_bot action")
            return

        try:
            # Replace placeholders in command
            command = action.command.replace("{ticker}", alert_rule.ticker)
            command = command.replace("{price}", str(current_price))

            logger.info(f"Executing bot command: {command}")

            # Execute command in background
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Don't wait for completion - let it run in background
            logger.info(f"Bot command started with PID: {process.pid}")

        except Exception as e:
            logger.error(f"Failed to execute bot command: {e}")

    async def _send_webhook(
        self,
        action: AlertAction,
        alert_rule: AlertRule,
        trigger_reason: str,
        current_price: Decimal,
        exchange: str
    ):
        """Send webhook notification."""
        if not action.webhook_url:
            logger.warning("No webhook URL specified")
            return

        try:
            import aiohttp
            import json

            payload = {
                "alert_name": alert_rule.name,
                "exchange": exchange,
                "ticker": alert_rule.ticker,
                "current_price": str(current_price),
                "trigger_reason": trigger_reason,
                "timestamp": datetime.now().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(action.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Webhook notification sent to {action.webhook_url}")
                    else:
                        logger.warning(f"Webhook returned status {response.status}")

        except ImportError:
            logger.error("aiohttp not installed. Install it to use webhook notifications: pip install aiohttp")
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")

    def cleanup(self):
        """Cleanup notification resources."""
        if self.telegram_bot:
            try:
                self.telegram_bot.close()
            except:
                pass
