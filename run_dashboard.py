#!/usr/bin/env python3
"""
Web Dashboard Launcher
网页仪表盘启动器
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import dotenv
import uvicorn


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Crypto Trading Web Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 启动仪表盘（默认 8000 端口）
  python run_dashboard.py

  # 指定端口
  python run_dashboard.py --port 8080

  # 绑定到所有网络接口
  python run_dashboard.py --host 0.0.0.0 --port 8000

  # 同时启动套利引擎
  python run_dashboard.py --enable-arbitrage --exchanges edgex backpack --tickers BTC ETH
        """
    )

    # 服务器配置
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='服务器主机地址 (默认: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='服务器端口 (默认: 8000)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='启用热重载（开发模式）'
    )

    # 套利引擎配置
    parser.add_argument(
        '--enable-arbitrage',
        action='store_true',
        help='启动时自动启用套利引擎'
    )
    parser.add_argument(
        '--exchanges',
        type=str,
        nargs='+',
        default=['edgex', 'backpack'],
        help='监控的交易所 (默认: edgex backpack)'
    )
    parser.add_argument(
        '--tickers',
        type=str,
        nargs='+',
        default=['BTC', 'ETH'],
        help='监控的币种 (默认: BTC ETH)'
    )
    parser.add_argument(
        '--min-profit',
        type=float,
        default=0.3,
        help='最小利润率阈值 (默认: 0.3)'
    )

    # 环境配置
    parser.add_argument(
        '--env-file',
        type=str,
        default='.env',
        help='.env 文件路径 (默认: .env)'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    # 加载环境变量
    env_path = Path(args.env_file)
    if env_path.exists():
        dotenv.load_dotenv(args.env_file)
        print(f"✓ 加载环境配置: {args.env_file}")
    else:
        print(f"⚠️  环境文件未找到: {args.env_file}")

    print("\n" + "=" * 80)
    print("🚀 Crypto Trading Web Dashboard")
    print("=" * 80)
    print(f"📍 Dashboard: http://{args.host}:{args.port}/dashboard")
    print(f"📚 API Docs: http://{args.host}:{args.port}/docs")
    print(f"📡 WebSocket: ws://{args.host}:{args.port}/ws")
    print("=" * 80)

    if args.enable_arbitrage:
        print("\n⚙️  套利引擎配置:")
        print(f"   交易所: {', '.join(args.exchanges)}")
        print(f"   币种: {', '.join(args.tickers)}")
        print(f"   最小利润率: {args.min_profit}%")
        print()

    print("💡 提示:")
    print("   - 在浏览器中打开 Dashboard 地址查看实时监控")
    print("   - 使用 API Docs 查看所有可用的 API 接口")
    print("   - 按 Ctrl+C 停止服务器")
    print("=" * 80 + "\n")

    # 启动服务器
    try:
        uvicorn.run(
            "web_dashboard.app:create_app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            factory=True
        )
    except KeyboardInterrupt:
        print("\n\n正在关闭服务器...")
        print("已退出。")
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
