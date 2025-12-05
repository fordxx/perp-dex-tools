##### 关注我 **X (Twitter)**: [@yourQuantGuy](https://x.com/yourQuantGuy)

---

**English speakers**: Please read README_EN.md for the English version of this documentation.

## 📢 分享说明

**欢迎分享本项目！** 如果您要分享或修改此代码，请务必包含对原始仓库的引用。我们鼓励开源社区的发展，但请保持对原作者工作的尊重和认可。

---

## 自动交易机器人

一个支持多个交易所（目前包括 EdgeX, Backpack, Paradex, Aster, Lighter, grvt, Extended）的模块化交易机器人。该机器人实现了自动下单并在盈利时自动平仓的策略，主要目的是取得高交易量。

## 🔔 价格提醒系统 (Price Alert System) - NEW!

**全新功能**：智能价格监控和提醒系统，支持多种条件和自动化操作！

### 主要功能
- ✅ **实时价格监控** - 监控多个交易所的加密货币价格
- ✅ **灵活的提醒条件** - 价格突破、区间、百分比变化、跨交易所价差、波动率等
- ✅ **多种通知方式** - Telegram、Lark、控制台、音频、Webhook
- ✅ **自动交易触发** - 价格达到时自动启动交易机器人
- ✅ **提醒历史记录** - 完整的提醒历史和统计分析
- ✅ **YAML 配置管理** - 简单易用的配置文件

### 快速开始

**使用配置文件：**
```bash
python run_price_alert.py --config config/alerts/btc_alerts.yaml
```

**快速命令行提醒：**
```bash
# BTC 突破 65000 时提醒
python run_price_alert.py --exchange edgex --ticker BTC --price-above 65000

# ETH 跌破 3200 时提醒（带 Telegram 通知）
python run_price_alert.py --exchange edgex --ticker ETH --price-below 3200 --channels telegram
```

### 配置示例

```yaml
alerts:
  # 基础价格突破提醒
  - name: "BTC突破65000"
    exchange: "edgex"
    ticker: "BTC"
    conditions:
      - type: "price_above"
        value: 65000
    actions:
      - type: "notify"
        channels: ["telegram", "console"]
        message: "🚀 BTC突破$65,000!"

  # 跨交易所套利机会
  - name: "BTC套利机会"
    exchanges: ["edgex", "backpack"]
    ticker: "BTC"
    conditions:
      - type: "price_spread"
        value: 50  # 价差超过$50
    actions:
      - type: "notify"
        channels: ["telegram"]
        message: "💰 发现套利机会！"

  # 自动交易触发（谨慎使用）
  - name: "ETH自动买入"
    exchange: "edgex"
    ticker: "ETH"
    enabled: false  # 默认禁用
    conditions:
      - type: "price_below"
        value: 3100
    actions:
      - type: "execute_bot"
        command: "python runbot.py --exchange edgex --ticker ETH --quantity 0.1 --direction buy"
```

### 详细文档

完整使用指南请查看：[价格提醒系统使用指南](docs/PRICE_ALERT_GUIDE.md)

配置示例文件：
- `config/alerts/btc_alerts.yaml` - BTC 价格提醒配置
- `config/alerts/eth_alerts.yaml` - ETH 价格提醒配置
- `config/alerts/example_alerts.yaml` - 通用配置模板

---

## 💰 智能套利引擎 (Arbitrage Engine) - NEW!

**全新功能**：自动发现和执行跨交易所套利机会，最大化利润！

### 核心优势

- ✅ **智能利润计算** - 自动扣除手续费、滑点，计算真实净利润
- ✅ **机会评分系统** - 多维度评估套利机会（利润率、绝对利润、流动性、可靠性）
- ✅ **自动执行** - 可选的自动套利交易执行
- ✅ **实时监控** - 持续监控多个交易所的价格差异
- ✅ **风险控制** - 最大仓位限制、滑点保护、超时机制
- ✅ **统计分析** - 完整的套利历史记录和收益统计

### 套利利润优化要点

