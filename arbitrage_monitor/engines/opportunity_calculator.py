"""套利机会计算引擎"""
import hashlib
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ..models.market_data import (
    MarketTicker,
    OrderBook,
    FundingRate,
    ExchangeConfig,
)
from ..models.arbitrage import (
    ArbitrageOpportunity,
    ArbitrageType,
    TradingCost,
    LiquidityMetrics,
)
from .depth_analyzer import DepthAnalyzer

logger = logging.getLogger(__name__)


class OpportunityCalculator:
    """套利机会计算引擎 - 识别和评估套利机会"""

    def __init__(
        self,
        exchange_configs: Dict[str, ExchangeConfig],
        min_profit_bps: Decimal = Decimal('10'),
        target_size_usd: Decimal = Decimal('5000'),
    ):
        """
        初始化计算引擎

        Args:
            exchange_configs: 交易所配置字典
            min_profit_bps: 最小利润要求（基点）
            target_size_usd: 目标交易规模
        """
        self.exchange_configs = exchange_configs
        self.min_profit_bps = min_profit_bps
        self.target_size_usd = target_size_usd
        self.depth_analyzer = DepthAnalyzer()

    def find_cross_exchange_opportunities(
        self,
        tickers: Dict[str, Dict[str, MarketTicker]],
        orderbooks: Dict[str, Dict[str, OrderBook]],
        funding_rates: Optional[Dict[str, Dict[str, FundingRate]]] = None,
    ) -> List[ArbitrageOpportunity]:
        """
        查找跨交易所套利机会

        Args:
            tickers: 交易所行情数据 {exchange: {symbol: ticker}}
            orderbooks: 订单簿数据 {exchange: {symbol: orderbook}}
            funding_rates: 资金费率数据 {exchange: {symbol: funding_rate}}

        Returns:
            套利机会列表
        """
        opportunities = []

        # 获取所有交易所共同支持的交易对
        common_symbols = self._get_common_symbols(tickers)

        for symbol in common_symbols:
            # 对每个交易对，比较所有交易所的价格
            symbol_tickers = {
                exchange: tickers[exchange][symbol]
                for exchange in tickers
                if symbol in tickers[exchange]
            }

            # 找出买入和卖出的最优交易所
            buy_exchange, sell_exchange, price_spread = self._find_best_spread(symbol_tickers)

            if not buy_exchange or not sell_exchange:
                continue

            # 获取订单簿
            buy_orderbook = orderbooks.get(buy_exchange, {}).get(symbol)
            sell_orderbook = orderbooks.get(sell_exchange, {}).get(symbol)

            if not buy_orderbook or not sell_orderbook:
                logger.debug(f"缺少订单簿数据: {symbol} {buy_exchange}/{sell_exchange}")
                continue

            # 分析流动性
            liquidity = self.depth_analyzer.analyze_liquidity(
                buy_orderbook,
                sell_orderbook,
                self.target_size_usd
            )

            if not liquidity:
                continue

            # 计算交易成本
            trading_cost = self._calculate_trading_cost(
                buy_exchange,
                sell_exchange,
                buy_orderbook,
                sell_orderbook,
            )

            # 计算盈利指标
            buy_price = liquidity.buy_avg_price
            sell_price = liquidity.sell_avg_price
            gross_spread = sell_price - buy_price
            gross_spread_bps = (gross_spread / buy_price) * Decimal('10000')

            # 净价差 = 毛价差 - 总成本
            net_spread = gross_spread - (buy_price * trading_cost.total_cost_rate)
            net_spread_bps = (net_spread / buy_price) * Decimal('10000')

            # 如果净利润低于最小要求，跳过
            if net_spread_bps < self.min_profit_bps:
                continue

            # 获取资金费率差异（如果有）
            funding_rate_diff = None
            funding_rate_annual = None
            if funding_rates:
                buy_funding = funding_rates.get(buy_exchange, {}).get(symbol)
                sell_funding = funding_rates.get(sell_exchange, {}).get(symbol)
                if buy_funding and sell_funding:
                    funding_rate_diff = sell_funding.rate - buy_funding.rate
                    funding_rate_annual = sell_funding.annual_rate - buy_funding.annual_rate

            # 计算风险评分和置信度
            risk_score = self._calculate_risk_score(
                liquidity,
                trading_cost,
                buy_orderbook,
                sell_orderbook,
            )
            confidence_score = self._calculate_confidence_score(
                liquidity,
                symbol_tickers[buy_exchange],
                symbol_tickers[sell_exchange],
            )

            # 计算数据延迟
            data_latency_ms = self._calculate_data_latency(
                symbol_tickers[buy_exchange],
                symbol_tickers[sell_exchange],
            )

            # 生成唯一ID
            opportunity_id = self._generate_opportunity_id(
                symbol, buy_exchange, sell_exchange
            )

            # 创建套利机会
            opportunity = ArbitrageOpportunity(
                opportunity_id=opportunity_id,
                arbitrage_type=ArbitrageType.CROSS_EXCHANGE,
                symbol=symbol,
                exchange_buy=buy_exchange,
                exchange_sell=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                trading_cost=trading_cost,
                liquidity=liquidity,
                gross_spread=gross_spread,
                net_spread=net_spread,
                gross_spread_bps=gross_spread_bps,
                net_spread_bps=net_spread_bps,
                funding_rate_diff=funding_rate_diff,
                funding_rate_annual=funding_rate_annual,
                risk_score=risk_score,
                confidence_score=confidence_score,
                data_latency_ms=data_latency_ms,
            )

            opportunities.append(opportunity)
            logger.info(
                f"发现套利机会: {symbol} {buy_exchange}→{sell_exchange} "
                f"净利润={net_spread_bps:.2f}bps 优先级={opportunity.priority_score:.2f}"
            )

        # 按优先级排序
        opportunities.sort(key=lambda x: x.priority_score, reverse=True)
        return opportunities

    def _get_common_symbols(self, tickers: Dict[str, Dict[str, MarketTicker]]) -> set:
        """获取所有交易所共同支持的交易对"""
        if not tickers:
            return set()

        symbol_sets = [set(exchange_tickers.keys()) for exchange_tickers in tickers.values()]
        return set.intersection(*symbol_sets) if symbol_sets else set()

    def _find_best_spread(
        self,
        symbol_tickers: Dict[str, MarketTicker]
    ) -> tuple[Optional[str], Optional[str], Decimal]:
        """
        找出最优买卖交易所组合

        Returns:
            (买入交易所, 卖出交易所, 价差)
        """
        if len(symbol_tickers) < 2:
            return None, None, Decimal('0')

        # 验证所有ticker数据
        valid_tickers = {
            exchange: ticker
            for exchange, ticker in symbol_tickers.items()
            if ticker.validate() and not ticker.is_stale()
        }

        if len(valid_tickers) < 2:
            return None, None, Decimal('0')

        # 找出最低ask（买入价）和最高bid（卖出价）
        min_ask_exchange = min(valid_tickers.items(), key=lambda x: x[1].ask_price)
        max_bid_exchange = max(valid_tickers.items(), key=lambda x: x[1].bid_price)

        buy_exchange = min_ask_exchange[0]
        sell_exchange = max_bid_exchange[0]
        buy_price = min_ask_exchange[1].ask_price
        sell_price = max_bid_exchange[1].bid_price

        # 如果是同一个交易所，无法套利
        if buy_exchange == sell_exchange:
            return None, None, Decimal('0')

        price_spread = sell_price - buy_price
        return buy_exchange, sell_exchange, price_spread

    def _calculate_trading_cost(
        self,
        buy_exchange: str,
        sell_exchange: str,
        buy_orderbook: OrderBook,
        sell_orderbook: OrderBook,
    ) -> TradingCost:
        """计算交易成本"""
        buy_config = self.exchange_configs.get(buy_exchange)
        sell_config = self.exchange_configs.get(sell_exchange)

        # 默认配置
        if not buy_config:
            buy_fee = Decimal('0.001')  # 0.1%
            withdrawal_fee = Decimal('0.0005')
        else:
            buy_fee = buy_config.taker_fee
            withdrawal_fee = buy_config.withdrawal_fee

        if not sell_config:
            sell_fee = Decimal('0.001')
        else:
            sell_fee = sell_config.taker_fee

        # 计算滑点
        slippage_buy = self.depth_analyzer.calculate_slippage(
            buy_orderbook, 'buy', self.target_size_usd
        )
        slippage_sell = self.depth_analyzer.calculate_slippage(
            sell_orderbook, 'sell', self.target_size_usd
        )

        return TradingCost(
            exchange_buy=buy_exchange,
            exchange_sell=sell_exchange,
            buy_fee=buy_fee,
            sell_fee=sell_fee,
            withdrawal_fee=withdrawal_fee,
            slippage_buy=slippage_buy,
            slippage_sell=slippage_sell,
            transfer_time_minutes=5,
        )

    def _calculate_risk_score(
        self,
        liquidity: LiquidityMetrics,
        trading_cost: TradingCost,
        buy_orderbook: OrderBook,
        sell_orderbook: OrderBook,
    ) -> Decimal:
        """
        计算风险评分 (0-100, 越高越危险)

        考虑因素:
        - 流动性风险（流动性越低越危险）
        - 滑点风险（滑点越大越危险）
        - 转账时间风险
        """
        # 流动性风险 (0-40分)
        liquidity_risk = (Decimal('100') - liquidity.liquidity_score) * Decimal('0.4')

        # 滑点风险 (0-30分)
        slippage_total_bps = (trading_cost.slippage_buy + trading_cost.slippage_sell) * Decimal('10000')
        slippage_risk = min(slippage_total_bps / Decimal('2'), Decimal('30'))

        # 转账时间风险 (0-20分)
        transfer_risk = min(Decimal(trading_cost.transfer_time_minutes) / Decimal('30') * Decimal('20'), Decimal('20'))

        # 深度不平衡风险 (0-10分)
        depth_imbalance = abs(liquidity.buy_depth_usd - liquidity.sell_depth_usd)
        max_depth = max(liquidity.buy_depth_usd, liquidity.sell_depth_usd)
        if max_depth > 0:
            imbalance_ratio = depth_imbalance / max_depth
            imbalance_risk = imbalance_ratio * Decimal('10')
        else:
            imbalance_risk = Decimal('10')

        total_risk = liquidity_risk + slippage_risk + transfer_risk + imbalance_risk
        return min(total_risk, Decimal('100'))

    def _calculate_confidence_score(
        self,
        liquidity: LiquidityMetrics,
        buy_ticker: MarketTicker,
        sell_ticker: MarketTicker,
    ) -> Decimal:
        """
        计算置信度评分 (0-100, 越高越可信)

        考虑因素:
        - 流动性充足度
        - 数据新鲜度
        - 价格稳定性
        """
        # 流动性评分 (0-40分)
        liquidity_confidence = liquidity.liquidity_score * Decimal('0.4')

        # 数据新鲜度 (0-30分)
        buy_age = (datetime.now() - buy_ticker.timestamp).total_seconds()
        sell_age = (datetime.now() - sell_ticker.timestamp).total_seconds()
        max_age = max(buy_age, sell_age)
        freshness_score = max(Decimal('30') - Decimal(str(max_age)) * Decimal('3'), Decimal('0'))

        # 价格稳定性 (0-30分)
        buy_spread_bps = buy_ticker.spread_bps
        sell_spread_bps = sell_ticker.spread_bps
        avg_spread_bps = (buy_spread_bps + sell_spread_bps) / Decimal('2')
        # 价差越小，价格越稳定，置信度越高
        stability_score = max(Decimal('30') - avg_spread_bps / Decimal('3'), Decimal('0'))

        total_confidence = liquidity_confidence + freshness_score + stability_score
        return min(total_confidence, Decimal('100'))

    def _calculate_data_latency(
        self,
        ticker1: MarketTicker,
        ticker2: MarketTicker,
    ) -> int:
        """计算数据延迟（毫秒）"""
        now = datetime.now()
        latency1 = (now - ticker1.timestamp).total_seconds() * 1000
        latency2 = (now - ticker2.timestamp).total_seconds() * 1000
        return int(max(latency1, latency2))

    def _generate_opportunity_id(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
    ) -> str:
        """生成唯一的套利机会ID"""
        hash_input = f"{symbol}_{buy_exchange}_{sell_exchange}_{datetime.now().strftime('%Y%m%d')}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
