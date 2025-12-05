#!/usr/bin/env python3
"""套利监控系统启动脚本"""
import asyncio
import logging
import signal
import sys
from decimal import Decimal
from pathlib import Path

import yaml

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from arbitrage_monitor.models.market_data import ExchangeConfig
from arbitrage_monitor.models.risk import RiskLimits
from arbitrage_monitor.services.arbitrage_service import ArbitrageMonitorService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('arbitrage_monitor.log')
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_file: str = "arbitrage_monitor/config_example.yaml") -> dict:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"配置文件加载成功: {config_file}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        sys.exit(1)


def create_exchange_configs(config: dict) -> dict:
    """创建交易所配置"""
    exchange_configs = {}

    for exchange_name, exchange_data in config.get('exchanges', {}).items():
        exchange_configs[exchange_name] = ExchangeConfig(
            name=exchange_data['name'],
            maker_fee=Decimal(str(exchange_data['maker_fee'])),
            taker_fee=Decimal(str(exchange_data['taker_fee'])),
            withdrawal_fee=Decimal(str(exchange_data['withdrawal_fee'])),
            min_order_size=Decimal(str(exchange_data['min_order_size'])),
            max_order_size=Decimal(str(exchange_data['max_order_size'])),
            supports_funding_rate=exchange_data.get('supports_funding_rate', True),
            api_rate_limit=exchange_data.get('api_rate_limit', 100),
        )

    logger.info(f"已配置 {len(exchange_configs)} 个交易所")
    return exchange_configs


def create_risk_limits(config: dict) -> RiskLimits:
    """创建风险限制"""
    limits_config = config.get('risk_limits', {})

    risk_limits = RiskLimits(
        max_position_size_usd=Decimal(str(limits_config.get('max_position_size_usd', 10000))),
        max_total_exposure_usd=Decimal(str(limits_config.get('max_total_exposure_usd', 50000))),
        max_exchange_exposure_usd=Decimal(str(limits_config.get('max_exchange_exposure_usd', 20000))),
        max_symbol_exposure_usd=Decimal(str(limits_config.get('max_symbol_exposure_usd', 15000))),
        min_profit_bps=Decimal(str(limits_config.get('min_profit_bps', 10))),
        max_risk_score=Decimal(str(limits_config.get('max_risk_score', 70))),
        min_confidence_score=Decimal(str(limits_config.get('min_confidence_score', 60))),
        min_liquidity_score=Decimal(str(limits_config.get('min_liquidity_score', 50))),
        max_slippage_bps=Decimal(str(limits_config.get('max_slippage_bps', 20))),
        max_data_latency_ms=limits_config.get('max_data_latency_ms', 1000),
        max_concurrent_trades=limits_config.get('max_concurrent_trades', 3),
        max_daily_trades=limits_config.get('max_daily_trades', 50),
        max_daily_loss_usd=Decimal(str(limits_config.get('max_daily_loss_usd', 1000))),
    )

    logger.info("风险限制配置完成")
    return risk_limits


async def print_status_loop(service: ArbitrageMonitorService):
    """定期打印状态信息"""
    while service.is_running:
        try:
            await asyncio.sleep(30)  # 每30秒打印一次

            # 获取统计信息
            service_stats = service.get_service_stats()
            risk_report = service.get_risk_report()
            exec_stats = service.get_execution_stats()
            opportunities = service.get_executable_opportunities()

            logger.info("=" * 80)
            logger.info("📊 套利监控系统状态")
            logger.info(f"运行时间: {service_stats['uptime_formatted']}")
            logger.info(f"总扫描次数: {service_stats['total_scans']}")
            logger.info(f"发现机会: {service_stats['total_opportunities_found']}")
            logger.info(f"可执行机会: {service_stats['total_executable_opportunities']}")

            logger.info("\n💰 当前可执行机会:")
            if opportunities:
                for i, opp in enumerate(opportunities[:5], 1):
                    logger.info(
                        f"  {i}. {opp['symbol']} {opp['buy_exchange']}→{opp['sell_exchange']} "
                        f"净利润={opp['net_spread_bps']:.2f}bps "
                        f"优先级={opp['priority_score']:.1f}"
                    )
            else:
                logger.info("  暂无可执行机会")

            logger.info(f"\n⚠️ 风险水平: {risk_report['risk_level']}")
            logger.info(f"敞口使用率: {risk_report['exposure_utilization_pct']:.1f}%")
            logger.info(f"活跃仓位: {risk_report['active_positions']}/{risk_report['max_concurrent_trades']}")
            logger.info(f"今日交易: {risk_report['daily_trades']}/{risk_report['max_daily_trades']}")
            logger.info(f"今日盈亏: ${risk_report['daily_pnl_usd']:.2f}")

            if exec_stats['total_trades'] > 0:
                logger.info(f"\n📈 执行统计:")
                logger.info(f"总交易次数: {exec_stats['total_trades']}")
                logger.info(f"总利润: ${exec_stats['total_profit_usd']:.2f}")
                logger.info(f"平均利润: ${exec_stats['avg_profit_usd']:.2f}")
                logger.info(f"胜率: {exec_stats['win_rate']:.1f}%")

            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"状态打印失败: {e}", exc_info=True)


async def main():
    """主函数"""
    logger.info("🚀 启动套利监控系统...")

    # 加载配置
    config = load_config()

    # 设置日志级别
    log_level = config.get('monitor', {}).get('log_level', 'INFO')
    logging.getLogger().setLevel(getattr(logging, log_level))

    # 创建配置对象
    exchange_configs = create_exchange_configs(config)
    risk_limits = create_risk_limits(config)

    # 获取监控配置
    monitor_config = config.get('monitor', {})
    scan_interval = monitor_config.get('scan_interval', 2)
    auto_execute = monitor_config.get('auto_execute', False)

    # 创建监控服务
    service = ArbitrageMonitorService(
        exchange_configs=exchange_configs,
        risk_limits=risk_limits,
        exchange_adapters={},  # 需要实际的交易所适配器
        auto_execute=auto_execute,
        scan_interval=scan_interval,
    )

    # 设置信号处理
    def signal_handler(sig, frame):
        logger.info("\n收到停止信号，正在关闭...")
        asyncio.create_task(service.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动服务
    await service.start()

    # 启动状态打印循环
    status_task = asyncio.create_task(print_status_loop(service))

    logger.info("✅ 套利监控系统运行中...")
    logger.info("⚠️  注意: 当前为演示模式，需要接入实际交易所数据源")
    logger.info("按 Ctrl+C 停止程序\n")

    # 等待服务运行
    try:
        while service.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    finally:
        await service.stop()
        status_task.cancel()

    logger.info("👋 套利监控系统已退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)
