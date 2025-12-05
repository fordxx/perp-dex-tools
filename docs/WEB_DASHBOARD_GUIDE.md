# Web Dashboard 使用指南

## 📊 功能概述

Web Dashboard 是一个现代化的实时监控仪表盘，提供以下功能：

### 核心功能

✅ **实时价格监控** - 跨多个交易所的加密货币价格实时展示
✅ **套利机会展示** - 自动发现并展示套利机会，包含评分和详细信息
✅ **收益统计** - 实时图表展示累计利润和交易统计
✅ **价格提醒管理** - 查看已触发的价格提醒历史
✅ **WebSocket 实时推送** - 无需刷新页面，数据自动更新
✅ **响应式设计** - 完美支持桌面和移动设备

---

## 🚀 快速开始

### 1. 安装依赖

Web Dashboard 需要额外的依赖：

```bash
pip install fastapi uvicorn websockets
```

或者更新 requirements.txt 后安装：

```bash
pip install -r requirements.txt
```

### 2. 启动仪表盘

**基础启动**（仅 Web 界面）：

```bash
python run_dashboard.py
```

**完整启动**（Web 界面 + 套利引擎）：

```bash
python run_dashboard.py --enable-arbitrage --exchanges edgex backpack --tickers BTC ETH
```

### 3. 访问仪表盘

启动后，在浏览器中打开：

```
http://localhost:8000/dashboard
```

---

## 🎨 界面介绍

### 1. 统计卡片（顶部）

四个实时更新的统计卡片：

- **累计利润** - 显示总利润和增长率
- **套利机会** - 当前发现的套利机会数量
- **执行交易** - 已执行的交易次数和成功率
- **价格提醒** - 已触发的提醒数量

### 2. 套利机会面板（左侧）

**功能**：
- 实时展示发现的套利机会
- 按评分排序（评分 0-100）
- 高亮显示高质量机会（评分 >75）

**卡片信息**：
```
🏆 评分：85.3 ← 综合评分
├─ 币种：BTC
├─ 路径：买入@EDGEX → 卖出@BACKPACK
├─ 价差：$300.00 (0.47%)
├─ 预估利润：$126.84 (0.20%)
├─ 买入价：$64,000.00
└─ 卖出价：$64,300.00
```

**评分颜色**：
- 🟢 绿色边框：高分机会（>75分）
- 🟡 黄色边框：中等机会（50-75分）
- ⚪ 灰色边框：低分机会（<50分）

### 3. 收益趋势图表

**功能**：
- 实时折线图展示累计利润变化
- 自动更新（保留最近 20 个数据点）
- 流畅的动画效果

### 4. 实时价格面板（右侧）

**功能**：
- 展示所有监控交易所的加密货币价格
- 显示涨跌幅（带颜色标识）
- 手动刷新按钮

**价格卡片**：
```
BTC                    $64,250.00
EDGEX                     +2.3% ↑
```

### 5. 最近提醒面板

**功能**：
- 展示最近触发的价格提醒
- 显示触发时间和提醒内容
- 自动滚动到最新提醒

---

## ⚙️ 配置选项

### 基础配置

```bash
# 默认启动（本地访问，8000 端口）
python run_dashboard.py

# 指定端口
python run_dashboard.py --port 8080

# 允许外部访问（局域网）
python run_dashboard.py --host 0.0.0.0 --port 8000
```

### 套利引擎配置

```bash
# 启用套利监控
python run_dashboard.py \
  --enable-arbitrage \
  --exchanges edgex backpack lighter \
  --tickers BTC ETH SOL \
  --min-profit 0.3
```

**参数说明**：
- `--enable-arbitrage`: 启动时自动开启套利引擎
- `--exchanges`: 监控的交易所列表
- `--tickers`: 监控的币种列表
- `--min-profit`: 最小利润率阈值（百分比）

### 开发模式

```bash
# 启用热重载（修改代码自动重启）
python run_dashboard.py --reload
```

---

## 📡 API 接口