#### 1. 真实利润计算
```
真实利润 = 价差 - 手续费 - 滑点

示例：
买入价：$64,000 (EdgeX)
卖出价：$64,300 (Backpack)
表面价差：$300 (0.47%)

扣除成本：
- 买入手续费 (0.05%)：$32
- 卖出手续费 (0.02%)：$12.86
- 买入滑点 (0.1%)：$64
- 卖出滑点 (0.1%)：$64.30

真实利润：$126.84 (0.20%)
```

#### 2. 手续费优化
- **Lighter**: Maker 0%, Taker 0.03% - 最优选择
- **EdgeX**: VIP 1 永久费率 0.02%/0.05%
- **组合策略**: Lighter 买入 + Lighter 卖出 = 总手续费 0.03%

#### 3. 执行速度优化
- 并行执行订单（延迟 100-200ms）
- WebSocket 预连接（延迟 50-100ms）
- 预充值资金，避免转账延迟

### 快速开始

**监控模式（只显示机会）**：
```bash
# 监控 EdgeX 和 Backpack 的 BTC、ETH 套利机会
python run_arbitrage.py --exchanges edgex backpack --tickers BTC ETH

# 监控所有主流交易所
python run_arbitrage.py --exchanges edgex backpack lighter aster --tickers BTC ETH SOL
```

**自动执行模式（谨慎使用）**：
```bash
# 自动执行利润率 > 0.3% 的套利机会
python run_arbitrage.py --exchanges edgex backpack --tickers BTC --auto-execute --min-profit 0.3
```

### 配置参数

```bash
--exchanges        # 监控的交易所列表
--tickers          # 监控的币种列表
--min-profit       # 最小利润率阈值 (默认: 0.3%)
--interval         # 价格检查间隔秒数 (默认: 5)
--auto-execute     # 自动执行套利（谨慎！）
--max-position     # 最大仓位 USDT (默认: 1000)
--slippage         # 滑点估算 % (默认: 0.1)
```

### 高级套利策略

详细的套利优化策略请查看：[套利策略优化指南](docs/ARBITRAGE_STRATEGIES.md)

包含内容：
- 📊 准确的利润计算方法
- 💡 5种高级套利策略（三角套利、资金费率套利、闪电套利等）
- 🎯 实战优化技巧（预充值、动态阈值、智能路由等）
- 📈 利润提升案例（提升 1000%+ 的实战案例）
- 🛡️ 风险管理和问题排查
- 💰 收益预估（年化收益率 70-100%+）

### 套利引擎特性

#### 智能机会评分
```python
评分 = 利润率(40%) + 绝对利润(30%) + 价差大小(20%) + 交易所可靠性(10%)

# 只执行评分 > 70 的高质量机会
```

#### 实时监控输出
```
[14:30:25] 发现 3 个套利机会：
--------------------------------------------------------------------------------
1. BTC: Buy@edgex $64,000.00 -> Sell@backpack $64,300.00 |
   Spread: $300.00 (0.47%) | Est.Profit: $126.84 (0.20%) | Score: 85.3
2. ETH: Buy@lighter $3,200.00 -> Sell@backpack $3,215.00 |
   Spread: $15.00 (0.47%) | Est.Profit: $8.50 (0.27%) | Score: 72.1
3. SOL: Buy@edgex $142.50 -> Sell@aster $143.20 |
   Spread: $0.70 (0.49%) | Est.Profit: $0.45 (0.32%) | Score: 68.5
--------------------------------------------------------------------------------
```

#### 收益统计
```
📊 套利引擎统计
================================================================================
发现机会数: 147
执行交易数: 23
成功率: 95.7%
累计利润: $1,847.32
平均单次利润: $80.32
================================================================================
```

### 收益预估

**保守策略**（低风险）
- 资金：$10,000
- 最小利润率：0.5%
- 每天机会：5次
- 月收益：$600（年化 72%）

**激进策略**（高收益）
- 资金：$50,000
- 最小利润率：0.2%
- 每天机会：20次
- 月收益：$4,200（年化 100.8%）

---

## 📊 Web 实时监控仪表盘 (Web Dashboard) - NEW!

**全新功能**：现代化的实时监控仪表盘，让交易数据一目了然！

### 界面预览

🎨 **暗色主题**  |  📱 **响应式设计**  |  ⚡ **实时更新**

### 核心功能

