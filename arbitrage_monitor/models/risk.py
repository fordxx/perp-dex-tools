"""风险管理数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class RiskLimits:
    """风险限制配置"""
    max_position_size_usd: Decimal = Decimal('10000')  # 单次最大仓位
    max_total_exposure_usd: Decimal = Decimal('50000')  # 总敞口限制
    max_exchange_exposure_usd: Decimal = Decimal('20000')  # 单交易所敞口
    max_symbol_exposure_usd: Decimal = Decimal('15000')  # 单币种敞口

    min_profit_bps: Decimal = Decimal('10')  # 最小利润要求（基点）
    max_risk_score: Decimal = Decimal('70')  # 最大风险评分
    min_confidence_score: Decimal = Decimal('60')  # 最小置信度
    min_liquidity_score: Decimal = Decimal('50')  # 最小流动性评分

    max_slippage_bps: Decimal = Decimal('20')  # 最大可接受滑点
    max_data_latency_ms: int = 1000  # 最大数据延迟（毫秒）

    max_concurrent_trades: int = 3  # 最大并发交易数
    max_daily_trades: int = 50  # 每日最大交易次数
    max_daily_loss_usd: Decimal = Decimal('1000')  # 每日最大亏损

    def is_within_limits(
        self,
        position_size: Decimal,
        profit_bps: Decimal,
        risk_score: Decimal,
        confidence_score: Decimal,
        liquidity_score: Decimal,
    ) -> tuple[bool, Optional[str]]:
        """检查是否在风险限制内"""
        if position_size > self.max_position_size_usd:
            return False, f"仓位大小 {position_size} 超过限制 {self.max_position_size_usd}"

        if profit_bps < self.min_profit_bps:
            return False, f"利润 {profit_bps}bps 低于最小要求 {self.min_profit_bps}bps"

        if risk_score > self.max_risk_score:
            return False, f"风险评分 {risk_score} 超过限制 {self.max_risk_score}"

        if confidence_score < self.min_confidence_score:
            return False, f"置信度 {confidence_score} 低于要求 {self.min_confidence_score}"

        if liquidity_score < self.min_liquidity_score:
            return False, f"流动性评分 {liquidity_score} 低于要求 {self.min_liquidity_score}"

        return True, None


@dataclass
class PositionRisk:
    """仓位风险"""
    exchange: str
    symbol: str
    position_size_usd: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    duration_minutes: int
    risk_level: str = "low"  # low, medium, high, critical

    @property
    def pnl_percentage(self) -> Decimal:
        """盈亏百分比"""
        if self.position_size_usd == 0:
            return Decimal('0')
        return (self.unrealized_pnl / self.position_size_usd) * Decimal('100')

    def should_close(self, stop_loss_pct: Decimal = Decimal('-2')) -> bool:
        """是否应该止损"""
        return self.pnl_percentage <= stop_loss_pct


@dataclass
class ExposureMetrics:
    """敞口指标"""
    total_exposure_usd: Decimal = Decimal('0')
    exchange_exposure: Dict[str, Decimal] = field(default_factory=dict)
    symbol_exposure: Dict[str, Decimal] = field(default_factory=dict)
    active_positions: int = 0
    daily_trades_count: int = 0
    daily_pnl_usd: Decimal = Decimal('0')
    timestamp: datetime = field(default_factory=datetime.now)

    def add_position(self, exchange: str, symbol: str, size_usd: Decimal):
        """添加仓位"""
        self.total_exposure_usd += size_usd
        self.exchange_exposure[exchange] = self.exchange_exposure.get(exchange, Decimal('0')) + size_usd
        self.symbol_exposure[symbol] = self.symbol_exposure.get(symbol, Decimal('0')) + size_usd
        self.active_positions += 1

    def remove_position(self, exchange: str, symbol: str, size_usd: Decimal):
        """移除仓位"""
        self.total_exposure_usd -= size_usd
        self.exchange_exposure[exchange] = self.exchange_exposure.get(exchange, Decimal('0')) - size_usd
        self.symbol_exposure[symbol] = self.symbol_exposure.get(symbol, Decimal('0')) - size_usd
        self.active_positions -= 1

    def check_limits(self, limits: RiskLimits) -> tuple[bool, Optional[str]]:
        """检查是否超过风险限制"""
        if self.total_exposure_usd > limits.max_total_exposure_usd:
            return False, f"总敞口 {self.total_exposure_usd} 超过限制 {limits.max_total_exposure_usd}"

        for exchange, exposure in self.exchange_exposure.items():
            if exposure > limits.max_exchange_exposure_usd:
                return False, f"{exchange} 敞口 {exposure} 超过限制 {limits.max_exchange_exposure_usd}"

        for symbol, exposure in self.symbol_exposure.items():
            if exposure > limits.max_symbol_exposure_usd:
                return False, f"{symbol} 敞口 {exposure} 超过限制 {limits.max_symbol_exposure_usd}"

        if self.active_positions >= limits.max_concurrent_trades:
            return False, f"活跃仓位数 {self.active_positions} 达到限制 {limits.max_concurrent_trades}"

        if self.daily_trades_count >= limits.max_daily_trades:
            return False, f"今日交易次数 {self.daily_trades_count} 达到限制 {limits.max_daily_trades}"

        if self.daily_pnl_usd <= -limits.max_daily_loss_usd:
            return False, f"今日亏损 {self.daily_pnl_usd} 达到限制 {limits.max_daily_loss_usd}"

        return True, None

    def get_exposure_report(self) -> dict:
        """生成敞口报告"""
        return {
            'total_exposure_usd': float(self.total_exposure_usd),
            'exchange_exposure': {k: float(v) for k, v in self.exchange_exposure.items()},
            'symbol_exposure': {k: float(v) for k, v in self.symbol_exposure.items()},
            'active_positions': self.active_positions,
            'daily_trades': self.daily_trades_count,
            'daily_pnl': float(self.daily_pnl_usd),
            'timestamp': self.timestamp.isoformat(),
        }
