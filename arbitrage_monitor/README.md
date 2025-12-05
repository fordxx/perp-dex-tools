# 🚀 高级套利监控系统 (Advanced Arbitrage Monitor)

一个企业级的加密货币套利监控和自动交易系统，支持多交易所实时监控、智能风险管理和自动执行。

## ✨ 核心特性

### 🎯 与原系统对比的改进

| 功能模块 | 原系统 | 新系统 ✨ |
|---------|--------|---------|
| **盈利能力分析** | 仅计算价差 | ✅ 全成本计算（手续费+滑点+转账） |
| **流动性分析** | 无 | ✅ 完整订单簿深度分析 |
| **风险管理** | 无 | ✅ 多维度风险控制系统 |
| **交易执行** | 仅监控 | ✅ 自动/手动交易执行引擎 |
| **套利类型** | 价差+费率差 | ✅ 支持多种套利策略 |
| **数据验证** | 基础验证 | ✅ 多层数据验证和时效性检查 |
| **性能优化** | 实时计算 | ✅ 智能缓存和批量处理 |

### 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│           监控服务 (ArbitrageMonitorService)         │
├──────────────┬──────────────┬──────────────────────┤
│ 市场深度     │  机会计算器   │  执行引擎            │
│ 分析器       │  (智能评分)   │  (自动交易)          │
├──────────────┼──────────────┼──────────────────────┤
│ 深度分析     │  风险管理器   │  性能监控            │
│ 流动性评估   │  (多维控制)   │  (统计分析)          │
└──────────────┴──────────────┴──────────────────────┘
          ↓           ↓              ↓
    [EdgeX] [Lighter] [Backpack] [Apex] [Hyperliquid]
```

## 📦 核心模块

### 1️⃣ 数据模型 (models/)

#### 市场数据模型
- **MarketTicker**: 实时行情数据（带数据验证和时效性检查）
- **OrderBook**: 完整订单簿（支持深度分析）
- **FundingRate**: 资金费率（年化计算）
- **ExchangeConfig**: 交易所配置（手续费、限制等）

#### 套利模型
- **TradingCost**: 全成本分析（手续费+滑点+转账费）
- **LiquidityMetrics**: 流动性指标（深度、评分、可执行规模）
- **ArbitrageOpportunity**: 套利机会（包含风险和置信度评分）
- **ExecutionPlan**: 执行计划（带验证和追踪）

#### 风险模型
- **RiskLimits**: 风险限制配置
- **PositionRisk**: 仓位风险追踪
- **ExposureMetrics**: 敞口指标管理

### 2️⃣ 分析引擎 (engines/)

#### DepthAnalyzer - 市场深度分析器
```python
# 功能:
✅ 订单簿流动性分析
✅ 滑点计算
✅ 市场冲击评估
✅ 可执行规模计算
```

#### OpportunityCalculator - 套利机会计算引擎
```python
# 核心算法:
✅ 跨交易所价差识别
✅ 真实成本计算（手续费+滑点）
✅ 风险评分（0-100）
✅ 置信度评分（0-100）
✅ 优先级智能排序
```

**风险评分算法**:
- 流动性风险 (0-40分)
- 滑点风险 (0-30分)
- 转账时间风险 (0-20分)
- 深度不平衡风险 (0-10分)

**置信度评分算法**:
- 流动性充足度 (0-40分)
- 数据新鲜度 (0-30分)
- 价格稳定性 (0-30分)

#### RiskManager - 风险管理器
```python
# 多维度风险控制:
✅ 仓位限制（单次、总额、交易所、币种）
✅ 利润门槛检查
✅ 并发交易数控制
✅ 每日交易次数和亏损限制
✅ 实时敞口监控
✅ 自动止损
```

#### ExecutionEngine - 交易执行引擎
```python
# 执行能力:
✅ 并行下单（买卖同时执行）
✅ 市价单/限价单支持
✅ 超时保护
✅ 失败回滚
✅ 执行统计追踪
✅ 模拟模式（安全测试）
```

### 3️⃣ 监控服务 (services/)

#### ArbitrageMonitorService - 主控制器
```python
# 核心功能:
✅ 实时套利机会扫描
✅ 自动/手动交易执行
✅ 风险实时监控
✅ 性能统计分析
✅ 状态报告生成
```

## 🚀 快速开始

### 安装依赖

```bash
pip install pyyaml
```

### 配置系统

1. 复制配置文件：
```bash
cp arbitrage_monitor/config_example.yaml arbitrage_monitor/config.yaml
```

2. 编辑配置文件，设置交易所参数和风险限制

### 运行监控

```bash
# 模拟模式（安全测试）
python arbitrage_monitor/run_monitor.py

# 实盘模式（需要配置交易所API）
# 修改 config.yaml 中 monitor.auto_execute: true
```

## 📊 使用示例

### 基础监控

```python
from arbitrage_monitor.services import ArbitrageMonitorService
from arbitrage_monitor.models import ExchangeConfig, RiskLimits
from decimal import Decimal

# 创建交易所配置
exchange_configs = {
    'edgex': ExchangeConfig(
        name='EdgeX',
        maker_fee=Decimal('0.0002'),
        taker_fee=Decimal('0.0005'),
        withdrawal_fee=Decimal('0.0001'),
        min_order_size=Decimal('10'),
        max_order_size=Decimal('100000'),
    ),
    # ... 其他交易所
}