- ✅ **实时价格监控** - 多交易所价格对比，自动更新
- ✅ **套利机会展示** - 智能评分，高亮高质量机会
- ✅ **收益统计图表** - 折线图实时展示利润增长
- ✅ **提醒历史查看** - 所有触发的提醒一目了然
- ✅ **WebSocket 推送** - 无需刷新，数据自动更新
- ✅ **RESTful API** - 完整的 API 接口，易于集成

### 快速开始

**1. 安装依赖**
```bash
pip install fastapi uvicorn
```

**2. 启动仪表盘**
```bash
# 基础启动
python run_dashboard.py

# 同时启动套利引擎
python run_dashboard.py --enable-arbitrage --exchanges edgex backpack --tickers BTC ETH
```

**3. 访问仪表盘**
```
浏览器打开: http://localhost:8000/dashboard
API 文档: http://localhost:8000/docs
```

### 主要界面

#### 1. 统计卡片
实时展示四大核心指标：
- 💰 累计利润：$1,847.32
- 🎯 套利机会：3 个
- 📈 执行交易：23 笔（成功率 95.7%）
- 🔔 价格提醒：12 次触发

#### 2. 套利机会面板
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 BTC 套利机会        评分: 85.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
买入@EDGEX → 卖出@BACKPACK

价差: $300 (0.47%)
预估利润: $126.84 (0.20%) ✅
买入价: $64,000    卖出价: $64,300
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 3. 实时价格面板
```
┌─────────────────────────┐
│ BTC          $64,250.00 │
│ EDGEX            +2.3% ↑│
├─────────────────────────┤
│ ETH           $3,420.00 │
│ BACKPACK         +1.8% ↑│
└─────────────────────────┘
```

#### 4. 收益趋势图表
实时折线图展示利润增长曲线

### 高级功能

#### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/prices` | GET | 获取最新价格 |
| `/api/arbitrage/opportunities` | GET | 获取套利机会 |
| `/api/alerts/history` | GET | 获取提醒历史 |
| `/api/statistics` | GET | 获取统计数据 |

#### WebSocket 实时推送

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // 实时数据自动推送
};
```

### 移动设备访问

```bash
# 允许局域网访问
python run_dashboard.py --host 0.0.0.0 --port 8000
```

在手机浏览器访问：`http://你的电脑IP:8000/dashboard`

### 完整文档

详细使用指南：[Web Dashboard 使用指南](docs/WEB_DASHBOARD_GUIDE.md)

包含内容：
- 📖 详细界面介绍
- ⚙️ 配置选项说明
- 📡 API 接口文档
- 🔧 自定义和扩展
- 🐛 问题排查指南

---

## 邀请链接 (获得返佣以及福利)

#### EdgeX: [https://pro.edgex.exchange/referral/QUANT](https://pro.edgex.exchange/referral/QUANT)

永久享受 VIP 1 费率；额外 10% 手续费返佣；10% 额外奖励积分

#### Backpack: [https://backpack.exchange/join/quant](https://backpack.exchange/join/quant)

使用我的推荐链接获得 35% 手续费返佣

#### Paradex: [https://app.paradex.trade/r/quant](https://app.paradex.trade/r/quant)

使用我的推荐链接获得 10% 手续费返佣以及潜在未来福利

#### Aster: [https://www.asterdex.com/zh-CN/referral/5191B1](https://www.asterdex.com/zh-CN/referral/5191B1)

使用我的推荐链接获得 30% 手续费返佣以及积分加成

#### grvt: [https://grvt.io/exchange/sign-up?ref=QUANT](https://grvt.io/exchange/sign-up?ref=QUANT)

获得 1.3x 全网最高的积分加成，未来的手续费返佣（官方预计 10 月中上线），以及即将开始的专属交易竞赛

#### Extended: [https://app.extended.exchange/join/QUANT](https://app.extended.exchange/join/QUANT)
10%的即时手续费减免；积分加成（官方未公布具体加成公式，但文档里有明确说明，通过官方大使邀请能拿到比自己小号邀请自己更多的分数）

#### ApeX: [https://join.omni.apex.exchange/quant]( https://join.omni.apex.exchange/quant)
30%返佣; 5%手续费减免; 积分加成; 有资格参与10月20日至11月2日的社区专属交易竞赛，总奖金高达$5500

## 安装

