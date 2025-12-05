"""交易执行引擎"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Protocol

from ..models.arbitrage import ExecutionPlan

logger = logging.getLogger(__name__)


class ExchangeAdapter(Protocol):
    """交易所适配器协议 - 定义交易所需要实现的接口"""

    async def create_market_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        quantity: Decimal,
    ) -> dict:
        """创建市价单"""
        ...

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """创建限价单"""
        ...

    async def get_order_status(self, order_id: str) -> dict:
        """获取订单状态"""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        ...


class ExecutionEngine:
    """交易执行引擎 - 负责执行套利交易"""

    def __init__(
        self,
        exchange_adapters: dict[str, ExchangeAdapter],
        auto_execute: bool = False,
    ):
        """
        初始化执行引擎

        Args:
            exchange_adapters: 交易所适配器字典 {exchange_name: adapter}
            auto_execute: 是否自动执行（False为模拟模式）
        """
        self.exchange_adapters = exchange_adapters
        self.auto_execute = auto_execute
        self.execution_history = []

    async def execute_arbitrage(
        self,
        plan: ExecutionPlan,
        use_limit_orders: bool = False,
    ) -> tuple[bool, Optional[str], Optional[Decimal]]:
        """
        执行套利交易

        Args:
            plan: 执行计划
            use_limit_orders: 是否使用限价单（False使用市价单）

        Returns:
            (是否成功, 失败原因, 实际利润)
        """
        if not self.auto_execute:
            logger.info(f"[模拟模式] 执行套利: {plan.opportunity.symbol}")
            return await self._simulate_execution(plan)

        opportunity = plan.opportunity
        logger.info(
            f"开始执行套利: {opportunity.symbol} "
            f"{opportunity.exchange_buy}→{opportunity.exchange_sell} "
            f"规模=${plan.investment_usd}"
        )

        # 验证交易所适配器是否存在
        if opportunity.exchange_buy not in self.exchange_adapters:
            return False, f"缺少{opportunity.exchange_buy}交易所适配器", None

        if opportunity.exchange_sell not in self.exchange_adapters:
            return False, f"缺少{opportunity.exchange_sell}交易所适配器", None

        buy_adapter = self.exchange_adapters[opportunity.exchange_buy]
        sell_adapter = self.exchange_adapters[opportunity.exchange_sell]

        try:
            # 同时下买单和卖单
            start_time = datetime.now()

            if use_limit_orders:
                buy_task = self._execute_limit_buy(
                    buy_adapter,
                    opportunity.symbol,
                    plan.buy_quantity,
                    opportunity.buy_price,
                )
                sell_task = self._execute_limit_sell(
                    sell_adapter,
                    opportunity.symbol,
                    plan.sell_quantity,
                    opportunity.sell_price,
                )
            else:
                buy_task = self._execute_market_buy(
                    buy_adapter,
                    opportunity.symbol,
                    plan.buy_quantity,
                )
                sell_task = self._execute_market_sell(
                    sell_adapter,
                    opportunity.symbol,
                    plan.sell_quantity,
                )

            # 并行执行买卖单，设置超时
            results = await asyncio.wait_for(
                asyncio.gather(buy_task, sell_task, return_exceptions=True),
                timeout=plan.timeout_seconds
            )

            buy_result, sell_result = results

            # 检查是否有异常
            if isinstance(buy_result, Exception):
                logger.error(f"买单失败: {buy_result}")
                # 如果买单失败，尝试取消卖单
                if not isinstance(sell_result, Exception) and 'order_id' in sell_result:
                    await sell_adapter.cancel_order(sell_result['order_id'])
                return False, f"买单失败: {str(buy_result)}", None

            if isinstance(sell_result, Exception):
                logger.error(f"卖单失败: {sell_result}")
                # 如果卖单失败，尝试取消买单
                if 'order_id' in buy_result:
                    await buy_adapter.cancel_order(buy_result['order_id'])
                return False, f"卖单失败: {str(sell_result)}", None

            # 计算实际利润
            actual_buy_price = Decimal(str(buy_result['avg_price']))
            actual_sell_price = Decimal(str(sell_result['avg_price']))
            actual_quantity = min(
                Decimal(str(buy_result['filled_quantity'])),
                Decimal(str(sell_result['filled_quantity']))
            )

            actual_profit = (actual_sell_price - actual_buy_price) * actual_quantity
            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录执行历史
            self._record_execution(plan, buy_result, sell_result, actual_profit, execution_time)

            logger.info(
                f"套利执行成功: {opportunity.symbol} "
                f"实际利润=${actual_profit:.2f} "
                f"耗时={execution_time:.2f}s"
            )

            return True, None, actual_profit

        except asyncio.TimeoutError:
            logger.error(f"执行超时: {plan.timeout_seconds}秒")
            return False, "执行超时", None

        except Exception as e:
            logger.error(f"执行失败: {e}", exc_info=True)
            return False, f"执行异常: {str(e)}", None

    async def _execute_market_buy(
        self,
        adapter: ExchangeAdapter,
        symbol: str,
        quantity: Decimal,
    ) -> dict:
        """执行市价买单"""
        logger.debug(f"下市价买单: {symbol} 数量={quantity}")
        result = await adapter.create_market_order(symbol, 'buy', quantity)
        return result

    async def _execute_market_sell(
        self,
        adapter: ExchangeAdapter,
        symbol: str,
        quantity: Decimal,
    ) -> dict:
        """执行市价卖单"""
        logger.debug(f"下市价卖单: {symbol} 数量={quantity}")
        result = await adapter.create_market_order(symbol, 'sell', quantity)
        return result

    async def _execute_limit_buy(
        self,
        adapter: ExchangeAdapter,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """执行限价买单"""
        logger.debug(f"下限价买单: {symbol} 数量={quantity} 价格={price}")
        result = await adapter.create_limit_order(symbol, 'buy', quantity, price)

        # 等待订单成交或部分成交
        order_id = result['order_id']
        for _ in range(10):  # 最多等待10次
            await asyncio.sleep(0.5)
            status = await adapter.get_order_status(order_id)
            if status['status'] in ['filled', 'partially_filled']:
                return status

        # 超时未成交，取消订单
        await adapter.cancel_order(order_id)
        raise Exception("限价单超时未成交")

    async def _execute_limit_sell(
        self,
        adapter: ExchangeAdapter,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> dict:
        """执行限价卖单"""
        logger.debug(f"下限价卖单: {symbol} 数量={quantity} 价格={price}")
        result = await adapter.create_limit_order(symbol, 'sell', quantity, price)

        # 等待订单成交或部分成交
        order_id = result['order_id']
        for _ in range(10):
            await asyncio.sleep(0.5)
            status = await adapter.get_order_status(order_id)
            if status['status'] in ['filled', 'partially_filled']:
                return status

        # 超时未成交，取消订单
        await adapter.cancel_order(order_id)
        raise Exception("限价单超时未成交")

    async def _simulate_execution(
        self,
        plan: ExecutionPlan,
    ) -> tuple[bool, Optional[str], Optional[Decimal]]:
        """
        模拟执行（用于测试）

        Returns:
            (True, None, 预期利润)
        """
        # 模拟网络延迟
        await asyncio.sleep(0.1)

        opportunity = plan.opportunity

        logger.info(
            f"[模拟] 买入 {plan.buy_quantity} {opportunity.symbol} "
            f"@ {opportunity.buy_price} on {opportunity.exchange_buy}"
        )
        logger.info(
            f"[模拟] 卖出 {plan.sell_quantity} {opportunity.symbol} "
            f"@ {opportunity.sell_price} on {opportunity.exchange_sell}"
        )
        logger.info(f"[模拟] 预期利润: ${plan.expected_profit_usd:.2f}")

        return True, None, plan.expected_profit_usd

    def _record_execution(
        self,
        plan: ExecutionPlan,
        buy_result: dict,
        sell_result: dict,
        actual_profit: Decimal,
        execution_time: float,
    ):
        """记录执行历史"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': plan.opportunity.symbol,
            'buy_exchange': plan.opportunity.exchange_buy,
            'sell_exchange': plan.opportunity.exchange_sell,
            'investment_usd': float(plan.investment_usd),
            'expected_profit_usd': float(plan.expected_profit_usd),
            'actual_profit_usd': float(actual_profit),
            'execution_time_seconds': execution_time,
            'buy_order': {
                'order_id': buy_result.get('order_id'),
                'avg_price': float(buy_result.get('avg_price', 0)),
                'filled_quantity': float(buy_result.get('filled_quantity', 0)),
            },
            'sell_order': {
                'order_id': sell_result.get('order_id'),
                'avg_price': float(sell_result.get('avg_price', 0)),
                'filled_quantity': float(sell_result.get('filled_quantity', 0)),
            },
        }
        self.execution_history.append(record)

        # 保持最近100条记录
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_execution_stats(self) -> dict:
        """获取执行统计"""
        if not self.execution_history:
            return {
                'total_trades': 0,
                'total_profit_usd': 0,
                'avg_profit_usd': 0,
                'win_rate': 0,
                'avg_execution_time': 0,
            }

        total_trades = len(self.execution_history)
        total_profit = sum(r['actual_profit_usd'] for r in self.execution_history)
        winning_trades = sum(1 for r in self.execution_history if r['actual_profit_usd'] > 0)
        avg_execution_time = sum(r['execution_time_seconds'] for r in self.execution_history) / total_trades

        return {
            'total_trades': total_trades,
            'total_profit_usd': total_profit,
            'avg_profit_usd': total_profit / total_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'avg_execution_time': avg_execution_time,
            'recent_trades': self.execution_history[-10:],
        }
