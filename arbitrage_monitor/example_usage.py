#!/usr/bin/env python3
"""套利监控系统使用示例"""
import asyncio
from datetime import datetime
from decimal import Decimal

from models.market_data import (
    MarketTicker,
    OrderBook,
    OrderBookLevel,
    FundingRate,
    ExchangeConfig,
)
from models.arbitrage import ArbitrageType
from models.risk import RiskLimits
from services.arbitrage_service import ArbitrageMonitorService


def create_sample_ticker(
    exchange: str,
    symbol: str,
    bid: float,
    ask: float,
    volume: float = 1000.0
) -> MarketTicker:
    """创建示例ticker数据"""
    bid_dec = Decimal(str(bid))
    ask_dec = Decimal(str(ask))
    mid = (bid_dec + ask_dec) / Decimal('2')

    return MarketTicker(
        exchange=exchange,
        symbol=symbol,
        bid_price=bid_dec,
        ask_price=ask_dec,
        mid_price=mid,
        bid_volume=Decimal(str(volume)),
        ask_volume=Decimal(str(volume)),
        last_price=mid,
        volume_24h=Decimal(str(volume * 100)),
        timestamp=datetime.now(),
    )


def create_sample_orderbook(
    exchange: str,
    symbol: str,
    base_price: float,
    depth: int = 10
) -> OrderBook:
    """创建示例订单簿"""
    base = Decimal(str(base_price))
    tick = base * Decimal('0.0001')  # 0.01% tick size

    # 生成买单（从高到低）
    bids = []
    for i in range(depth):
        price = base - (tick * i)
        volume = Decimal('10') * (1 + i * Decimal('0.1'))
        bids.append(OrderBookLevel(price=price, volume=volume))

    # 生成卖单（从低到高）
    asks = []
    for i in range(depth):
        price = base + (tick * (i + 1))
        volume = Decimal('10') * (1 + i * Decimal('0.1'))
        asks.append(OrderBookLevel(price=price, volume=volume))

    return OrderBook(
        exchange=exchange,
        symbol=symbol,
        bids=bids,
        asks=asks,
        timestamp=datetime.now(),
    )


def create_sample_funding_rate(
    exchange: str,
    symbol: str,
    rate: float
) -> FundingRate:
    """创建示例资金费率"""
    return FundingRate(
        exchange=exchange,
        symbol=symbol,
        rate=Decimal(str(rate)),
        predicted_rate=Decimal(str(rate)),
        timestamp=datetime.now(),
    )


