"""
高级套利监控系统

一个企业级的加密货币套利监控和自动交易系统。

核心功能:
- 实时跨交易所套利机会监控
- 完整的成本分析（手续费+滑点+转账费）
- 市场深度和流动性分析
- 智能风险管理和敞口控制
- 自动/手动交易执行
- 多维度风险评分
"""

__version__ = "2.0.0"
__author__ = "Arbitrage Monitor Team"

from .models import (
    MarketTicker,
    OrderBook,
    FundingRate,
    ExchangeConfig,
    ArbitrageOpportunity,
    ArbitrageType,
    TradingCost,
    LiquidityMetrics,
    ExecutionPlan,
    RiskLimits,
    PositionRisk,
    ExposureMetrics,
)

from .engines import (
    DepthAnalyzer,
    OpportunityCalculator,
    RiskManager,
)

from .services import ArbitrageMonitorService

__all__ = [
    # Models
    "MarketTicker",
    "OrderBook",
    "FundingRate",
    "ExchangeConfig",
    "ArbitrageOpportunity",
    "ArbitrageType",
    "TradingCost",
    "LiquidityMetrics",
    "ExecutionPlan",
    "RiskLimits",
    "PositionRisk",
    "ExposureMetrics",
    # Engines
    "DepthAnalyzer",
    "OpportunityCalculator",
    "RiskManager",
    # Services
    "ArbitrageMonitorService",
]
