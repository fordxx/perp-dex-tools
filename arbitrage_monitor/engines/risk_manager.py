"""风险管理模块"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from ..models.arbitrage import ArbitrageOpportunity, ExecutionPlan
from ..models.risk import RiskLimits, PositionRisk, ExposureMetrics

logger = logging.getLogger(__name__)


class RiskManager:
    """风险管理器 - 控制交易风险和敞口"""

    def __init__(self, risk_limits: RiskLimits):
        """
        初始化风险管理器

        Args:
            risk_limits: 风险限制配置
        """
        self.risk_limits = risk_limits
        self.exposure = ExposureMetrics()
        self.active_positions: Dict[str, PositionRisk] = {}
        self.daily_reset_time: Optional[datetime] = None
        self._reset_daily_metrics()

    def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        investment_size: Decimal
    ) -> tuple[bool, Optional[str]]:
        """
        验证套利机会是否符合风险限制

        Args:
            opportunity: 套利机会
            investment_size: 投资规模

        Returns:
            (是否通过, 失败原因)
        """
        # 检查是否在风险限制内
        within_limits, reason = self.risk_limits.is_within_limits(
            position_size=investment_size,
            profit_bps=opportunity.net_spread_bps,
            risk_score=opportunity.risk_score,
            confidence_score=opportunity.confidence_score,
            liquidity_score=opportunity.liquidity.liquidity_score,
        )

        if not within_limits:
            return False, reason

        # 检查当前敞口限制
        can_add, reason = self._check_exposure_limits(
            opportunity.exchange_buy,
            opportunity.exchange_sell,
            opportunity.symbol,
            investment_size,
        )

        if not can_add:
            return False, reason

        return True, None

    def create_execution_plan(
        self,
        opportunity: ArbitrageOpportunity,
        investment_usd: Optional[Decimal] = None,
    ) -> Optional[ExecutionPlan]:
        """
        创建执行计划

        Args:
            opportunity: 套利机会
            investment_usd: 投资金额（如果为None，使用默认规模）

        Returns:
            ExecutionPlan 或 None（如果无法创建）
        """
        # 确定投资规模
        if investment_usd is None:
            investment_usd = min(
                self.risk_limits.max_position_size_usd,
                opportunity.liquidity.max_executable_size,
            )
        else:
            # 不能超过最大可执行规模
            investment_usd = min(investment_usd, opportunity.liquidity.max_executable_size)

        # 验证是否符合风险限制
        is_valid, reason = self.validate_opportunity(opportunity, investment_usd)
        if not is_valid:
            logger.warning(f"套利机会不符合风险限制: {reason}")
            return None

        # 计算交易数量
        buy_quantity = investment_usd / opportunity.buy_price
        sell_quantity = buy_quantity  # 假设1:1对冲

        # 计算预期利润
        expected_profit_usd = opportunity.calculate_profit(investment_usd)
        expected_profit_rate = expected_profit_usd / investment_usd if investment_usd > 0 else Decimal('0')

        # 创建执行计划
        plan = ExecutionPlan(
            opportunity=opportunity,
            investment_usd=investment_usd,
            buy_quantity=buy_quantity,
            sell_quantity=sell_quantity,
            expected_profit_usd=expected_profit_usd,
            expected_profit_rate=expected_profit_rate,
            max_slippage_tolerance=self.risk_limits.max_slippage_bps / Decimal('10000'),
            timeout_seconds=10,
        )

        # 验证执行计划
        is_valid, reason = plan.validate()
        if not is_valid:
            logger.warning(f"执行计划验证失败: {reason}")
            return None

        return plan

    def on_position_opened(
        self,
        plan: ExecutionPlan,
        actual_buy_price: Decimal,
        actual_sell_price: Decimal,
    ):
        """
        记录仓位开启

        Args:
            plan: 执行计划
            actual_buy_price: 实际买入价格
            actual_sell_price: 实际卖出价格
        """
        opportunity = plan.opportunity
        position_id = opportunity.opportunity_id

        # 更新敞口
        self.exposure.add_position(
            opportunity.exchange_buy,
            opportunity.symbol,
            plan.investment_usd
        )
        self.exposure.add_position(
            opportunity.exchange_sell,
            opportunity.symbol,
            plan.investment_usd
        )

        # 创建仓位风险记录
        avg_entry_price = (actual_buy_price + actual_sell_price) / Decimal('2')
        self.active_positions[position_id] = PositionRisk(
            exchange=f"{opportunity.exchange_buy}/{opportunity.exchange_sell}",
            symbol=opportunity.symbol,
            position_size_usd=plan.investment_usd,
            entry_price=avg_entry_price,
            current_price=avg_entry_price,
            unrealized_pnl=Decimal('0'),
            duration_minutes=0,
        )

        logger.info(
            f"仓位已开启: {opportunity.symbol} {opportunity.exchange_buy}→{opportunity.exchange_sell} "
            f"规模=${plan.investment_usd}"
        )

    def on_position_closed(
        self,
        plan: ExecutionPlan,
        actual_profit_usd: Decimal,
    ):
        """
        记录仓位关闭

        Args:
            plan: 执行计划
            actual_profit_usd: 实际利润
        """
        opportunity = plan.opportunity
        position_id = opportunity.opportunity_id

        # 更新敞口
        self.exposure.remove_position(
            opportunity.exchange_buy,
            opportunity.symbol,
            plan.investment_usd
        )
        self.exposure.remove_position(
            opportunity.exchange_sell,
            opportunity.symbol,
            plan.investment_usd
        )

        # 更新每日交易统计
        self.exposure.daily_trades_count += 1
        self.exposure.daily_pnl_usd += actual_profit_usd

        # 移除活跃仓位
        if position_id in self.active_positions:
            del self.active_positions[position_id]

        logger.info(
            f"仓位已关闭: {opportunity.symbol} {opportunity.exchange_buy}→{opportunity.exchange_sell} "
            f"利润=${actual_profit_usd:.2f}"
        )

    def update_position_prices(self, prices: Dict[str, Decimal]):
        """
        更新仓位的当前价格

        Args:
            prices: {symbol: current_price}
        """
        for position_id, position in self.active_positions.items():
            if position.symbol in prices:
                current_price = prices[position.symbol]
                # 简化计算：假设盈亏与价格变化成正比
                price_change_pct = (current_price - position.entry_price) / position.entry_price
                position.current_price = current_price
                position.unrealized_pnl = position.position_size_usd * price_change_pct

    def check_stop_loss(self) -> List[str]:
        """
        检查需要止损的仓位

        Returns:
            需要止损的仓位ID列表
        """
        stop_loss_positions = []
        stop_loss_pct = Decimal('-2')  # -2% 止损

        for position_id, position in self.active_positions.items():
            if position.should_close(stop_loss_pct):
                stop_loss_positions.append(position_id)
                logger.warning(
                    f"仓位需要止损: {position.symbol} {position.exchange} "
                    f"盈亏={position.pnl_percentage:.2f}%"
                )

        return stop_loss_positions

    def get_risk_report(self) -> dict:
        """生成风险报告"""
        # 检查是否需要重置每日指标
        self._check_daily_reset()

        # 检查是否超过限制
        within_limits, limit_reason = self.exposure.check_limits(self.risk_limits)

        # 计算风险水平
        exposure_utilization = (
            self.exposure.total_exposure_usd / self.risk_limits.max_total_exposure_usd * 100
            if self.risk_limits.max_total_exposure_usd > 0
            else Decimal('0')
        )

        # 评估整体风险等级
        if exposure_utilization < 30:
            risk_level = "低"
        elif exposure_utilization < 60:
            risk_level = "中"
        elif exposure_utilization < 80:
            risk_level = "高"
        else:
            risk_level = "极高"

        return {
            'risk_level': risk_level,
            'within_limits': within_limits,
            'limit_reason': limit_reason,
            'exposure_utilization_pct': float(exposure_utilization),
            'total_exposure_usd': float(self.exposure.total_exposure_usd),
            'max_exposure_usd': float(self.risk_limits.max_total_exposure_usd),
            'active_positions': self.exposure.active_positions,
            'max_concurrent_trades': self.risk_limits.max_concurrent_trades,
            'daily_trades': self.exposure.daily_trades_count,
            'max_daily_trades': self.risk_limits.max_daily_trades,
            'daily_pnl_usd': float(self.exposure.daily_pnl_usd),
            'max_daily_loss_usd': float(self.risk_limits.max_daily_loss_usd),
            'exchange_exposure': {k: float(v) for k, v in self.exposure.exchange_exposure.items()},
            'symbol_exposure': {k: float(v) for k, v in self.exposure.symbol_exposure.items()},
        }

    def _check_exposure_limits(
        self,
        buy_exchange: str,
        sell_exchange: str,
        symbol: str,
        investment_size: Decimal,
    ) -> tuple[bool, Optional[str]]:
        """检查敞口限制"""
        # 模拟添加后的敞口
        new_total = self.exposure.total_exposure_usd + (investment_size * 2)  # 买+卖
        new_buy_exchange = self.exposure.exchange_exposure.get(buy_exchange, Decimal('0')) + investment_size
        new_sell_exchange = self.exposure.exchange_exposure.get(sell_exchange, Decimal('0')) + investment_size
        new_symbol = self.exposure.symbol_exposure.get(symbol, Decimal('0')) + (investment_size * 2)

        # 检查总敞口
        if new_total > self.risk_limits.max_total_exposure_usd:
            return False, f"总敞口将超限: {new_total} > {self.risk_limits.max_total_exposure_usd}"

        # 检查交易所敞口
        if new_buy_exchange > self.risk_limits.max_exchange_exposure_usd:
            return False, f"{buy_exchange}敞口将超限: {new_buy_exchange} > {self.risk_limits.max_exchange_exposure_usd}"

        if new_sell_exchange > self.risk_limits.max_exchange_exposure_usd:
            return False, f"{sell_exchange}敞口将超限: {new_sell_exchange} > {self.risk_limits.max_exchange_exposure_usd}"

        # 检查币种敞口
        if new_symbol > self.risk_limits.max_symbol_exposure_usd:
            return False, f"{symbol}敞口将超限: {new_symbol} > {self.risk_limits.max_symbol_exposure_usd}"

        # 检查并发交易数
        if self.exposure.active_positions >= self.risk_limits.max_concurrent_trades:
            return False, f"并发交易数已达上限: {self.exposure.active_positions}"

        # 检查每日交易次数
        if self.exposure.daily_trades_count >= self.risk_limits.max_daily_trades:
            return False, f"今日交易次数已达上限: {self.exposure.daily_trades_count}"

        # 检查每日亏损
        if self.exposure.daily_pnl_usd <= -self.risk_limits.max_daily_loss_usd:
            return False, f"今日亏损已达上限: {self.exposure.daily_pnl_usd}"

        return True, None

    def _reset_daily_metrics(self):
        """重置每日指标"""
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.exposure.daily_trades_count = 0
        self.exposure.daily_pnl_usd = Decimal('0')
        logger.info("每日风险指标已重置")

    def _check_daily_reset(self):
        """检查是否需要重置每日指标"""
        if datetime.now() >= self.daily_reset_time:
            self._reset_daily_metrics()