async def example_basic_monitoring():
    """示例1: 基础监控"""
    print("=" * 80)
    print("示例1: 基础套利监控")
    print("=" * 80)

    # 创建交易所配置
    exchange_configs = {
        'edgex': ExchangeConfig(
            name='EdgeX',
            maker_fee=Decimal('0.0002'),
            taker_fee=Decimal('0.0005'),
            withdrawal_fee=Decimal('0.0001'),
            min_order_size=Decimal('10'),
            max_order_size=Decimal('100000'),
        ),
        'lighter': ExchangeConfig(
            name='Lighter',
            maker_fee=Decimal('0.0001'),
            taker_fee=Decimal('0.0004'),
            withdrawal_fee=Decimal('0.0001'),
            min_order_size=Decimal('10'),
            max_order_size=Decimal('100000'),
        ),
    }

    # 创建风险限制
    risk_limits = RiskLimits(
        max_position_size_usd=Decimal('10000'),
        min_profit_bps=Decimal('5'),
        max_concurrent_trades=3,
    )

    # 创建监控服务
    service = ArbitrageMonitorService(
        exchange_configs=exchange_configs,
        risk_limits=risk_limits,
        auto_execute=False,  # 模拟模式
        scan_interval=2,
    )

    # 模拟市场数据 - EdgeX价格较低
    edgex_tickers = {
        'BTC-PERP': create_sample_ticker('edgex', 'BTC-PERP', 50000, 50010),
        'ETH-PERP': create_sample_ticker('edgex', 'ETH-PERP', 3000, 3002),
    }
    edgex_orderbooks = {
        'BTC-PERP': create_sample_orderbook('edgex', 'BTC-PERP', 50005),
        'ETH-PERP': create_sample_orderbook('edgex', 'ETH-PERP', 3001),
    }

    # 模拟市场数据 - Lighter价格较高（存在套利空间）
    lighter_tickers = {
        'BTC-PERP': create_sample_ticker('lighter', 'BTC-PERP', 50080, 50090),
        'ETH-PERP': create_sample_ticker('lighter', 'ETH-PERP', 3010, 3012),
    }
    lighter_orderbooks = {
        'BTC-PERP': create_sample_orderbook('lighter', 'BTC-PERP', 50085),
        'ETH-PERP': create_sample_orderbook('lighter', 'ETH-PERP', 3011),
    }

    # 更新市场数据
    service.update_market_data('edgex', edgex_tickers, edgex_orderbooks)
    service.update_market_data('lighter', lighter_tickers, lighter_orderbooks)

    # 启动服务
    await service.start()

    # 等待扫描
    await asyncio.sleep(3)

    # 获取套利机会
    opportunities = service.get_executable_opportunities()

    print(f"\n✅ 发现 {len(opportunities)} 个可执行套利机会:\n")

    for i, opp in enumerate(opportunities, 1):
        print(f"机会 {i}:")
        print(f"  币种: {opp['symbol']}")
        print(f"  路径: {opp['buy_exchange']} → {opp['sell_exchange']}")
        print(f"  买入价: ${opp['buy_price']:.2f}")
        print(f"  卖出价: ${opp['sell_price']:.2f}")
        print(f"  毛价差: {opp['gross_spread_bps']:.2f} bps")
        print(f"  净价差: {opp['net_spread_bps']:.2f} bps")
        print(f"  优先级评分: {opp['priority_score']:.2f}")
        print(f"  风险评分: {opp['risk_score']:.2f}")
        print(f"  置信度: {opp['confidence_score']:.2f}")
        print()

    # 获取统计信息
    stats = service.get_service_stats()
    print(f"📊 服务统计:")
    print(f"  总扫描次数: {stats['total_scans']}")
    print(f"  发现机会: {stats['total_opportunities_found']}")
    print(f"  可执行机会: {stats['total_executable_opportunities']}")

    # 停止服务
    await service.stop()


async def example_risk_management():
    """示例2: 风险管理"""
    print("\n" + "=" * 80)
    print("示例2: 风险管理演示")
    print("=" * 80)

    from engines.risk_manager import RiskManager
    from models.arbitrage import ArbitrageOpportunity, TradingCost, LiquidityMetrics

    # 创建风险管理器
    risk_limits = RiskLimits(
        max_position_size_usd=Decimal('5000'),
        max_total_exposure_usd=Decimal('20000'),
        min_profit_bps=Decimal('10'),
        max_concurrent_trades=2,
    )

    risk_manager = RiskManager(risk_limits)

    # 创建一个套利机会
    opportunity = ArbitrageOpportunity(
        opportunity_id='test_001',
        arbitrage_type=ArbitrageType.CROSS_EXCHANGE,
        symbol='BTC-PERP',
        exchange_buy='edgex',
        exchange_sell='lighter',
        buy_price=Decimal('50000'),
        sell_price=Decimal('50100'),
        trading_cost=TradingCost(
            exchange_buy='edgex',
            exchange_sell='lighter',
            buy_fee=Decimal('0.0005'),
            sell_fee=Decimal('0.0005'),
            withdrawal_fee=Decimal('0.0001'),
            slippage_buy=Decimal('0.0002'),
            slippage_sell=Decimal('0.0002'),
        ),
        liquidity=LiquidityMetrics(
            buy_depth_usd=Decimal('50000'),
            sell_depth_usd=Decimal('50000'),
            buy_avg_price=Decimal('50010'),
            sell_avg_price=Decimal('50090'),
            liquidity_score=Decimal('80'),
            max_executable_size=Decimal('10000'),
        ),
        gross_spread=Decimal('100'),
        net_spread=Decimal('35'),
        gross_spread_bps=Decimal('20'),
        net_spread_bps=Decimal('7'),
        risk_score=Decimal('45'),
        confidence_score=Decimal('75'),
    )

    # 测试1: 验证机会
    print("\n📋 测试1: 验证套利机会")
    is_valid, reason = risk_manager.validate_opportunity(opportunity, Decimal('3000'))
    print(f"  投资额 $3000: {'✅ 通过' if is_valid else '❌ 拒绝'}")
    if reason:
        print(f"  原因: {reason}")

    # 测试2: 创建执行计划
    print("\n📋 测试2: 创建执行计划")
    plan = risk_manager.create_execution_plan(opportunity, Decimal('3000'))
    if plan:
        print(f"  ✅ 执行计划创建成功")
        print(f"  投资额: ${plan.investment_usd}")
        print(f"  预期利润: ${plan.expected_profit_usd:.2f}")
        print(f"  预期收益率: {plan.expected_profit_rate * 100:.3f}%")
    else:
        print(f"  ❌ 无法创建执行计划")

    # 测试3: 模拟仓位开启
    if plan:
        print("\n📋 测试3: 模拟仓位开启")
        risk_manager.on_position_opened(plan, Decimal('50010'), Decimal('50090'))
        print(f"  ✅ 仓位已开启")

        # 获取风险报告
        report = risk_manager.get_risk_report()
        print(f"  总敞口: ${report['total_exposure_usd']:.2f}")
        print(f"  活跃仓位: {report['active_positions']}")
        print(f"  风险水平: {report['risk_level']}")

        # 测试4: 模拟仓位关闭
        print("\n📋 测试4: 模拟仓位关闭")
        risk_manager.on_position_closed(plan, Decimal('210'))  # $210 利润
        print(f"  ✅ 仓位已关闭")

        # 获取更新后的风险报告
        report = risk_manager.get_risk_report()
        print(f"  总敞口: ${report['total_exposure_usd']:.2f}")
        print(f"  活跃仓位: {report['active_positions']}")
        print(f"  今日盈亏: ${report['daily_pnl_usd']:.2f}")


