#!/usr/bin/env python3
"""
Arbitrage Engine Runner
套利引擎启动脚本
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from decimal import Decimal
import dotenv

from arbitrage_engine import ArbitrageEngine


def setup_logging(log_level: str):
    """设置日志"""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 抑制噪音日志
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Arbitrage Engine - Automated cross-exchange arbitrage trading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 监控模式（只显示机会，不执行）
  python run_arbitrage.py --exchanges edgex backpack --tickers BTC ETH

  # 监控所有交易所
  python run_arbitrage.py --exchanges edgex backpack lighter aster --tickers BTC ETH SOL

  # 自动执行模式（谨慎使用！）
  python run_arbitrage.py --exchanges edgex backpack --tickers BTC --auto-execute

  # 高频监控（1秒间隔）
  python run_arbitrage.py --exchanges edgex backpack --tickers BTC --interval 1

  # 设置最小利润率
  python run_arbitrage.py --exchanges edgex backpack --tickers ETH --min-profit 0.5
        """
    )

    # 基础参数
    parser.add_argument(
        '--exchanges',
        type=str,
        nargs='+',
        default=['edgex', 'backpack'],
        help='监控的交易所列表 (默认: edgex backpack)'
    )
    parser.add_argument(
        '--tickers',
        type=str,
        nargs='+',
        default=['BTC', 'ETH'],
        help='监控的币种列表 (默认: BTC ETH)'
    )
    parser.add_argument(
        '--min-profit',
        type=float,
        default=0.3,
        help='最小利润率阈值 (%%) (默认: 0.3)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='价格检查间隔（秒）(默认: 5)'
    )

    # 执行参数
    parser.add_argument(
        '--auto-execute',
        action='store_true',
        help='自动执行套利交易（谨慎使用！）'
    )
    parser.add_argument(
        '--max-position',
        type=float,
        default=1000,
        help='最大仓位大小（USDT）(默认: 1000)'
    )
    parser.add_argument(
        '--slippage',
        type=float,
        default=0.1,
        help='滑点估算 (%%) (默认: 0.1)'
    )

    # 通用选项
    parser.add_argument(
        '--env-file',
        type=str,
        default='.env',
        help='.env 文件路径 (默认: .env)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别 (默认: INFO)'
    )

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_arguments()

    # 设置日志
    setup_logging(args.log_level)

    # 加载环境变量
    env_path = Path(args.env_file)
    if env_path.exists():
        dotenv.load_dotenv(args.env_file)
        print(f"✓ 加载环境配置: {args.env_file}")
    else:
        print(f"⚠️  环境文件未找到: {args.env_file}")

    # 创建配置
    config = {
        'exchanges': args.exchanges,
        'tickers': [t.upper() for t in args.tickers],
        'min_profit_percent': Decimal(str(args.min_profit)),
        'check_interval': args.interval,
        'auto_execute': args.auto_execute,
        'max_position_size': Decimal(str(args.max_position)),
        'slippage_percent': Decimal(str(args.slippage)),
    }

    # 安全确认
    if args.auto_execute:
        print("\n" + "=" * 80)
        print("⚠️  警告：自动执行模式已启用！")
        print("=" * 80)
        print("这将自动执行套利交易，可能导致资金损失。")
        print("确保你理解风险并已经充分测试。")
        print("=" * 80)
        response = input("\n输入 'YES' 确认继续，或按 Ctrl+C 取消: ")
        if response != 'YES':
            print("已取消。")
            sys.exit(0)

    # 创建并启动引擎
    engine = ArbitrageEngine(config)

    try:
        await engine.start_monitoring()
    except KeyboardInterrupt:
        print("\n正在停止...")
    except Exception as e:
        print(f"\n错误: {e}")
        logging.exception("Fatal error in arbitrage engine")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已退出。")
        sys.exit(0)