Python 版本要求（最佳选项是 Python 3.10 - 3.12）：

- grvt 要求 python 版本在 3.10 及以上
- Paradex 要求 python 版本在 3.9 - 3.12
- 其他交易所需要 python 版本在 3.8 及以上

1. **克隆仓库**：

   ```bash
   git clone <repository-url>
   cd perp-dex-tools
   ```

2. **创建并激活虚拟环境**：

   首先确保你目前不在任何虚拟环境中：

   ```bash
   deactivate
   ```

   创建虚拟环境：

   ```bash
   python3 -m venv env
   ```

   激活虚拟环境（每次使用脚本时，都需要激活虚拟环境）：

   ```bash
   source env/bin/activate  # Windows: env\Scripts\activate
   ```

3. **安装依赖**：
   首先确保你目前不在任何虚拟环境中：

   ```bash
   deactivate
   ```

   激活虚拟环境（每次使用脚本时，都需要激活虚拟环境）：

   ```bash
   source env/bin/activate  # Windows: env\Scripts\activate
   ```

   ```bash
   pip install -r requirements.txt
   ```

   **grvt 用户**：如果您想使用 grvt 交易所，需要额外安装 grvt 专用依赖：
   激活虚拟环境（每次使用脚本时，都需要激活虚拟环境）：

   ```bash
   source env/bin/activate  # Windows: env\Scripts\activate
   ```

   ```bash
   pip install grvt-pysdk
   ```

   **Paradex 用户**：如果您想使用 Paradex 交易所，需要额外创建一个虚拟环境并安装 Paradex 专用依赖：

   首先确保你目前不在任何虚拟环境中：

   ```bash
   deactivate
   ```

   创建 Paradex 专用的虚拟环境（名称为 para_env）：

   ```bash
   python3 -m venv para_env
   ```

   激活虚拟环境（每次使用脚本时，都需要激活虚拟环境）：

   ```bash
   source para_env/bin/activate  # Windows: para_env\Scripts\activate
   ```

   安装 Paradex 依赖

   ```bash
   pip install -r para_requirements.txt
   ```

   **apex 用户**：如果您想使用 apex 交易所，需要额外安装 apex 专用依赖：
   激活虚拟环境（每次使用脚本时，都需要激活虚拟环境）：

   ```bash
   source env/bin/activate  # Windows: env\Scripts\activate
   ```

   ```bash
   pip install -r apex_requirements.txt
   ```

4. **设置环境变量**：
   在项目根目录创建`.env`文件，并使用 env_example.txt 作为样本，修改为你的 api 密匙。

5. **Telegram 机器人设置（可选）**：
   如需接收交易通知，请参考 [Telegram 机器人设置指南](docs/telegram-bot-setup.md) 配置 Telegram 机器人。

## 策略概述

**重要提醒**：大家一定要先理解了这个脚本的逻辑和风险，这样你就能设置更适合你自己的参数，或者你也可能觉得这不是一个好策略，根本不想用这个策略来刷交易量。我在推特也说过，我不是为了分享而写这些脚本，而是我真的在用这个脚本，所以才写了，然后才顺便分享出来。
这个脚本主要还是要看长期下来的磨损，只要脚本持续开单，如果一个月后价格到你被套的最高点，那么你这一个月的交易量就都是零磨损的了。所以我认为如果把`--quantity`和`--wait-time`设置的太小，并不是一个好的长期的策略，但确实适合短期内高强度冲交易量。我自己一般用 40 到 60 的 quantity，450 到 650 的 wait-time，以此来保证即使市场和你的判断想法，脚本依然能够持续稳定地下单，直到价格回到你的开单点，实现零磨损刷了交易量。

该机器人实现了简单的交易策略：

1. **订单下单**：在市场价格附近下限价单
2. **订单监控**：等待订单成交
3. **平仓订单**：在止盈水平自动下平仓单
4. **持仓管理**：监控持仓和活跃订单
5. **风险管理**：限制最大并发订单数
6. **网格步长控制**：通过 `--grid-step` 参数控制新订单与现有平仓订单之间的最小价格距离
7. **停止交易控制**：通过 `--stop-price` 参数控制停止交易的的价格条件

#### ⚙️ 关键参数