# 创建风险限制
risk_limits = RiskLimits(
    max_position_size_usd=Decimal('10000'),
    min_profit_bps=Decimal('10'),
    max_concurrent_trades=3,
)

# 启动监控服务
service = ArbitrageMonitorService(
    exchange_configs=exchange_configs,
    risk_limits=risk_limits,
    auto_execute=False,  # 模拟模式
    scan_interval=2,
)

await service.start()
```

### 更新市场数据

```python
# 更新某个交易所的市场数据
service.update_market_data(
    exchange='edgex',
    tickers={
        'BTC-PERP': MarketTicker(...),
        'ETH-PERP': MarketTicker(...),
    },
    orderbooks={
        'BTC-PERP': OrderBook(...),
        'ETH-PERP': OrderBook(...),
    },
)
```

### 查看套利机会

```python
# 获取当前可执行机会
opportunities = service.get_executable_opportunities()

for opp in opportunities:
    print(f"机会: {opp['symbol']}")
    print(f"  {opp['buy_exchange']} → {opp['sell_exchange']}")
    print(f"  净利润: {opp['net_spread_bps']:.2f} bps")
    print(f"  优先级: {opp['priority_score']:.1f}")
```

### 手动执行交易

```python
# 手动执行指定机会
success, error = await service.manual_execute(opportunity_id)
if success:
    print("交易执行成功!")
else:
    print(f"执行失败: {error}")
```

### 风险报告

```python
# 获取风险报告
risk_report = service.get_risk_report()
print(f"风险水平: {risk_report['risk_level']}")
print(f"总敞口: ${risk_report['total_exposure_usd']:.2f}")
print(f"活跃仓位: {risk_report['active_positions']}")
```

## 🔧 高级配置

### 风险限制配置

```yaml
risk_limits:
  # 仓位限制
  max_position_size_usd: 10000      # 单次最大 $10k
  max_total_exposure_usd: 50000     # 总敞口 $50k
  max_exchange_exposure_usd: 20000  # 单交易所 $20k
  max_symbol_exposure_usd: 15000    # 单币种 $15k

  # 利润要求
  min_profit_bps: 10               # 最小 10bps (0.1%)
  max_risk_score: 70               # 最大风险评分
  min_confidence_score: 60         # 最小置信度

  # 执行限制
  max_slippage_bps: 20            # 最大 20bps 滑点
  max_concurrent_trades: 3        # 最多3个并发
  max_daily_trades: 50            # 每日最多50笔
  max_daily_loss_usd: 1000        # 每日最大亏损 $1k
```

### 交易所配置

```yaml
exchanges:
  edgex:
    maker_fee: 0.0002    # 挂单 0.02%
    taker_fee: 0.0005    # 吃单 0.05%
    withdrawal_fee: 0.0001
    min_order_size: 10
    max_order_size: 100000
    supports_funding_rate: true
```

## 📈 性能特性

- **并行处理**: 同时扫描多个交易所
- **智能缓存**: 减少重复计算
- **批量操作**: 优化数据处理
- **异步执行**: 高效的IO操作

## 🛡️ 安全特性

### 数据验证
- ✅ 价格合理性检查
- ✅ 数据时效性验证
- ✅ 异常值过滤

### 风险控制
- ✅ 多维度敞口限制
- ✅ 实时止损
- ✅ 每日亏损上限
- ✅ 并发交易控制

### 执行保护
- ✅ 超时保护
- ✅ 失败回滚
- ✅ 滑点保护
- ✅ 模拟模式测试

## 📝 日志和监控

系统提供完整的日志记录：

```
2025-12-05 10:30:15 - INFO - 套利监控系统启动
2025-12-05 10:30:16 - INFO - 发现套利机会: BTC-PERP edgex→lighter 净利润=25.5bps
2025-12-05 10:30:20 - INFO - 套利执行成功，实际利润=$125.50
```

## 🔄 与现有系统集成

本系统可以轻松集成到现有的交易基础设施：

```python
# 实现交易所适配器接口
class MyExchangeAdapter:
    async def create_market_order(self, symbol, side, quantity):
        # 调用实际交易所API
        pass

# 注入到执行引擎
service = ArbitrageMonitorService(
    exchange_adapters={
        'edgex': MyExchangeAdapter(),
        'lighter': MyExchangeAdapter(),
    },
    auto_execute=True,
)
```

## 📊 统计和报告

系统提供丰富的统计信息：

- **服务统计**: 运行时间、扫描次数、发现机会数
- **风险报告**: 敞口使用率、活跃仓位、每日盈亏
- **执行统计**: 总交易数、总利润、胜率、平均执行时间

## ⚠️ 注意事项

1. **测试优先**: 始终在模拟模式下充分测试
2. **风险控制**: 根据资金量合理设置风险限制
3. **数据质量**: 确保市场数据的准确性和时效性
4. **网络延迟**: 考虑网络延迟对套利的影响
5. **交易所限制**: 遵守各交易所的API使用限制

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

感谢原套利监控系统提供的基础架构思路。本系统在其基础上进行了全面升级和改进。

---

**🔥 核心改进总结**:

1. ✅ **完整成本分析** - 不再只看价差，考虑所有实际成本
2. ✅ **智能风险管理** - 多维度风险控制，保护资金安全
3. ✅ **流动性分析** - 评估实际可执行规模
4. ✅ **自动交易** - 支持自动和手动执行
5. ✅ **性能优化** - 高效的数据处理和缓存
6. ✅ **企业级架构** - 模块化、可扩展、易维护