Dashboard 提供完整的 RESTful API 和 WebSocket 接口。

### REST API

访问 API 文档：`http://localhost:8000/docs`

**主要接口**：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/prices` | GET | 获取最新价格 |
| `/api/arbitrage/opportunities` | GET | 获取套利机会 |
| `/api/alerts/history` | GET | 获取提醒历史 |
| `/api/statistics` | GET | 获取统计数据 |
| `/api/arbitrage/start` | POST | 启动套利引擎 |
| `/api/arbitrage/stop` | POST | 停止套利引擎 |

**示例请求**：

```bash
# 获取当前价格
curl http://localhost:8000/api/prices

# 获取套利机会
curl http://localhost:8000/api/arbitrage/opportunities

# 获取统计数据
curl http://localhost:8000/api/statistics
```

**示例响应**：

```json
{
  "timestamp": "2025-12-05T14:30:00",
  "opportunities": [
    {
      "ticker": "BTC",
      "buy_exchange": "edgex",
      "sell_exchange": "backpack",
      "buy_price": 64000.00,
      "sell_price": 64300.00,
      "spread": 300.00,
      "spread_percent": 0.47,
      "estimated_profit": 126.84,
      "profit_percent": 0.20,
      "score": 85.3
    }
  ],
  "count": 1
}
```

### WebSocket 接口

**连接地址**：`ws://localhost:8000/ws`

**实时数据推送**：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    // data.type === 'arbitrage_update'
    // data.data.prices - 最新价格
    // data.data.opportunities - 套利机会
    // data.data.statistics - 统计数据
};
```

**推送频率**：每 5 秒（可配置）

**推送内容**：
```json
{
  "type": "arbitrage_update",
  "data": {
    "prices": {
      "edgex": { "BTC": 64000, "ETH": 3200 },
      "backpack": { "BTC": 64300, "ETH": 3215 }
    },
    "opportunities": [...],
    "statistics": {
      "total_profit": 1847.32,
      "total_trades": 23,
      "total_opportunities": 147
    }
  }
}
```

---

## 🎯 实际使用场景

### 场景 1：仅监控价格

适合：了解市场行情，不执行交易

```bash
# 启动仪表盘
python run_dashboard.py

# 在另一个终端运行价格提醒
python run_price_alert.py --config config/alerts/btc_alerts.yaml
```

**优势**：
- 实时查看多交易所价格
- 发现价差机会
- 收到价格提醒时在 Dashboard 查看详情

### 场景 2：套利监控 + 手动执行

适合：想要看到机会后手动决策

```bash
# 启动仪表盘 + 套利监控
python run_dashboard.py \
  --enable-arbitrage \
  --exchanges edgex backpack lighter \
  --tickers BTC ETH
```

**优势**：
- 实时看到套利机会和评分
- 评估后手动执行高分机会
- 降低风险，完全掌控

### 场景 3：全自动套利

适合：已充分测试，自动化执行

```bash
# 1. 启动 Dashboard
python run_dashboard.py --port 8000

# 2. 在另一终端启动自动套利
python run_arbitrage.py \
  --exchanges edgex backpack \
  --tickers BTC ETH \
  --auto-execute \
  --min-profit 0.5
```

**优势**：
- Dashboard 实时监控执行情况
- 查看实时利润增长
- 随时查看统计数据

### 场景 4：移动设备监控

```bash
# 绑定到所有网络接口
python run_dashboard.py --host 0.0.0.0 --port 8000
```

然后在手机浏览器访问：
```
http://你的电脑IP:8000/dashboard
```

**优势**：
- 随时随地查看交易状态
- 响应式设计完美适配手机
- 实时推送无需刷新

---

## 🔧 自定义和扩展

### 修改更新频率

编辑 `arbitrage_engine.py`：

```python
# 原来
await asyncio.sleep(5)  # 5秒更新一次