- **quantity**: 每笔订单的交易数量
- **direction**: 脚本交易的方向，buy 表示看多，sell 表示看空
- **take-profit**: 止盈百分比（如 0.02 表示 0.02%）
- **max-orders**: 最大同时活跃订单数（风险控制）
- **wait-time**: 订单间等待时间（避免过于频繁交易）
- **grid-step**: 网格步长控制（防止平仓订单过于密集）
- **stop-price**: 当市场价格达到该价格时退出脚本
- **pause-price**: 当市场价格达到该价格时暂停脚本

#### 网格步长功能详解

`--grid-step` 参数用于控制新订单的平仓价格与现有平仓订单之间的最小距离：

- **默认值 -100**：无网格步长限制，按原策略执行
- **正值（如 0.5）**：新订单的平仓价格必须与最近的平仓订单价格保持至少 0.5% 的距离
- **作用**：防止平仓订单过于密集，提高成交概率和风险管理

例如，当看多且 `--grid-step 0.5` 时：

- 如果现有平仓订单价格为 2000 USDT
- 新订单的平仓价格必须低于 1990 USDT（2000 × (1 - 0.5%)）
- 这样可以避免平仓订单过于接近，提高整体策略效果

#### 📊 交易流程示例

假设当前 ETH 价格为 $2000，设置止盈为 0.02%：

1. **开仓**：在 $2000.40 下买单（略高于市价）
2. **成交**：订单被市场成交，获得多头仓位
3. **平仓**：立即在 $2000.80 下卖单（止盈价格）
4. **完成**：平仓单成交，获得 0.02% 利润
5. **重复**：继续下一轮交易

#### 🛡️ 风险控制

- **订单限制**：通过 `max-orders` 限制最大并发订单数
- **网格控制**：通过 `grid-step` 确保平仓订单有合理间距
- **下单频率控制**：通过 `wait-time` 确保下单的时间间隔，防止短时间内被套
- **实时监控**：持续监控持仓和订单状态
- **⚠️ 无止损机制**：此策略不包含止损功能，在不利市场条件下可能面临较大损失

## 示例命令：

### EdgeX 交易所：

ETH：

```bash
python runbot.py --exchange edgex --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450
```

ETH（带网格步长控制）：

```bash
python runbot.py --exchange edgex --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450 --grid-step 0.5
```

ETH（带停止交易的价格控制）：

```bash
python runbot.py --exchange edgex --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450 --stop-price 5500
```

BTC：

```bash
python runbot.py --exchange edgex --ticker BTC --quantity 0.05 --take-profit 0.02 --max-orders 40 --wait-time 450
```

### Backpack 交易所：

ETH 永续合约：

```bash
python runbot.py --exchange backpack --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450
```

ETH 永续合约（带网格步长控制）：

```bash
python runbot.py --exchange backpack --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450 --grid-step 0.3
```

ETH 永续合约（启用 Boost 模式）：

```bash
python runbot.py --exchange backpack --ticker ETH --direction buy --quantity 0.1 --boost
```

### Aster 交易所：

ETH：

```bash
python runbot.py --exchange aster --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450
```

ETH（启用 Boost 模式）：

```bash
python runbot.py --exchange aster --ticker ETH --direction buy --quantity 0.1 --boost
```

### GRVT 交易所：

BTC：

```bash
python runbot.py --exchange grvt --ticker BTC --quantity 0.05 --take-profit 0.02 --max-orders 40 --wait-time 450
```

### Extended 交易所：

ETH：

```bash
python runbot.py --exchange extended --ticker ETH --quantity 0.1 --take-profit 0 --max-orders 40 --wait-time 450 --grid-step 0.1
```

## 🆕 对冲模式 (Hedge Mode)

新增的对冲模式 (`hedge_mode.py`) 是一个新的交易策略，通过同时在两个交易所进行对冲交易来降低风险：

### 对冲模式工作原理

1. **开仓阶段**：在选定交易所（如 Backpack）下 maker 订单
2. **对冲阶段**：订单成交后，立即在 Lighter 下市价订单进行对冲
3. **平仓阶段**：在选定交易所下另一个 maker 订单平仓
4. **对冲平仓**：在 Lighter 下市价订单平仓

### 对冲模式优势

