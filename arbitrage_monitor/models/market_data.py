"""市场数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class MarketTicker:
    """市场行情数据"""
    exchange: str
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    mid_price: Decimal
    bid_volume: Decimal
    ask_volume: Decimal
    last_price: Decimal
    volume_24h: Decimal
    timestamp: datetime

    @property
    def spread(self) -> Decimal:
        """买卖价差"""
        return self.ask_price - self.bid_price

    @property
    def spread_bps(self) -> Decimal:
        """价差基点 (basis points)"""
        if self.mid_price == 0:
            return Decimal('0')
        return (self.spread / self.mid_price) * Decimal('10000')

    def is_stale(self, max_age_seconds: int = 5) -> bool:
        """检查数据是否过时"""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > max_age_seconds

    def validate(self) -> bool:
        """验证数据有效性"""
        if self.bid_price <= 0 or self.ask_price <= 0:
            return False
        if self.bid_price > self.ask_price:
            return False
        if self.bid_volume < 0 or self.ask_volume < 0:
            return False
        return True


@dataclass
class OrderBookLevel:
    """订单簿价格档位"""
    price: Decimal
    volume: Decimal

    @property
    def notional_value(self) -> Decimal:
        """名义价值"""
        return self.price * self.volume


@dataclass
class OrderBook:
    """完整订单簿"""
    exchange: str
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime

    def get_bid_depth(self, depth_usd: Decimal) -> Decimal:
        """计算指定美元深度的平均买价"""
        accumulated_value = Decimal('0')
        accumulated_volume = Decimal('0')

        for level in self.bids:
            if accumulated_value >= depth_usd:
                break
            value = min(level.notional_value, depth_usd - accumulated_value)
            volume = value / level.price
            accumulated_value += value
            accumulated_volume += volume

        if accumulated_volume == 0:
            return Decimal('0')
        return accumulated_value / accumulated_volume

    def get_ask_depth(self, depth_usd: Decimal) -> Decimal:
        """计算指定美元深度的平均卖价"""
        accumulated_value = Decimal('0')
        accumulated_volume = Decimal('0')

        for level in self.asks:
            if accumulated_value >= depth_usd:
                break
            value = min(level.notional_value, depth_usd - accumulated_value)
            volume = value / level.price
            accumulated_value += value
            accumulated_volume += volume

        if accumulated_volume == 0:
            return Decimal('0')
        return accumulated_value / accumulated_volume

    def get_liquidity_score(self, depth_usd: Decimal = Decimal('10000')) -> Decimal:
        """计算流动性评分 (0-100)"""
        bid_depth = sum(level.notional_value for level in self.bids[:10])
        ask_depth = sum(level.notional_value for level in self.asks[:10])

        total_depth = bid_depth + ask_depth
        score = min(total_depth / (depth_usd * 2) * 100, Decimal('100'))
        return score


@dataclass
class FundingRate:
    """资金费率"""
    exchange: str
    symbol: str
    rate: Decimal  # 8小时费率
    predicted_rate: Optional[Decimal] = None
    next_funding_time: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def annual_rate(self) -> Decimal:
        """年化费率"""
        return self.rate * Decimal('365') * Decimal('3')  # 每天3次


@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str
    maker_fee: Decimal  # 挂单手续费率
    taker_fee: Decimal  # 吃单手续费率
    withdrawal_fee: Decimal  # 提现手续费
    min_order_size: Decimal  # 最小下单量
    max_order_size: Decimal  # 最大下单量
    supports_funding_rate: bool = True
    api_rate_limit: int = 100  # 每秒请求限制

    def calculate_trading_fee(self, notional: Decimal, is_maker: bool = False) -> Decimal:
        """计算交易手续费"""
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        return notional * fee_rate