# 改为更快
await asyncio.sleep(2)  # 2秒更新一次
```

### 添加自定义指标

编辑 `web_dashboard/app.py`，添加新的 API 端点：

```python
@self.app.get("/api/custom/metric")
async def get_custom_metric():
    return {
        "metric_name": "custom_value",
        "timestamp": datetime.now().isoformat()
    }
```

### 修改界面样式

编辑 `web_dashboard/static/style.css`：

```css
/* 修改主题颜色 */
:root {
    --accent-primary: #4ade80;  /* 改为你喜欢的颜色 */
}

/* 修改字体 */
body {
    font-family: 'Your Font', sans-serif;
}
```

---

## 📈 性能优化

### 1. 减少 WebSocket 推送频率

如果数据量大，可以降低推送频率：

```python
# 在 _run_arbitrage_engine 中
await asyncio.sleep(10)  # 从 5 秒改为 10 秒
```

### 2. 限制历史数据量

```python
# 只保留最近 50 个机会
self.arbitrage_opportunities = opportunities[:50]
```

### 3. 使用数据库

对于长期运行，建议使用数据库存储历史数据：

```python
# 安装 SQLAlchemy
pip install sqlalchemy

# 使用 SQLite 或 PostgreSQL 存储历史
```

---

## 🛡️ 安全建议

### 1. 生产环境部署

**不要暴露到公网**：

```bash
# ❌ 危险 - 任何人都可以访问
python run_dashboard.py --host 0.0.0.0 --port 8000

# ✅ 安全 - 仅本地访问
python run_dashboard.py --host 127.0.0.1 --port 8000
```

### 2. 使用反向代理

推荐使用 Nginx 做反向代理并添加认证：

```nginx
server {
    listen 80;
    server_name dashboard.yourdomain.com;

    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3. 启用 HTTPS

使用 Let's Encrypt 免费证书：

```bash
certbot --nginx -d dashboard.yourdomain.com
```

---

## 🐛 问题排查

### Q1: Dashboard 打开后没有数据

**可能原因**：
1. 套利引擎未启动
2. WebSocket 连接失败

**解决方法**：
```bash
# 方法 1: 启动时直接启用套利引擎
python run_dashboard.py --enable-arbitrage

# 方法 2: 使用 API 启动
curl -X POST http://localhost:8000/api/arbitrage/start \
  -H "Content-Type: application/json" \
  -d '{
    "exchanges": ["edgex", "backpack"],
    "tickers": ["BTC", "ETH"],
    "min_profit_percent": 0.3
  }'
```

### Q2: WebSocket 连接断开

**检查**：
- 浏览器控制台是否有错误
- 服务器日志是否有异常

**解决**：
- 前端会自动重连（5秒后）
- 如果持续失败，重启服务器

### Q3: 移动设备无法访问

**检查**：
- 确保使用 `--host 0.0.0.0`
- 确保防火墙允许端口
- 确保手机和电脑在同一局域网

```bash
# 查看本机 IP
# Linux/Mac
ifconfig | grep inet

# Windows
ipconfig
```

### Q4: 图表不显示

**可能原因**：Chart.js 加载失败

**解决**：检查网络连接，或下载 Chart.js 到本地：

```bash
# 下载 Chart.js 到 static 目录
cd web_dashboard/static
wget https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
```

然后修改 `index.html`：

```html
<!-- 从 CDN 改为本地 -->
<script src="/static/chart.umd.min.js"></script>
```

---

## 🎓 进阶使用

### 集成到现有系统

```python
# 在你的代码中集成 Dashboard
from web_dashboard import create_app
import uvicorn

app = create_app()

# 添加自定义路由
@app.get("/custom")
async def custom_endpoint():
    return {"status": "ok"}

# 启动
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "run_dashboard.py", "--host", "0.0.0.0"]
```

运行：

```bash
docker build -t crypto-dashboard .
docker run -p 8000:8000 crypto-dashboard
```

---

## 📞 技术支持

遇到问题？
1. 查看服务器日志
2. 检查浏览器控制台
3. 参考本文档的问题排查部分

---

祝你使用愉快！📊✨
