# 价格提醒系统使用指南

## 📖 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [功能特性](#功能特性)
- [配置文件详解](#配置文件详解)
- [使用示例](#使用示例)
- [高级功能](#高级功能)
- [常见问题](#常见问题)

---

## 概述

价格提醒系统是一个强大的加密货币价格监控工具，可以实时监控多个交易所的价格变化，并在满足特定条件时触发自动通知或执行交易操作。

### 主要特性

✅ **多交易所支持** - 支持 EdgeX, Backpack, Aster, GRVT, Extended, Lighter, Paradex, Apex
✅ **灵活的提醒条件** - 价格突破、区间、百分比变化、价差、波动率等
✅ **多种通知方式** - Telegram, Lark, 控制台, 音频, Webhook
✅ **自动交易触发** - 价格达到时自动启动交易机器人
✅ **提醒历史记录** - 完整的提醒历史和统计分析
✅ **配置文件管理** - YAML 配置文件，易于管理和分享

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

确保 `.env` 文件中配置了必要的 API 密钥和通知渠道：

```bash
# Telegram 通知（可选）
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Lark 通知（可选）
LARK_WEBHOOK_URL=your_webhook_url

# 交易所 API 密钥（必需）
EDGEX_ACCOUNT_ID=...
EDGEX_STARK_PRIVATE_KEY=...
# ... 其他交易所配置
```

### 3. 运行简单提醒

**方式一：使用配置文件**

```bash
python run_price_alert.py --config config/alerts/btc_alerts.yaml
```

**方式二：快速命令行提醒**

```bash
# BTC 突破 65000 时提醒
python run_price_alert.py --exchange edgex --ticker BTC --price-above 65000

# ETH 跌破 3200 时提醒（带 Telegram 通知）
python run_price_alert.py --exchange edgex --ticker ETH --price-below 3200 --channels telegram
```

---

## 功能特性

### 提醒条件类型

| 条件类型 | 说明 | 示例 |
|---------|------|------|
| `price_above` | 价格突破某个值 | BTC > $65,000 |
| `price_below` | 价格跌破某个值 | ETH < $3,200 |
| `price_range` | 价格在某个区间内 | BTC 在 $60,000 - $62,000 |
| `percent_change` | 价格变化百分比 | 1小时涨幅 > 5% |
| `price_spread` | 跨交易所价差 | EdgeX 和 Backpack 价差 > $50 |
| `volatility` | 波动率监控 | 1小时波动率 > 3% |

### 动作类型

| 动作类型 | 说明 | 配置示例 |
|---------|------|---------|
| `notify` | 发送通知 | channels: [telegram, lark, console] |
| `sound` | 播放音频提醒 | enabled: true |
| `execute_bot` | 执行交易机器人 | command: "python runbot.py ..." |
| `webhook` | 发送 Webhook | webhook_url: "https://..." |
| `log_only` | 仅记录日志 | - |

---

## 配置文件详解

### 基础结构

```yaml
# 全局设置
check_interval: 10  # 价格检查间隔（秒）
enable_sound: true  # 启用音频提醒
log_level: "INFO"   # 日志级别

# 提醒规则列表
alerts:
  - name: "提醒名称"
    exchange: "edgex"
    ticker: "BTC"
    enabled: true
    repeat: false
    cooldown: 300
    conditions:
      - type: "price_above"
        value: 65000
    actions:
      - type: "notify"
        channels: ["telegram"]
        message: "BTC突破$65,000!"
```

### 完整配置参数

#### 全局参数

```yaml
check_interval: 10           # 价格检查间隔（秒），默认 10
enable_sound: true           # 启用音频提醒，默认 true
enable_terminal_ui: true     # 启用终端UI，默认 true
log_level: "INFO"           # 日志级别: DEBUG, INFO, WARNING, ERROR
```

#### 提醒规则参数

```yaml
- name: "提醒名称"              # 必需：提醒规则的名称
  exchange: "edgex"            # 单个交易所（可选）
  exchanges: ["edgex", "bp"]   # 多个交易所（可选，用于价差监控）
  ticker: "BTC"               # 必需：币种代码
  enabled: true               # 是否启用，默认 true
  repeat: false               # 是否重复触发，默认 false
  cooldown: 300               # 冷却时间（秒），默认 300
  priority: 0                 # 优先级，默认 0
```

---

## 使用示例

### 示例 1：基础价格突破提醒

**目标**：BTC 突破 $65,000 时发送 Telegram 通知

```yaml
alerts:
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
      - type: "sound"
        enabled: true
```

**运行**：
```bash
python run_price_alert.py --config config/alerts/btc_alerts.yaml
```

### 示例 2：价格区间买入提醒

**目标**：ETH 在 $3,100 - $3,200 区间时提醒买入

```yaml
alerts:
  - name: "ETH买入区间"
    exchange: "edgex"
    ticker: "ETH"
    repeat: true
    cooldown: 3600  # 1小时只提醒一次
    conditions:
      - type: "price_range"
        min_value: 3100
        max_value: 3200
    actions:
      - type: "notify"
        channels: ["telegram"]
        message: "💰 ETH进入买入区间 [$3,100-$3,200]"
```

### 示例 3：快速涨跌提醒

**目标**：BTC 1小时涨幅或跌幅超过 3% 时提醒

```yaml
alerts:
  # 快速上涨
  - name: "BTC快速上涨"
    exchange: "edgex"
    ticker: "BTC"
    repeat: true
    cooldown: 1800
    conditions:
      - type: "percent_change"
        percent: 3
        timeframe: "1h"
    actions:
      - type: "notify"
        channels: ["telegram"]
        message: "📈 BTC 1小时涨幅超过3%"

  # 快速下跌
  - name: "BTC快速下跌"
    exchange: "edgex"
    ticker: "BTC"
    repeat: true
    cooldown: 1800
    conditions:
      - type: "percent_change"
        percent: -3
        timeframe: "1h"
    actions:
      - type: "notify"
        channels: ["telegram"]
        message: "📉 BTC 1小时跌幅超过3%"
```

### 示例 4：跨交易所套利提醒

**目标**：监控 EdgeX 和 Backpack 之间的 BTC 价差，超过 $50 时提醒

```yaml
alerts:
  - name: "BTC套利机会"
    exchanges: ["edgex", "backpack"]
    ticker: "BTC"
    repeat: true
    cooldown: 600
    conditions:
      - type: "price_spread"
        value: 50
        comparison_exchange: "backpack"
    actions:
      - type: "notify"
        channels: ["telegram"]
        message: "💰 BTC价差超过$50！套利机会"
```

### 示例 5：自动交易触发

**目标**：BTC 跌破 $60,000 时自动启动交易机器人买入

⚠️ **警告**：自动交易有风险，请充分测试后再使用！

```yaml
alerts:
  - name: "BTC自动买入"
    exchange: "edgex"
    ticker: "BTC"
    enabled: false  # 默认禁用，需要时手动启用
    repeat: false
    cooldown: 7200
    conditions:
      - type: "price_below"
        value: 60000
    actions:
      - type: "notify"
        channels: ["telegram"]
        message: "🤖 BTC达到买入价格，启动交易机器人"
      - type: "execute_bot"
        command: "python runbot.py --exchange edgex --ticker BTC --quantity 0.05 --direction buy --max-orders 20"
```

### 示例 6：波动率监控

**目标**：ETH 1小时波动率超过 3% 时提醒（高波动警告）

```yaml
alerts:
  - name: "ETH高波动率"
    exchange: "edgex"
    ticker: "ETH"
    repeat: true
    cooldown: 3600
    conditions:
      - type: "volatility"
        percent: 3
        timeframe: "1h"
    actions:
      - type: "notify"
        channels: ["telegram", "console"]
        message: "⚡ ETH波动率飙升！注意风险"
```

---

## 高级功能

### 1. 监控多个配置文件

同时加载多个配置文件，统一监控：

```bash
python run_price_alert.py --config \
  config/alerts/btc_alerts.yaml \
  config/alerts/eth_alerts.yaml \
  config/alerts/sol_alerts.yaml
```

### 2. 自定义检查间隔

```bash
python run_price_alert.py --config config/alerts/btc_alerts.yaml --interval 5
```

### 3. 命令行快速提醒

无需配置文件，直接从命令行创建提醒：

```bash
# BTC 突破 65000
python run_price_alert.py --exchange edgex --ticker BTC --price-above 65000

# ETH 跌破 3200，带 Telegram 通知
python run_price_alert.py --exchange edgex --ticker ETH --price-below 3200 --channels telegram

# 价格区间提醒
python run_price_alert.py --exchange backpack --ticker BTC --price-range 60000,62000 --repeat

# 自定义消息
python run_price_alert.py --exchange edgex --ticker BTC --price-above 65000 \
  --message "BTC突破目标价格！立即查看" --channels telegram,lark
```

### 4. 提醒历史和统计

提醒历史会自动保存在：
- `logs/alerts/alert_history.json` - JSON 格式
- `logs/alerts/alert_history.csv` - CSV 格式（便于 Excel 分析）

查看统计信息：程序退出时会自动显示统计摘要。

### 5. Webhook 集成

发送提醒到自定义 Webhook（可集成 Discord, Slack 等）：

```yaml
actions:
  - type: "webhook"
    webhook_url: "https://your-webhook-url.com/alerts"
```

Webhook 接收的数据格式：
```json
{
  "alert_name": "BTC突破65000",
  "exchange": "edgex",
  "ticker": "BTC",
  "current_price": "65123.45",
  "trigger_reason": "Price $65,123.45 is above $65,000.00",
  "timestamp": "2025-12-05T14:30:00"
}
```

---

## 常见问题

### Q1: 如何配置 Telegram 通知？

1. 创建 Telegram Bot（与 @BotFather 对话）
2. 获取 Bot Token
3. 获取你的 Chat ID（与 @userinfobot 对话）
4. 在 `.env` 文件中配置：
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

详细教程：[Telegram Bot 设置指南](telegram-bot-setup.md)

### Q2: 如何避免频繁提醒？

使用 `cooldown` 和 `repeat` 参数：

```yaml
- name: "BTC价格监控"
  repeat: true       # 允许重复触发
  cooldown: 3600     # 但每次触发后冷却1小时
```

### Q3: 可以同时监控多个交易所吗？

可以！有两种方式：

**方式一**：为每个交易所创建独立提醒
```yaml
alerts:
  - name: "BTC EdgeX"
    exchange: "edgex"
    ticker: "BTC"
    ...
  - name: "BTC Backpack"
    exchange: "backpack"
    ticker: "BTC"
    ...
```

**方式二**：使用价差监控（适合套利）
```yaml
alerts:
  - name: "BTC套利"
    exchanges: ["edgex", "backpack"]
    ticker: "BTC"
    conditions:
      - type: "price_spread"
        value: 50
```

### Q4: 自动交易安全吗？

⚠️ **自动交易有风险！** 建议：

1. 先用小金额测试
2. 设置合理的 `cooldown` 避免频繁交易
3. 使用 `repeat: false` 确保只执行一次
4. 默认设置 `enabled: false`，需要时手动启用
5. 充分理解交易机器人的逻辑

### Q5: 如何停止价格提醒？

按 `Ctrl+C` 优雅退出，系统会：
- 断开所有交易所连接
- 保存提醒历史
- 显示统计摘要

### Q6: 支持哪些时间范围？

支持的 timeframe 格式：
- `5m` = 5分钟
- `15m` = 15分钟
- `1h` = 1小时
- `4h` = 4小时
- `24h` = 24小时
- `7d` = 7天

### Q7: 价格数据从哪里来？

直接从各个交易所的 API 实时获取，复用现有的 exchange clients，数据准确可靠。

### Q8: 可以监控多少个提醒？

理论上没有限制，但建议：
- 每个配置文件 10-20 个提醒
- 总共不超过 50-100 个活跃提醒
- 适当调整 `check_interval` 避免 API 限流

---

## 配置文件模板

### 完整示例模板

参考以下配置文件：
- `config/alerts/example_alerts.yaml` - 通用模板，包含所有功能示例
- `config/alerts/btc_alerts.yaml` - BTC 专用配置
- `config/alerts/eth_alerts.yaml` - ETH 专用配置

### 最小配置

```yaml
check_interval: 10
alerts:
  - name: "我的第一个提醒"
    exchange: "edgex"
    ticker: "BTC"
    conditions:
      - type: "price_above"
        value: 65000
    actions:
      - type: "notify"
        channels: ["console"]
```

---

## 贡献和反馈

如有问题或建议，欢迎：
- 提交 Issue
- 分享你的配置文件
- 贡献新功能

---

## 许可证

本项目采用非商业许可证，仅供个人学习和研究使用。

## 免责声明

加密货币交易涉及重大风险，本工具仅供辅助决策，不构成投资建议。使用风险自负。
