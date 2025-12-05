"""套利机会数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ArbitrageType(Enum):
    """套利类型"""
    SPOT_SPOT = "spot_spot"  # 现货-现货套利
    PERP_PERP = "perp_perp"  # 永续-永续套利
    FUNDING_RATE = "funding_rate"  # 资金费率套利
    TRIANGULAR = "triangular"  # 三角套利
    CROSS_EXCHANGE = "cross_exchange"  # 跨交易所套利


@dataclass
class TradingCost:
    """交易成本分析"""
    exchange_buy: str
    exchange_sell: str
    buy_fee: Decimal  # 买入手续费
    sell_fee: Decimal  # 卖出手续费
    withdrawal_fee: Decimal  # 提现费用
    slippage_buy: Decimal  # 买入滑点
    slippage_sell: Decimal  # 卖出滑点
    transfer_time_minutes: int = 5  # 转账时间（分钟）

    @property
    def total_fee_rate(self) -> Decimal:
        """总手续费率"""
        return self.buy_fee + self.sell_fee + self.withdrawal_fee

    @property
    def total_slippage_rate(self) -> Decimal:
        """总滑点率"""
        return self.slippage_buy + self.slippage_sell

    @property
    def total_cost_rate(self) -> Decimal:
        """总成本率（手续费+滑点）"""
        return self.total_fee_rate + self.total_slippage_rate


@dataclass
class LiquidityMetrics:
    """流动性指标"""
    buy_depth_usd: Decimal  # 买入方向市场深度
    sell_depth_usd: Decimal  # 卖出方向市场深度
    buy_avg_price: Decimal  # 买入平均价格
    sell_avg_price: Decimal  # 卖出平均价格
    liquidity_score: Decimal  # 流动性评分 (0-100)
    max_executable_size: Decimal  # 最大可执行规模

    def is_sufficient(self, min_size_usd: Decimal = Decimal('1000')) -> bool:
        """检查流动性是否充足"""
        return (self.buy_depth_usd >= min_size_usd and
                self.sell_depth_usd >= min_size_usd and
                self.liquidity_score >= Decimal('50'))


@dataclass
class ArbitrageOpportunity:
    """套利机会"""
    opportunity_id: str
    arbitrage_type: ArbitrageType
    symbol: str
    exchange_buy: str
    exchange_sell: str
    buy_price: Decimal
    sell_price: Decimal

    # 成本分析
    trading_cost: TradingCost

    # 流动性分析
    liquidity: LiquidityMetrics

    # 盈利分析
    gross_spread: Decimal  # 毛价差
    net_spread: Decimal  # 净价差（扣除成本）
    gross_spread_bps: Decimal  # 毛价差基点
    net_spread_bps: Decimal  # 净价差基点

    # 资金费率（如适用）
    funding_rate_diff: Optional[Decimal] = None
    funding_rate_annual: Optional[Decimal] = None

    # 风险评估
    risk_score: Decimal = Decimal('0')  # 风险评分 (0-100)
    confidence_score: Decimal = Decimal('0')  # 置信度评分 (0-100)

    # 元数据
    timestamp: datetime = field(default_factory=datetime.now)
    data_latency_ms: int = 0  # 数据延迟毫秒数

    @property
    def profit_potential_bps(self) -> Decimal:
        """潜在利润（基点）"""
        profit = self.net_spread_bps
        if self.funding_rate_annual:
            # 如果有资金费率差，按年化计算额外收益（假设持仓1天）
            profit += (self.funding_rate_annual / Decimal('365'))
        return profit

    @property
    def is_profitable(self) -> bool:
        """是否有利可图（净收益为正）"""
        return self.net_spread > 0

    @property
    def is_executable(self) -> bool:
        """是否可执行"""
        if not self.is_profitable:
            return False
        if not self.liquidity.is_sufficient():
            return False
        if self.data_latency_ms > 1000:  # 数据延迟超过1秒
            return False
        if self.confidence_score < Decimal('60'):
            return False
        return True

    @property
    def priority_score(self) -> Decimal:
        """优先级评分（用于排序）"""
        # 综合考虑利润、流动性、风险和置信度
        profit_weight = self.net_spread_bps * Decimal('0.4')
        liquidity_weight = self.liquidity.liquidity_score * Decimal('0.2')
        confidence_weight = self.confidence_score * Decimal('0.3')
        risk_weight = (Decimal('100') - self.risk_score) * Decimal('0.1')

        return profit_weight + liquidity_weight + confidence_weight + risk_weight

    def calculate_profit(self, investment_usd: Decimal) -> Decimal:
        """计算指定投资额的预期利润"""
        if investment_usd > self.liquidity.max_executable_size:
            investment_usd = self.liquidity.max_executable_size

        profit_rate = self.net_spread / self.buy_price
        return investment_usd * profit_rate

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.opportunity_id,
            'type': self.arbitrage_type.value,
            'symbol': self.symbol,
            'buy_exchange': self.exchange_buy,
            'sell_exchange': self.exchange_sell,
            'buy_price': float(self.buy_price),
            'sell_price': float(self.sell_price),
            'gross_spread_bps': float(self.gross_spread_bps),
            'net_spread_bps': float(self.net_spread_bps),
            'profit_potential_bps': float(self.profit_potential_bps),
            'liquidity_score': float(self.liquidity.liquidity_score),
            'risk_score': float(self.risk_score),
            'confidence_score': float(self.confidence_score),
            'priority_score': float(self.priority_score),
            'is_executable': self.is_executable,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    opportunity: ArbitrageOpportunity
    investment_usd: Decimal
    buy_quantity: Decimal
    sell_quantity: Decimal
    expected_profit_usd: Decimal
    expected_profit_rate: Decimal
    max_slippage_tolerance: Decimal = Decimal('0.001')  # 0.1%
    timeout_seconds: int = 10

    status: str = "pending"  # pending, executing, completed, failed
    actual_profit_usd: Optional[Decimal] = None
    execution_time: Optional[datetime] = None
    failure_reason: Optional[str] = None

    def validate(self) -> tuple[bool, Optional[str]]:
        """验证执行计划"""
        if self.investment_usd <= 0:
            return False, "投资金额必须大于0"

        if self.investment_usd > self.opportunity.liquidity.max_executable_size:
            return False, f"投资金额超过最大可执行规模 {self.opportunity.liquidity.max_executable_size}"

        if not self.opportunity.is_executable:
            return False, "套利机会不可执行"

        if self.buy_quantity <= 0 or self.sell_quantity <= 0:
            return False, "交易数量必须大于0"

        return True, None
