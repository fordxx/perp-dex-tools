#!/usr/bin/env python3
"""
Price Alert System Entry Point
价格提醒系统入口脚本
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List
import yaml
import dotenv

from price_alert import AlertManager, AlertConfig
from decimal import Decimal


def setup_logging(log_level: str):
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Suppress noisy loggers
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def load_config_file(config_path: str) -> AlertConfig:
    """Load alert configuration from YAML file."""
    path = Path(config_path)

    if not path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            print(f"Error: Empty configuration file: {config_path}")
            sys.exit(1)

        config = AlertConfig.from_dict(data)
        print(f"✓ Loaded configuration from {config_path}")
        print(f"  - {len(config.alerts)} alerts defined")
        print(f"  - {len(config.get_active_alerts())} alerts enabled")

        return config

    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML configuration: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to load configuration: {e}")
        sys.exit(1)


def load_multiple_configs(config_paths: List[str]) -> AlertConfig:
    """Load and merge multiple configuration files."""
    merged_config = AlertConfig()

    for config_path in config_paths:
        config = load_config_file(config_path)
        merged_config.alerts.extend(config.alerts)

        # Use settings from first config file
        if not merged_config.check_interval:
            merged_config.check_interval = config.check_interval
            merged_config.enable_sound = config.enable_sound
            merged_config.enable_terminal_ui = config.enable_terminal_ui
            merged_config.log_level = config.log_level

    print(f"\n✓ Merged {len(config_paths)} configuration files")
    print(f"  - Total alerts: {len(merged_config.alerts)}")
    print(f"  - Active alerts: {len(merged_config.get_active_alerts())}")

    return merged_config


def create_quick_alert(args) -> AlertConfig:
    """Create a quick alert from command line arguments."""
    from price_alert import AlertRule, AlertCondition, AlertAction, ConditionType, ActionType

    # Determine condition type
    if args.price_above:
        condition = AlertCondition(
            type=ConditionType.PRICE_ABOVE,
            value=Decimal(str(args.price_above))
        )
        alert_name = f"{args.ticker}突破${args.price_above}"
    elif args.price_below:
        condition = AlertCondition(
            type=ConditionType.PRICE_BELOW,
            value=Decimal(str(args.price_below))
        )
        alert_name = f"{args.ticker}跌破${args.price_below}"
    elif args.price_range:
        min_val, max_val = args.price_range.split(',')
        condition = AlertCondition(
            type=ConditionType.PRICE_RANGE,
            min_value=Decimal(min_val),
            max_value=Decimal(max_val)
        )
        alert_name = f"{args.ticker}进入区间[${min_val}-${max_val}]"
    else:
        print("Error: Must specify --price-above, --price-below, or --price-range")
        sys.exit(1)

    # Create action
    channels = args.channels.split(',') if args.channels else ['console']
    action = AlertAction(
        type=ActionType.NOTIFY,
        channels=channels,
        message=args.message if args.message else None
    )

    # Create alert rule
    alert = AlertRule(
        name=alert_name,
        exchange=args.exchange,
        ticker=args.ticker.upper(),
        conditions=[condition],
        actions=[action],
        enabled=True,
        repeat=args.repeat,
        cooldown=args.cooldown
    )

    # Create config
    config = AlertConfig(
        alerts=[alert],
        check_interval=args.interval,
        enable_sound=not args.no_sound,
        log_level=args.log_level
    )

    print(f"\n✓ Created quick alert: {alert_name}")
    return config


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Price Alert System - Monitor cryptocurrency prices and trigger alerts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load alerts from configuration file
  python run_price_alert.py --config config/alerts/btc_alerts.yaml

  # Load multiple configuration files
  python run_price_alert.py --config config/alerts/btc_alerts.yaml config/alerts/eth_alerts.yaml

  # Quick alert - BTC above 65000
  python run_price_alert.py --exchange edgex --ticker BTC --price-above 65000

  # Quick alert - ETH below 3200 with Telegram notification
  python run_price_alert.py --exchange edgex --ticker ETH --price-below 3200 --channels telegram

  # Quick alert - Price range
  python run_price_alert.py --exchange backpack --ticker BTC --price-range 60000,62000
        """
    )

    # Configuration file mode
    parser.add_argument(
        '--config',
        type=str,
        nargs='+',
        help='Path to alert configuration file(s) (YAML)'
    )

    # Quick alert mode
    parser.add_argument(
        '--exchange',
        type=str,
        help='Exchange name for quick alert (e.g., edgex, backpack)'
    )
    parser.add_argument(
        '--ticker',
        type=str,
        help='Ticker symbol for quick alert (e.g., BTC, ETH)'
    )
    parser.add_argument(
        '--price-above',
        type=float,
        help='Alert when price goes above this value'
    )
    parser.add_argument(
        '--price-below',
        type=float,
        help='Alert when price goes below this value'
    )
    parser.add_argument(
        '--price-range',
        type=str,
        help='Alert when price is in range (format: min,max)'
    )
    parser.add_argument(
        '--channels',
        type=str,
        default='console',
        help='Notification channels (comma-separated): telegram,lark,console (default: console)'
    )
    parser.add_argument(
        '--message',
        type=str,
        help='Custom alert message'
    )
    parser.add_argument(
        '--repeat',
        action='store_true',
        help='Allow alert to repeat after cooldown'
    )
    parser.add_argument(
        '--cooldown',
        type=int,
        default=300,
        help='Cooldown period in seconds (default: 300)'
    )

    # General options
    parser.add_argument(
        '--env-file',
        type=str,
        default='.env',
        help='Path to .env file (default: .env)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Price check interval in seconds (default: 10)'
    )
    parser.add_argument(
        '--no-sound',
        action='store_true',
        help='Disable sound alerts'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging
    setup_logging(args.log_level)

    # Load environment variables
    env_path = Path(args.env_file)
    if env_path.exists():
        dotenv.load_dotenv(args.env_file)
        print(f"✓ Loaded environment from {args.env_file}")
    else:
        print(f"Warning: Environment file not found: {args.env_file}")
        print("  Some features (Telegram, Lark) may not work without proper configuration")

    # Load or create configuration
    if args.config:
        # Load from configuration file(s)
        if len(args.config) == 1:
            config = load_config_file(args.config[0])
        else:
            config = load_multiple_configs(args.config)
    elif args.exchange and args.ticker:
        # Create quick alert
        config = create_quick_alert(args)
    else:
        print("Error: Must specify either --config or quick alert parameters (--exchange, --ticker, etc.)")
        print("Run with --help for usage information")
        sys.exit(1)

    # Create and start alert manager
    manager = AlertManager(config)

    try:
        await manager.start()
    except KeyboardInterrupt:
        print("\n\nShutdown signal received...")
    except Exception as e:
        print(f"\nError: {e}")
        logging.exception("Fatal error in alert system")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
