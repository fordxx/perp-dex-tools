"""套利监控服务主程序"""
import asyncio
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
from ..models.arbitrage import ArbitrageOpportunity, ExecutionPlan
from ..models.risk import RiskLimits
from ..engines.depth_analyzer import DepthAnalyzer
from ..engines.opportunity_calculator import OpportunityCalculator
from ..engines.risk_manager import RiskManager
from ..engines.execution_engine import ExecutionEngine

logger = logging.getLogger(__name__)


class ArbitrageMonitorService:
    """套利监控服务 - 整合所有组件的主服务"""

    def __init__(
        self,
        exchange_configs: Dict[str, ExchangeConfig],
        risk_limits: RiskLimits,
        exchange_adapters: Optional[dict] = None,
        auto_execute: bool = False,
        scan_interval: int = 2,
    ):
        """
        初始化监控服务

        Args:
            exchange_configs: 交易所配置
            risk_limits: 风险限制
            exchange_adapters: 交易所适配器（用于自动交易）
            auto_execute: 是否自动执行交易
            scan_interval: 扫描间隔（秒）
        """
        self.exchange_configs = exchange_configs
        self.risk_limits = risk_limits
        self.scan_interval = scan_interval

        # 初始化各个引擎
        self.depth_analyzer = DepthAnalyzer()
        self.opportunity_calculator = OpportunityCalculator(
            exchange_configs=exchange_configs,
            min_profit_bps=risk_limits.min_profit_bps,
        )
        self.risk_manager = RiskManager(risk_limits=risk_limits)
        self.execution_engine = ExecutionEngine(
            exchange_adapters=exchange_adapters or {},
            auto_execute=auto_execute,
        )

        # 数据缓存
        self.latest_tickers: Dict[str, Dict[str, MarketTicker]] = {}
        self.latest_orderbooks: Dict[str, Dict[str, OrderBook]] = {}
        self.latest_funding_rates: Dict[str, Dict[str, FundingRate]] = {}

        # 套利机会缓存
        self.current_opportunities: List[ArbitrageOpportunity] = []
        self.best_opportunities: List[ArbitrageOpportunity] = []

        # 统计数据
        self.stats = {
            'total_scans': 0,
            'total_opportunities_found': 0,
            'total_executable_opportunities': 0,
            'last_scan_time': None,
            'uptime_seconds': 0,
        }
        self.start_time = datetime.now()

        # 运行状态
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动监控服务"""
        if self.is_running:
            logger.warning("监控服务已在运行中")
            return

        self.is_running = True
        logger.info("套利监控服务启动")
        logger.info(f"扫描间隔: {self.scan_interval}秒")
        logger.info(f"自动执行: {'是' if self.execution_engine.auto_execute else '否（模拟模式）'}")
        logger.info(f"风险限制: 最大仓位=${self.risk_limits.max_position_size_usd}, "
                   f"最小利润={self.risk_limits.min_profit_bps}bps")

        # 启动监控循环
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """停止监控服务"""
        if not self.is_running:
            return

        logger.info("正在停止监控服务...")
        self.is_running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("监控服务已停止")

    async def _monitor_loop(self):
        """主监控循环"""
        try:
            while self.is_running:
                scan_start = datetime.now()

                # 执行一次扫描
                await self._scan_opportunities()

                # 更新统计数据
                self.stats['total_scans'] += 1
                self.stats['last_scan_time'] = datetime.now()
                self.stats['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()

                # 计算扫描耗时
                scan_duration = (datetime.now() - scan_start).total_seconds()
                logger.debug(f"扫描耗时: {scan_duration:.3f}秒")

                # 等待下一次扫描
                await asyncio.sleep(max(0, self.scan_interval - scan_duration))

        except asyncio.CancelledError:
            logger.info("监控循环被取消")
        except Exception as e:
            logger.error(f"监控循环异常: {e}", exc_info=True)
            self.is_running = False

    async def _scan_opportunities(self):
        """扫描套利机会"""
        try:
            # 查找套利机会
            opportunities = self.opportunity_calculator.find_cross_exchange_opportunities(
                tickers=self.latest_tickers,
                orderbooks=self.latest_orderbooks,
                funding_rates=self.latest_funding_rates if self.latest_funding_rates else None,
            )

            self.current_opportunities = opportunities
            self.stats['total_opportunities_found'] += len(opportunities)

            # 筛选可执行的机会
            executable_opportunities = [
                opp for opp in opportunities
                if opp.is_executable
            ]

            self.stats['total_executable_opportunities'] += len(executable_opportunities)

            if executable_opportunities:
                logger.info(f"发现 {len(executable_opportunities)} 个可执行套利机会")

                # 保存最佳机会（按优先级排序）
                self.best_opportunities = executable_opportunities[:10]

                # 如果启用自动执行，执行最佳机会
                if self.execution_engine.auto_execute and executable_opportunities:
                    await self._auto_execute_best_opportunity(executable_opportunities[0])

        except Exception as e:
            logger.error(f"扫描套利机会失败: {e}", exc_info=True)

    async def _auto_execute_best_opportunity(self, opportunity: ArbitrageOpportunity):
        """自动执行最佳套利机会"""
        try:
            # 创建执行计划
            plan = self.risk_manager.create_execution_plan(opportunity)

            if not plan:
                logger.debug("无法创建执行计划（可能超过风险限制）")
                return

            logger.info(
                f"准备执行套利: {opportunity.symbol} "
                f"{opportunity.exchange_buy}→{opportunity.exchange_sell} "
                f"预期利润=${plan.expected_profit_usd:.2f}"
            )

            # 执行交易
            success, error, actual_profit = await self.execution_engine.execute_arbitrage(plan)

            if success:
                # 更新风险管理器
                if actual_profit is not None:
                    self.risk_manager.on_position_opened(
                        plan,
                        opportunity.buy_price,
                        opportunity.sell_price,
                    )
                    # 假设立即平仓（实际场景可能需要延迟）
                    self.risk_manager.on_position_closed(plan, actual_profit)

                logger.info(f"套利执行成功，实际利润=${actual_profit:.2f}")
            else:
                logger.error(f"套利执行失败: {error}")

        except Exception as e:
            logger.error(f"自动执行失败: {e}", exc_info=True)

    def update_market_data(
        self,
        exchange: str,
        tickers: Dict[str, MarketTicker],
        orderbooks: Dict[str, OrderBook],
        funding_rates: Optional[Dict[str, FundingRate]] = None,
    ):
        """
        更新市场数据

        Args:
            exchange: 交易所名称
            tickers: 行情数据字典 {symbol: ticker}
            orderbooks: 订单簿字典 {symbol: orderbook}
            funding_rates: 资金费率字典 {symbol: funding_rate}
        """
        self.latest_tickers[exchange] = tickers
        self.latest_orderbooks[exchange] = orderbooks

        if funding_rates:
            self.latest_funding_rates[exchange] = funding_rates

    def get_current_opportunities(self, top_n: int = 10) -> List[dict]:
        """
        获取当前套利机会

        Args:
            top_n: 返回前N个机会

        Returns:
            套利机会列表（字典格式）
        """
        opportunities = sorted(
            self.current_opportunities,
            key=lambda x: x.priority_score,
            reverse=True
        )[:top_n]

        return [opp.to_dict() for opp in opportunities]

    def get_executable_opportunities(self) -> List[dict]:
        """获取可执行的套利机会"""
        opportunities = [
            opp for opp in self.current_opportunities
            if opp.is_executable
        ]

        opportunities.sort(key=lambda x: x.priority_score, reverse=True)
        return [opp.to_dict() for opp in opportunities]

    def get_risk_report(self) -> dict:
        """获取风险报告"""
        return self.risk_manager.get_risk_report()

    def get_execution_stats(self) -> dict:
        """获取执行统计"""
        return self.execution_engine.get_execution_stats()

    def get_service_stats(self) -> dict:
        """获取服务统计"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            'is_running': self.is_running,
            'uptime_seconds': uptime,
            'uptime_formatted': self._format_uptime(uptime),
            'total_scans': self.stats['total_scans'],
            'total_opportunities_found': self.stats['total_opportunities_found'],
            'total_executable_opportunities': self.stats['total_executable_opportunities'],
            'last_scan_time': self.stats['last_scan_time'].isoformat() if self.stats['last_scan_time'] else None,
            'scan_interval': self.scan_interval,
            'auto_execute': self.execution_engine.auto_execute,
            'current_opportunities_count': len(self.current_opportunities),
            'executable_opportunities_count': len([o for o in self.current_opportunities if o.is_executable]),
        }

    def _format_uptime(self, seconds: float) -> str:
        """格式化运行时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"

    async def manual_execute(self, opportunity_id: str) -> tuple[bool, Optional[str]]:
        """
        手动执行指定的套利机会

        Args:
            opportunity_id: 套利机会ID

        Returns:
            (是否成功, 错误信息)
        """
        # 查找机会
        opportunity = None
        for opp in self.current_opportunities:
            if opp.opportunity_id == opportunity_id:
                opportunity = opp
                break

        if not opportunity:
            return False, "未找到指定的套利机会"

        # 创建执行计划
        plan = self.risk_manager.create_execution_plan(opportunity)
        if not plan:
            return False, "无法创建执行计划（可能超过风险限制）"

        # 执行
        success, error, actual_profit = await self.execution_engine.execute_arbitrage(plan)

        if success and actual_profit is not None:
            self.risk_manager.on_position_opened(plan, opportunity.buy_price, opportunity.sell_price)
            self.risk_manager.on_position_closed(plan, actual_profit)
            return True, None

        return False, error
