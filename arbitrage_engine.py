"""
Arbitrage Engine for Cross-Exchange Trading
智能套利引擎 - 自动发现和执行跨交易所套利机会
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

from exchanges.factory import ExchangeFactory
from helpers.telegram_bot import TelegramBot


logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    """套利机会数据结构"""
    ticker: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    spread: Decimal  # 绝对价差
    spread_percent: Decimal  # 百分比价差
    estimated_profit: Decimal  # 预估净利润
    profit_percent: Decimal  # 利润率
    max_quantity: Decimal  # 最大可交易数量
    timestamp: datetime
    score: float  # 机会评分 (0-100)

    def __str__(self):
        return (f"{self.ticker}: Buy@{self.buy_exchange} ${self.buy_price:.2f} -> "
                f"Sell@{self.sell_exchange} ${self.sell_price:.2f} | "
                f"Spread: ${self.spread:.2f} ({self.spread_percent:.2f}%) | "
                f"Est.Profit: ${self.estimated_profit:.2f} ({self.profit_percent:.2f}%) | "
                f"Score: {self.score:.1f}")


class ArbitrageEngine:
    """
    套利引擎 - 核心功能：
    1. 实时监控多交易所价格
    2. 计算真实净利润（考虑手续费、滑点）
    3. 机会评分和排序
    4. 自动执行套利交易
    """

    def __init__(self, config: Dict):
        """
        初始化套利引擎

        Args:
            config: 配置字典
                - exchanges: 要监控的交易所列表
                - tickers: 要监控的币种列表
                - min_profit_percent: 最小利润率阈值
                - check_interval: 检查间隔（秒）
                - auto_execute: 是否自动执行
                - max_position_size: 最大仓位（USDT）
                - slippage_percent: 滑点估算（百分比）
        """
        self.config = config
        self.exchanges = {}
        self.price_cache: Dict[str, Dict[str, Decimal]] = {}  # {exchange: {ticker: price}}
        self.fee_rates: Dict[str, Dict[str, Decimal]] = {}  # {exchange: {maker: %, taker: %}}

        # 配置参数
        self.min_profit_percent = Decimal(str(config.get('min_profit_percent', 0.5)))
        self.check_interval = config.get('check_interval', 5)
        self.auto_execute = config.get('auto_execute', False)
        self.max_position_size = Decimal(str(config.get('max_position_size', 1000)))
        self.slippage_percent = Decimal(str(config.get('slippage_percent', 0.1)))

        # 统计
        self.opportunities_found = 0
        self.trades_executed = 0
        self.total_profit = Decimal('0')

        # 通知
        self.telegram_bot = None
        self._setup_telegram()

    def _setup_telegram(self):
        """设置 Telegram 通知"""
        import os
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if token and chat_id:
            self.telegram_bot = TelegramBot(token, chat_id)

    async def initialize(self):
        """初始化所有交易所连接"""
        from trading_bot import TradingConfig

        for exchange_name in self.config['exchanges']:
            try:
                # 创建最小配置
                minimal_config = TradingConfig(
                    ticker="BTC",
                    contract_id="",
                    quantity=Decimal("0.1"),
                    take_profit=Decimal("0.02"),
                    tick_size=Decimal("0.01"),
                    direction="buy",
                    max_orders=1,
                    wait_time=1,
                    exchange=exchange_name.lower(),
                    grid_step=Decimal("-100"),
                    stop_price=Decimal("-1"),
                    pause_price=Decimal("-1"),
                    boost_mode=False
                )

                client = ExchangeFactory.create_exchange(exchange_name.lower(), minimal_config)
                await client.connect()

                self.exchanges[exchange_name.lower()] = client

                # 获取手续费率（这里用估算值，实际应该从交易所API获取）
                self.fee_rates[exchange_name.lower()] = {
                    'maker': self._get_estimated_maker_fee(exchange_name),
                    'taker': self._get_estimated_taker_fee(exchange_name)
                }

                logger.info(f"Connected to {exchange_name}")

            except Exception as e:
                logger.error(f"Failed to initialize {exchange_name}: {e}")

    def _get_estimated_maker_fee(self, exchange: str) -> Decimal:
        """获取 Maker 手续费率估算"""
        fee_map = {
            'edgex': Decimal('0.0002'),    # 0.02%
            'backpack': Decimal('0.0002'),  # 0.02%
            'lighter': Decimal('0.0000'),   # 0% maker
            'aster': Decimal('0.0002'),
            'grvt': Decimal('0.0002'),
            'extended': Decimal('0.0002'),
            'apex': Decimal('0.0002'),
            'paradex': Decimal('0.0002'),
        }
        return fee_map.get(exchange.lower(), Decimal('0.0005'))

    def _get_estimated_taker_fee(self, exchange: str) -> Decimal:
        """获取 Taker 手续费率估算"""
        fee_map = {
            'edgex': Decimal('0.0005'),    # 0.05%
            'backpack': Decimal('0.0005'),
            'lighter': Decimal('0.0003'),   # 0.03%
            'aster': Decimal('0.0005'),
            'grvt': Decimal('0.0005'),
            'extended': Decimal('0.0005'),
            'apex': Decimal('0.0005'),
            'paradex': Decimal('0.0005'),
        }
        return fee_map.get(exchange.lower(), Decimal('0.001'))

    async def fetch_all_prices(self):
        """获取所有交易所的价格"""
        tasks = []
        for exchange_name, client in self.exchanges.items():
            for ticker in self.config['tickers']:
                tasks.append(self._fetch_price(exchange_name, ticker, client))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_price(self, exchange: str, ticker: str, client):
        """获取单个价格"""
        try:
            price = await client.get_current_price(ticker)
            if price:
                if exchange not in self.price_cache:
                    self.price_cache[exchange] = {}
                self.price_cache[exchange][ticker] = Decimal(str(price))
        except Exception as e:
            logger.debug(f"Error fetching {ticker} from {exchange}: {e}")

    def find_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        发现套利机会

        算法：
        1. 遍历所有交易所对
        2. 计算价差
        3. 扣除手续费和滑点
        4. 计算净利润
        5. 评分排序
        """
        opportunities = []

        for ticker in self.config['tickers']:
            # 收集该币种在所有交易所的价格
            prices = {}
            for exchange in self.exchanges.keys():
                if exchange in self.price_cache and ticker in self.price_cache[exchange]:
                    prices[exchange] = self.price_cache[exchange][ticker]

            # 需要至少2个交易所有价格
            if len(prices) < 2:
                continue

            # 找出最低价和最高价
            sorted_prices = sorted(prices.items(), key=lambda x: x[1])

            # 遍历所有可能的交易对
            for i in range(len(sorted_prices)):
                for j in range(i + 1, len(sorted_prices)):
                    buy_exchange, buy_price = sorted_prices[i]
                    sell_exchange, sell_price = sorted_prices[j]

                    # 计算套利机会
                    opp = self._calculate_arbitrage(
                        ticker, buy_exchange, sell_exchange,
                        buy_price, sell_price
                    )

                    if opp and opp.profit_percent >= self.min_profit_percent:
                        opportunities.append(opp)

        # 按评分排序
        opportunities.sort(key=lambda x: x.score, reverse=True)

        return opportunities

    def _calculate_arbitrage(
        self,
        ticker: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: Decimal,
        sell_price: Decimal
    ) -> Optional[ArbitrageOpportunity]:
        """
        计算套利机会的真实利润

        考虑因素：
        1. 买入手续费（Taker）
        2. 卖出手续费（Maker/Taker）
        3. 滑点
        4. 最小价差要求
        """
        # 基础价差
        spread = sell_price - buy_price
        if spread <= 0:
            return None

        spread_percent = (spread / buy_price) * 100

        # 假设买入用 Taker，卖出用 Maker（理想情况）
        buy_fee_rate = self.fee_rates[buy_exchange]['taker']
        sell_fee_rate = self.fee_rates[sell_exchange]['maker']

        # 计算真实成本和收益（假设交易 1 个币）
        quantity = Decimal('1')

        # 买入成本 = 买入价 + 买入手续费 + 滑点
        buy_cost = buy_price * (1 + buy_fee_rate + self.slippage_percent / 100)

        # 卖出收益 = 卖出价 - 卖出手续费 - 滑点
        sell_revenue = sell_price * (1 - sell_fee_rate - self.slippage_percent / 100)

        # 净利润（每个币）
        profit_per_unit = sell_revenue - buy_cost

        if profit_per_unit <= 0:
            return None

        # 利润率
        profit_percent = (profit_per_unit / buy_cost) * 100

        # 计算最大可交易数量（基于最大仓位）
        max_quantity = self.max_position_size / buy_cost

        # 总预估利润
        estimated_profit = profit_per_unit * min(quantity, max_quantity)

        # 机会评分（0-100）
        score = self._calculate_score(
            spread_percent, profit_percent, estimated_profit, buy_exchange, sell_exchange
        )

        return ArbitrageOpportunity(
            ticker=ticker,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread=spread,
            spread_percent=spread_percent,
            estimated_profit=estimated_profit,
            profit_percent=profit_percent,
            max_quantity=max_quantity,
            timestamp=datetime.now(),
            score=score
        )

    def _calculate_score(
        self,
        spread_percent: Decimal,
        profit_percent: Decimal,
        estimated_profit: Decimal,
        buy_exchange: str,
        sell_exchange: str
    ) -> float:
        """
        计算套利机会评分

        评分因素：
        1. 利润率（权重 40%）
        2. 绝对利润（权重 30%）
        3. 价差大小（权重 20%）
        4. 交易所可靠性（权重 10%）
        """
        # 利润率评分（0-40分）
        profit_score = min(float(profit_percent) * 10, 40)

        # 绝对利润评分（0-30分）
        profit_amount_score = min(float(estimated_profit) * 3, 30)

        # 价差评分（0-20分）
        spread_score = min(float(spread_percent) * 5, 20)

        # 交易所可靠性评分（0-10分）
        reliability_score = self._get_exchange_reliability_score(buy_exchange, sell_exchange)

        total_score = profit_score + profit_amount_score + spread_score + reliability_score

        return min(total_score, 100)

    def _get_exchange_reliability_score(self, buy_exchange: str, sell_exchange: str) -> float:
        """交易所可靠性评分"""
        # 基于交易所的流动性、稳定性等因素
        reliability_map = {
            'edgex': 9,
            'backpack': 9,
            'lighter': 8,
            'aster': 7,
            'grvt': 7,
            'extended': 7,
            'apex': 7,
            'paradex': 7,
        }
        buy_score = reliability_map.get(buy_exchange, 5)
        sell_score = reliability_map.get(sell_exchange, 5)
        return (buy_score + sell_score) / 2

    async def execute_arbitrage(self, opportunity: ArbitrageOpportunity, quantity: Decimal):
        """
        执行套利交易

        步骤：
        1. 同时在两个交易所下单
        2. 买方：市价买入
        3. 卖方：限价卖出（或市价）
        4. 监控成交
        5. 记录结果
        """
        logger.info(f"Executing arbitrage: {opportunity}")

        try:
            # 获取交易所客户端
            buy_client = self.exchanges[opportunity.buy_exchange]
            sell_client = self.exchanges[opportunity.sell_exchange]

            # 同时下单（使用 gather 并发执行）
            buy_task = buy_client.place_market_order(
                opportunity.ticker, quantity, 'buy'
            )
            sell_task = sell_client.place_market_order(
                opportunity.ticker, quantity, 'sell'
            )

            buy_result, sell_result = await asyncio.gather(buy_task, sell_task)

            # 检查执行结果
            if buy_result.success and sell_result.success:
                actual_profit = self._calculate_actual_profit(
                    buy_result, sell_result, quantity
                )

                self.trades_executed += 1
                self.total_profit += actual_profit

                # 发送通知
                await self._notify_success(opportunity, actual_profit)

                logger.info(f"Arbitrage executed successfully! Profit: ${actual_profit:.2f}")
                return True
            else:
                logger.error(f"Arbitrage execution failed: Buy={buy_result.success}, Sell={sell_result.success}")
                await self._notify_failure(opportunity, buy_result, sell_result)
                return False

        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}")
            return False

    def _calculate_actual_profit(self, buy_result, sell_result, quantity: Decimal) -> Decimal:
        """计算实际利润"""
        buy_cost = buy_result.price * quantity
        sell_revenue = sell_result.price * quantity
        return sell_revenue - buy_cost

    async def _notify_success(self, opportunity: ArbitrageOpportunity, actual_profit: Decimal):
        """发送成功通知"""
        message = f"""
✅ 套利成功！

币种: {opportunity.ticker}
买入: {opportunity.buy_exchange} @ ${opportunity.buy_price:.2f}
卖出: {opportunity.sell_exchange} @ ${opportunity.sell_price:.2f}
预估利润: ${opportunity.estimated_profit:.2f}
实际利润: ${actual_profit:.2f}
利润率: {opportunity.profit_percent:.2f}%

总执行次数: {self.trades_executed}
累计利润: ${self.total_profit:.2f}
        """.strip()

        if self.telegram_bot:
            self.telegram_bot.send_text(message)
        print(message)

    async def _notify_failure(self, opportunity: ArbitrageOpportunity, buy_result, sell_result):
        """发送失败通知"""
        message = f"""
❌ 套利执行失败

币种: {opportunity.ticker}
买入状态: {'成功' if buy_result.success else '失败'}
卖出状态: {'成功' if sell_result.success else '失败'}
        """.strip()

        if self.telegram_bot:
            self.telegram_bot.send_text(message)
        logger.warning(message)

    async def start_monitoring(self):
        """开始监控套利机会"""
        logger.info("Starting arbitrage monitoring...")

        await self.initialize()

        print("\n" + "=" * 80)
        print("🤖 套利引擎已启动")
        print("=" * 80)
        print(f"监控交易所: {', '.join(self.exchanges.keys())}")
        print(f"监控币种: {', '.join(self.config['tickers'])}")
        print(f"最小利润率: {self.min_profit_percent}%")
        print(f"自动执行: {'是' if self.auto_execute else '否'}")
        print(f"最大仓位: ${self.max_position_size}")
        print("=" * 80 + "\n")

        while True:
            try:
                # 获取所有价格
                await self.fetch_all_prices()

                # 发现套利机会
                opportunities = self.find_arbitrage_opportunities()

                if opportunities:
                    self.opportunities_found += len(opportunities)

                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 发现 {len(opportunities)} 个套利机会：")
                    print("-" * 80)

                    for i, opp in enumerate(opportunities[:5], 1):  # 只显示前5个
                        print(f"{i}. {opp}")

                        # 自动执行最佳机会
                        if self.auto_execute and i == 1 and opp.score >= 70:
                            quantity = min(opp.max_quantity, Decimal('0.1'))  # 限制单次交易量
                            await self.execute_arbitrage(opp, quantity)

                    print("-" * 80)

                # 等待下次检查
                await asyncio.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Stopping arbitrage monitoring...")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)

        # 清理
        await self.cleanup()

    async def cleanup(self):
        """清理资源"""
        for exchange_name, client in self.exchanges.items():
            try:
                await client.disconnect()
            except:
                pass

        # 打印统计
        print("\n" + "=" * 80)
        print("📊 套利引擎统计")
        print("=" * 80)
        print(f"发现机会数: {self.opportunities_found}")
        print(f"执行交易数: {self.trades_executed}")
        print(f"累计利润: ${self.total_profit:.2f}")
        print("=" * 80 + "\n")


# 使用示例
async def main():
    """示例用法"""
    config = {
        'exchanges': ['edgex', 'backpack', 'lighter'],  # 监控的交易所
        'tickers': ['BTC', 'ETH', 'SOL'],  # 监控的币种
        'min_profit_percent': 0.3,  # 最小利润率 0.3%
        'check_interval': 3,  # 3秒检查一次
        'auto_execute': False,  # 是否自动执行（谨慎！）
        'max_position_size': 1000,  # 最大仓位 $1000
        'slippage_percent': 0.1,  # 滑点估算 0.1%
    }

    engine = ArbitrageEngine(config)
    await engine.start_monitoring()


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()

    asyncio.run(main())