- **风险降低**：通过同时持有相反头寸，降低单边市场风险
- **交易量提升**：在两个交易所同时产生交易量
- **套利机会**：利用两个交易所之间的价差
- **自动化执行**：全自动化的对冲交易流程

### 对冲模式使用示例

```bash
# 运行 BTC 对冲模式（Backpack）
python hedge_mode.py --exchange backpack --ticker BTC --size 0.05 --iter 20 --max-position 1

# 运行 ETH 对冲模式（Extended）
python hedge_mode.py --exchange extended --ticker ETH --size 0.1 --iter 20

# 运行 BTC 对冲模式（Apex）
python hedge_mode.py --exchange apex --ticker BTC --size 0.05 --iter 20

# 运行 BTC 对冲模式（GRVT）
python hedge_mode.py --exchange grvt --ticker BTC --size 0.05 --iter 20

# 运行 BTC 对冲模式（edgeX）
python hedge_mode.py --exchange edgex --ticker BTC --size 0.001 --iter 20
```

### 对冲模式参数

- `--exchange`: 主要交易所（支持 'backpack', 'extended', 'apex', 'grvt', 'edgex'）
- `--ticker`: 交易对符号（如 BTC, ETH）
- `--size`: 每笔订单数量
- `--iter`: 交易循环次数
- `--fill-timeout`: maker 订单填充超时时间（秒，默认 5）
- `--sleep`: 每一笔交易之后的暂停时间，增加持仓时间（秒，默认 0）
- `--max-position`: 当设置了这个参数后，对冲模式会在对冲的同时逐渐建仓到设置的最大仓位，单位是币本位，比如在跑btc时设置0.1，就是指逐渐建仓到0.1btc，并逐渐建仓。达到这个最大仓位后，会逐渐建仓，以此循环。

## 配置

### 环境变量

#### 通用配置

- `ACCOUNT_NAME`: 环境变量中当前账号的名称，用于多账号日志区分，可自定义，非必须

#### Telegram 配置（可选）

- `TELEGRAM_BOT_TOKEN`: Telegram 机器人令牌
- `TELEGRAM_CHAT_ID`: Telegram 对话 ID

#### EdgeX 配置

- `EDGEX_ACCOUNT_ID`: 您的 EdgeX 账户 ID
- `EDGEX_STARK_PRIVATE_KEY`: 您的 EdgeX API 私钥
- `EDGEX_BASE_URL`: EdgeX API 基础 URL（默认：https://pro.edgex.exchange）
- `EDGEX_WS_URL`: EdgeX WebSocket URL（默认：wss://quote.edgex.exchange）

#### Backpack 配置

- `BACKPACK_PUBLIC_KEY`: 您的 Backpack API Key
- `BACKPACK_SECRET_KEY`: 您的 Backpack API Secret

#### Paradex 配置

- `PARADEX_L1_ADDRESS`: L1 钱包地址
- `PARADEX_L2_PRIVATE_KEY`: L2 钱包私钥（点击头像，钱包，"复制 paradex 私钥"）

#### Aster 配置

- `ASTER_API_KEY`: 您的 Aster API Key
- `ASTER_SECRET_KEY`: 您的 Aster API Secret

#### Lighter 配置

- `API_KEY_PRIVATE_KEY`: Lighter API 私钥
- `LIGHTER_ACCOUNT_INDEX`: Lighter 账户索引
- `LIGHTER_API_KEY_INDEX`: Lighter API 密钥索引

#### GRVT 配置

- `GRVT_TRADING_ACCOUNT_ID`: 您的 GRVT 交易账户 ID
- `GRVT_PRIVATE_KEY`: 您的 GRVT 私钥
- `GRVT_API_KEY`: 您的 GRVT API 密钥

#### Extended 配置

- `EXTENDED_API_KEY`: Extended API Key
- `EXTENDED_STARK_KEY_PUBLIC`: 创建API后显示的 Stark 公钥
- `EXTENDED_STARK_KEY_PRIVATE`: 创建API后显示的 Stark 私钥
- `EXTENDED_VAULT`: 创建API后显示的 Extended Vault ID

#### Apex 配置