async def example_depth_analysis():
    """示例3: 市场深度分析"""
    print("\n" + "=" * 80)
    print("示例3: 市场深度分析")
    print("=" * 80)

    from engines.depth_analyzer import DepthAnalyzer

    analyzer = DepthAnalyzer()

    # 创建订单簿
    buy_orderbook = create_sample_orderbook('edgex', 'BTC-PERP', 50000, depth=20)
    sell_orderbook = create_sample_orderbook('lighter', 'BTC-PERP', 50100, depth=20)

    # 分析流动性
    print("\n📊 流动性分析:")
    liquidity = analyzer.analyze_liquidity(
        buy_orderbook,
        sell_orderbook,
        target_size_usd=Decimal('5000')
    )

    if liquidity:
        print(f"  买入深度: ${liquidity.buy_depth_usd:.2f}")
        print(f"  卖出深度: ${liquidity.sell_depth_usd:.2f}")
        print(f"  买入平均价: ${liquidity.buy_avg_price:.2f}")
        print(f"  卖出平均价: ${liquidity.sell_avg_price:.2f}")
        print(f"  流动性评分: {liquidity.liquidity_score:.2f}")
        print(f"  最大可执行规模: ${liquidity.max_executable_size:.2f}")
        print(f"  是否充足: {'✅ 是' if liquidity.is_sufficient() else '❌ 否'}")

    # 计算滑点
    print("\n📊 滑点分析:")
    buy_slippage = analyzer.calculate_slippage(buy_orderbook, 'buy', Decimal('5000'))
    sell_slippage = analyzer.calculate_slippage(sell_orderbook, 'sell', Decimal('5000'))

    print(f"  买入滑点: {buy_slippage * 10000:.2f} bps")
    print(f"  卖出滑点: {sell_slippage * 10000:.2f} bps")
    print(f"  总滑点: {(buy_slippage + sell_slippage) * 10000:.2f} bps")

    # 市场冲击评估
    print("\n📊 市场冲击评估:")
    for size in [1000, 5000, 10000]:
        impact = analyzer.estimate_market_impact(buy_orderbook, 'buy', Decimal(str(size)))
        print(f"  ${size} 规模:")
        print(f"    平均价格: ${impact['avg_price']:.2f}")
        print(f"    滑点: {impact['slippage_bps']:.2f} bps")
        print(f"    深度消耗: {impact['depth_consumed_pct']:.1f}%")
        print(f"    可执行: {'✅' if impact['is_executable'] else '❌'}")


async def main():
    """运行所有示例"""
    print("🚀 套利监控系统使用示例\n")

    # 示例1: 基础监控
    await example_basic_monitoring()

    # 示例2: 风险管理
    await example_risk_management()

    # 示例3: 深度分析
    await example_depth_analysis()

    print("\n" + "=" * 80)
    print("✅ 所有示例执行完成!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
