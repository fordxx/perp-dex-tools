"""市场深度分析器"""
import logging
from decimal import Decimal
from typing import Optional

from ..models.market_data import OrderBook, OrderBookLevel
from ..models.arbitrage import LiquidityMetrics

logger = logging.getLogger(__name__)


class DepthAnalyzer:
    """市场深度分析器 - 评估订单簿流动性和可执行性"""

    def __init__(self, min_depth_usd: Decimal = Decimal('1000')):
        self.min_depth_usd = min_depth_usd

    def analyze_liquidity(
        self,
        buy_orderbook: OrderBook,
        sell_orderbook: OrderBook,
        target_size_usd: Decimal = Decimal('5000')
    ) -> Optional[LiquidityMetrics]:
        """
        分析套利所需的买卖方向流动性

        Args:
            buy_orderbook: 买入方向订单簿（需要从asks买入）
            sell_orderbook: 卖出方向订单簿（需要向bids卖出）
            target_size_usd: 目标交易规模（美元）

        Returns:
            LiquidityMetrics 或 None（如果流动性不足）
        """
        try:
            # 计算买入方向（从asks买入）的深度和平均价格
            buy_avg_price = buy_orderbook.get_ask_depth(target_size_usd)
            buy_depth_usd = self._calculate_depth(buy_orderbook.asks, buy_avg_price)

            # 计算卖出方向（向bids卖出）的深度和平均价格
            sell_avg_price = sell_orderbook.get_bid_depth(target_size_usd)
            sell_depth_usd = self._calculate_depth(sell_orderbook.bids, sell_avg_price)

            # 如果任一方向平均价格为0，说明流动性不足
            if buy_avg_price == 0 or sell_avg_price == 0:
                logger.debug(
                    f"流动性不足: {buy_orderbook.exchange}-{buy_orderbook.symbol} "
                    f"buy_avg={buy_avg_price}, sell_avg={sell_avg_price}"
                )
                return None

            # 计算流动性评分
            buy_liquidity_score = buy_orderbook.get_liquidity_score(target_size_usd)
            sell_liquidity_score = sell_orderbook.get_liquidity_score(target_size_usd)
            liquidity_score = (buy_liquidity_score + sell_liquidity_score) / Decimal('2')

            # 计算最大可执行规模
            max_executable_size = min(buy_depth_usd, sell_depth_usd)

            return LiquidityMetrics(
                buy_depth_usd=buy_depth_usd,
                sell_depth_usd=sell_depth_usd,
                buy_avg_price=buy_avg_price,
                sell_avg_price=sell_avg_price,
                liquidity_score=liquidity_score,
                max_executable_size=max_executable_size,
            )

        except Exception as e:
            logger.error(f"流动性分析失败: {e}", exc_info=True)
            return None

    def _calculate_depth(
        self,
        levels: list[OrderBookLevel],
        avg_price: Decimal
    ) -> Decimal:
        """
        计算订单簿深度（美元）

        Args:
            levels: 订单簿价格档位列表
            avg_price: 平均价格

        Returns:
            深度（美元）
        """
        total_depth = Decimal('0')
        for level in levels:
            # 如果价格偏离平均价格超过1%，停止累加
            price_deviation = abs(level.price - avg_price) / avg_price
            if price_deviation > Decimal('0.01'):
                break
            total_depth += level.notional_value

        return total_depth

    def calculate_slippage(
        self,
        orderbook: OrderBook,
        side: str,
        target_size_usd: Decimal
    ) -> Decimal:
        """
        计算预期滑点

        Args:
            orderbook: 订单簿
            side: 'buy' 或 'sell'
            target_size_usd: 目标交易规模

        Returns:
            预期滑点百分比
        """
        try:
            if side == 'buy':
                # 买入：使用asks
                best_price = orderbook.asks[0].price if orderbook.asks else Decimal('0')
                avg_price = orderbook.get_ask_depth(target_size_usd)
            else:
                # 卖出：使用bids
                best_price = orderbook.bids[0].price if orderbook.bids else Decimal('0')
                avg_price = orderbook.get_bid_depth(target_size_usd)

            if best_price == 0 or avg_price == 0:
                return Decimal('999')  # 无法计算，返回极大值

            # 滑点 = (实际价格 - 最优价格) / 最优价格
            if side == 'buy':
                slippage = (avg_price - best_price) / best_price
            else:
                slippage = (best_price - avg_price) / best_price

            return max(slippage, Decimal('0'))

        except Exception as e:
            logger.error(f"滑点计算失败: {e}", exc_info=True)
            return Decimal('999')

    def estimate_market_impact(
        self,
        orderbook: OrderBook,
        side: str,
        size_usd: Decimal
    ) -> dict:
        """
        估算市场冲击

        Args:
            orderbook: 订单簿
            side: 'buy' 或 'sell'
            size_usd: 交易规模

        Returns:
            包含冲击分析的字典
        """
        levels = orderbook.asks if side == 'buy' else orderbook.bids
        if not levels:
            return {
                'avg_price': Decimal('0'),
                'slippage_bps': Decimal('999999'),
                'depth_consumed_pct': Decimal('100'),
                'is_executable': False,
            }

        best_price = levels[0].price
        total_depth = sum(level.notional_value for level in levels[:20])

        # 计算平均价格和滑点
        if side == 'buy':
            avg_price = orderbook.get_ask_depth(size_usd)
        else:
            avg_price = orderbook.get_bid_depth(size_usd)

        if avg_price == 0:
            slippage_bps = Decimal('999999')
        else:
            if side == 'buy':
                slippage = (avg_price - best_price) / best_price
            else:
                slippage = (best_price - avg_price) / best_price
            slippage_bps = slippage * Decimal('10000')

        # 计算深度消耗比例
        depth_consumed_pct = (size_usd / total_depth * Decimal('100')) if total_depth > 0 else Decimal('100')

        # 判断是否可执行
        is_executable = (
            avg_price > 0 and
            slippage_bps < Decimal('50') and  # 滑点小于0.5%
            depth_consumed_pct < Decimal('80')  # 不消耗超过80%的深度
        )

        return {
            'avg_price': avg_price,
            'slippage_bps': slippage_bps,
            'depth_consumed_pct': depth_consumed_pct,
            'is_executable': is_executable,
            'total_depth_usd': total_depth,
        }

    def compare_liquidity(
        self,
        orderbook1: OrderBook,
        orderbook2: OrderBook
    ) -> dict:
        """
        比较两个订单簿的流动性

        Returns:
            比较结果字典
        """
        liquidity1 = orderbook1.get_liquidity_score()
        liquidity2 = orderbook2.get_liquidity_score()

        depth1 = sum(level.notional_value for level in orderbook1.bids[:10] + orderbook1.asks[:10])
        depth2 = sum(level.notional_value for level in orderbook2.bids[:10] + orderbook2.asks[:10])

        return {
            f'{orderbook1.exchange}_liquidity_score': float(liquidity1),
            f'{orderbook2.exchange}_liquidity_score': float(liquidity2),
            f'{orderbook1.exchange}_depth_usd': float(depth1),
            f'{orderbook2.exchange}_depth_usd': float(depth2),
            'better_liquidity': orderbook1.exchange if liquidity1 > liquidity2 else orderbook2.exchange,
        }