- `APEX_API_KEY`: 您的 Apex API 密钥
- `APEX_API_KEY_PASSPHRASE`: 您的 Apex API 密钥密码
- `APEX_API_KEY_SECRET`: 您的 Apex API 密钥私钥
- `APEX_OMNI_KEY_SEED`: 您的 Apex Omni 密钥种子

**获取 LIGHTER_ACCOUNT_INDEX 的方法**：

1. 在下面的网址最后加上你的钱包地址：

   ```
   https://mainnet.zklighter.elliot.ai/api/v1/account?by=l1_address&value=
   ```

2. 在浏览器中打开这个网址

3. 在结果中搜索 "account_index" - 如果你有子账户，会有多个 account_index，短的那个是你主账户的，长的是你的子账户。

### 命令行参数

- `--exchange`: 使用的交易所：'edgex'、'backpack'、'paradex'、'aster'、'lighter'、'grvt' 或 'extended'（默认：edgex）
- `--ticker`: 标的资产符号（例如：ETH、BTC、SOL）。合约 ID 自动解析。
- `--quantity`: 订单数量（默认：0.1）
- `--take-profit`: 止盈百分比（例如 0.02 表示 0.02%）
- `--direction`: 交易方向：'buy'或'sell'（默认：buy）
- `--env-file`: 账户配置文件 (默认：.env)
- `--max-orders`: 最大活跃订单数（默认：40）
- `--wait-time`: 订单间等待时间（秒）（默认：450）
- `--grid-step`: 与下一个平仓订单价格的最小距离百分比（默认：-100，表示无限制）
- `--stop-price`: 当 `direction` 是 'buy' 时，当 price >= stop-price 时停止交易并退出程序；'sell' 逻辑相反（默认：-1，表示不会因为价格原因停止交易），参数的目的是防止订单被挂在”你认为的开多高点或开空低点“。
- `--pause-price`: 当 `direction` 是 'buy' 时，当 price >= pause-price 时暂停交易，并在价格回到 pause-price 以下时重新开始交易；'sell' 逻辑相反（默认：-1，表示不会因为价格原因停止交易），参数的目的是防止订单被挂在”你认为的开多高点或开空低点“。
- `--boost`: 启用 Boost 模式进行交易量提升（仅适用于 aster 和 backpack 交易所）
  Boost 模式的下单逻辑：下 maker 单开仓，成交后立即用 taker 单关仓，以此循环。磨损为一单 maker，一单 taker 的手续费，以及滑点。

## 日志记录

该机器人提供全面的日志记录：

- **交易日志**：包含订单详情的 CSV 文件
- **调试日志**：带时间戳的详细活动日志
- **控制台输出**：实时状态更新
- **错误处理**：全面的错误日志记录和处理

## Q & A

### 如何在同一设备配置同一交易所的多个账号？

1. 为每个账户创建一个 .env 文件，如 account_1.env, account_2.env
2. 在每个账户的 .env 文件中设置 `ACCOUNT_NAME=`, 如`ACCOUNT_NAME=MAIN`。
3. 在每个文件中配置好每个账户的 API key 或是密匙
4. 通过更改命令行中的 `--env-file` 参数来开始不同的账户，如 `python runbot.py --env-file account_1.env [其他参数...]`

### 如何在同一设备配置不同交易所的多个账号？

将不同交易所的账号都配置在同一 `.env` 文件后，通过更改命令行中的 `--exchange` 参数来开始不同的交易所，如 `python runbot.py --exchange backpack [其他参数...]`

### 如何在同一设备用同一账号配置同一交易所的多个合约？

将账号配置在 `.env` 文件后，通过更改命令行中的 `--ticker` 参数来开始不同的合约，如 `python runbot.py --ticker ETH [其他参数...]`

## 贡献

1. Fork 仓库
2. 创建功能分支
3. 进行更改
4. 如适用，添加测试
5. 提交拉取请求

## 许可证

本项目采用非商业许可证 - 详情请参阅[LICENSE](LICENSE)文件。

**重要提醒**：本软件仅供个人学习和研究使用，严禁用于任何商业用途。如需商业使用，请联系作者获取商业许可证。

## 免责声明

本软件仅供教育和研究目的。加密货币交易涉及重大风险，可能导致重大财务损失。使用风险自负，切勿用您无法承受损失的资金进行交易。
