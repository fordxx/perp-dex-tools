"""
Storage and history tracking for price alerts.
"""

import json
import os
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class AlertRecord:
    """Record of a triggered alert."""

    def __init__(
        self,
        alert_name: str,
        exchange: str,
        ticker: str,
        trigger_price: Decimal,
        trigger_reason: str,
        timestamp: Optional[datetime] = None
    ):
        self.alert_name = alert_name
        self.exchange = exchange
        self.ticker = ticker
        self.trigger_price = trigger_price
        self.trigger_reason = trigger_reason
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            'alert_name': self.alert_name,
            'exchange': self.exchange,
            'ticker': self.ticker,
            'trigger_price': str(self.trigger_price),
            'trigger_reason': self.trigger_reason,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRecord':
        """Create record from dictionary."""
        return cls(
            alert_name=data['alert_name'],
            exchange=data['exchange'],
            ticker=data['ticker'],
            trigger_price=Decimal(data['trigger_price']),
            trigger_reason=data['trigger_reason'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )


class AlertStorage:
    """Handles storage and retrieval of alert history."""

    def __init__(self, storage_dir: str = "logs/alerts"):
        """Initialize alert storage."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.history_file = self.storage_dir / "alert_history.json"
        self.csv_file = self.storage_dir / "alert_history.csv"

        # In-memory cache
        self.history: List[AlertRecord] = []
        self._load_history()

        # Statistics
        self.stats: Dict[str, Any] = {}
        self._calculate_stats()

    def _load_history(self):
        """Load alert history from file."""
        if not self.history_file.exists():
            return

        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                self.history = [AlertRecord.from_dict(record) for record in data]
            logger.info(f"Loaded {len(self.history)} alert records from history")
        except Exception as e:
            logger.error(f"Failed to load alert history: {e}")
            self.history = []

    def _save_history(self):
        """Save alert history to file."""
        try:
            with open(self.history_file, 'w') as f:
                data = [record.to_dict() for record in self.history]
                json.dump(data, f, indent=2)
            logger.debug("Alert history saved")
        except Exception as e:
            logger.error(f"Failed to save alert history: {e}")

    def record_alert(
        self,
        alert_name: str,
        exchange: str,
        ticker: str,
        trigger_price: Decimal,
        trigger_reason: str
    ):
        """Record a triggered alert."""
        record = AlertRecord(
            alert_name=alert_name,
            exchange=exchange,
            ticker=ticker,
            trigger_price=trigger_price,
            trigger_reason=trigger_reason
        )

        self.history.append(record)
        self._save_history()
        self._save_to_csv(record)
        self._calculate_stats()

        logger.info(f"Recorded alert: {alert_name} - {trigger_reason}")

    def _save_to_csv(self, record: AlertRecord):
        """Append record to CSV file for easy analysis."""
        file_exists = self.csv_file.exists()

        try:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)

                # Write header if file is new
                if not file_exists:
                    writer.writerow([
                        'Timestamp',
                        'Alert Name',
                        'Exchange',
                        'Ticker',
                        'Trigger Price',
                        'Trigger Reason'
                    ])

                # Write record
                writer.writerow([
                    record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    record.alert_name,
                    record.exchange,
                    record.ticker,
                    f"{record.trigger_price:.2f}",
                    record.trigger_reason
                ])
        except Exception as e:
            logger.error(f"Failed to save record to CSV: {e}")

    def _calculate_stats(self):
        """Calculate statistics from alert history."""
        if not self.history:
            self.stats = {
                'total_alerts': 0,
                'by_ticker': {},
                'by_exchange': {},
                'by_alert_name': {}
            }
            return

        self.stats = {
            'total_alerts': len(self.history),
            'by_ticker': {},
            'by_exchange': {},
            'by_alert_name': {}
        }

        for record in self.history:
            # Count by ticker
            self.stats['by_ticker'][record.ticker] = \
                self.stats['by_ticker'].get(record.ticker, 0) + 1

            # Count by exchange
            self.stats['by_exchange'][record.exchange] = \
                self.stats['by_exchange'].get(record.exchange, 0) + 1

            # Count by alert name
            self.stats['by_alert_name'][record.alert_name] = \
                self.stats['by_alert_name'].get(record.alert_name, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        return self.stats.copy()

    def get_recent_alerts(self, limit: int = 10) -> List[AlertRecord]:
        """Get most recent alerts."""
        return sorted(self.history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_alerts_by_ticker(self, ticker: str) -> List[AlertRecord]:
        """Get all alerts for a specific ticker."""
        return [r for r in self.history if r.ticker.upper() == ticker.upper()]

    def get_alerts_by_exchange(self, exchange: str) -> List[AlertRecord]:
        """Get all alerts for a specific exchange."""
        return [r for r in self.history if r.exchange.lower() == exchange.lower()]

    def get_alerts_by_name(self, alert_name: str) -> List[AlertRecord]:
        """Get all alerts with a specific name."""
        return [r for r in self.history if r.alert_name == alert_name]

    def clear_history(self):
        """Clear all alert history."""
        self.history = []
        self._save_history()
        self._calculate_stats()
        logger.info("Alert history cleared")

    def export_to_file(self, filename: str, format: str = 'json'):
        """Export alert history to a file."""
        try:
            if format == 'json':
                with open(filename, 'w') as f:
                    data = [record.to_dict() for record in self.history]
                    json.dump(data, f, indent=2)
            elif format == 'csv':
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'Timestamp',
                        'Alert Name',
                        'Exchange',
                        'Ticker',
                        'Trigger Price',
                        'Trigger Reason'
                    ])
                    for record in self.history:
                        writer.writerow([
                            record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            record.alert_name,
                            record.exchange,
                            record.ticker,
                            f"{record.trigger_price:.2f}",
                            record.trigger_reason
                        ])
            else:
                raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Alert history exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export alert history: {e}")

    def print_summary(self):
        """Print a summary of alert statistics."""
        print("\n" + "=" * 60)
        print("📊 Alert History Summary")
        print("=" * 60)

        stats = self.get_stats()
        print(f"\nTotal Alerts: {stats['total_alerts']}")

        if stats['by_ticker']:
            print("\nAlerts by Ticker:")
            for ticker, count in sorted(stats['by_ticker'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {ticker}: {count}")

        if stats['by_exchange']:
            print("\nAlerts by Exchange:")
            for exchange, count in sorted(stats['by_exchange'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {exchange}: {count}")

        if stats['by_alert_name']:
            print("\nAlerts by Name:")
            for name, count in sorted(stats['by_alert_name'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {name}: {count}")

        recent = self.get_recent_alerts(5)
        if recent:
            print("\nRecent Alerts:")
            for record in recent:
                print(f"  {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
                      f"{record.alert_name} ({record.ticker}) @ ${record.trigger_price:.2f}")

        print("=" * 60 + "\n")
