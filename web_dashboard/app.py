"""
Web Dashboard for Price Monitoring and Arbitrage
实时监控仪表盘 - FastAPI 后端
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import asyncio
import json
from datetime import datetime
from decimal import Decimal
import logging

from arbitrage_engine import ArbitrageEngine
from price_alert.alert_manager import AlertManager
from price_alert.alert_config import AlertConfig


logger = logging.getLogger(__name__)


class WebDashboard:
    """Web Dashboard 管理器"""

    def __init__(self):
        self.app = FastAPI(title="Crypto Trading Dashboard")

        # CORS 配置
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # WebSocket 连接管理
        self.active_connections: List[WebSocket] = []

        # 数据缓存
        self.latest_prices: Dict[str, Dict[str, Any]] = {}
        self.arbitrage_opportunities: List[Dict] = []
        self.alert_history: List[Dict] = []
        self.statistics: Dict[str, Any] = {
            'total_profit': 0,
            'total_trades': 0,
            'success_rate': 0,
            'alerts_triggered': 0,
        }

        # 后台任务
        self.arbitrage_engine: ArbitrageEngine = None
        self.alert_manager: AlertManager = None

        # 设置路由
        self._setup_routes()

    def _setup_routes(self):
        """设置 API 路由"""

        # 挂载静态文件
        from pathlib import Path
        from fastapi.responses import RedirectResponse

        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @self.app.get("/")
        async def root():
            """主页 - 重定向到仪表盘"""
            return RedirectResponse(url="/dashboard")

        @self.app.get("/dashboard")
        async def dashboard():
            """仪表盘页面"""
            html_file = Path(__file__).parent / "static" / "index.html"
            if html_file.exists():
                return HTMLResponse(html_file.read_text())
            return {"error": "Dashboard HTML not found"}

        @self.app.get("/api/prices")
        async def get_prices():
            """获取最新价格"""
            return {
                "timestamp": datetime.now().isoformat(),
                "prices": self.latest_prices
            }

        @self.app.get("/api/arbitrage/opportunities")
        async def get_arbitrage_opportunities():
            """获取套利机会"""
            return {
                "timestamp": datetime.now().isoformat(),
                "opportunities": self.arbitrage_opportunities,
                "count": len(self.arbitrage_opportunities)
            }

        @self.app.get("/api/alerts/history")
        async def get_alert_history(limit: int = 50):
            """获取提醒历史"""
            return {
                "timestamp": datetime.now().isoformat(),
                "alerts": self.alert_history[-limit:],
                "count": len(self.alert_history)
            }

        @self.app.get("/api/statistics")
        async def get_statistics():
            """获取统计数据"""
            return {
                "timestamp": datetime.now().isoformat(),
                "statistics": self.statistics
            }

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket 实时数据推送"""
            await self.connect(websocket)
            try:
                while True:
                    # 保持连接并发送心跳
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text("pong")
            except WebSocketDisconnect:
                self.disconnect(websocket)

        @self.app.post("/api/arbitrage/start")
        async def start_arbitrage(config: Dict[str, Any]):
            """启动套利引擎"""
            try:
                self.arbitrage_engine = ArbitrageEngine(config)
                asyncio.create_task(self._run_arbitrage_engine())
                return {"status": "started", "message": "Arbitrage engine started"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        @self.app.post("/api/arbitrage/stop")
        async def stop_arbitrage():
            """停止套利引擎"""
            if self.arbitrage_engine:
                await self.arbitrage_engine.cleanup()
                self.arbitrage_engine = None
                return {"status": "stopped", "message": "Arbitrage engine stopped"}
            return {"status": "error", "message": "No running engine"}

        @self.app.post("/api/alerts/start")
        async def start_alerts(config: Dict[str, Any]):
            """启动价格提醒"""
            try:
                alert_config = AlertConfig.from_dict(config)
                self.alert_manager = AlertManager(alert_config)
                asyncio.create_task(self._run_alert_manager())
                return {"status": "started", "message": "Alert manager started"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    async def connect(self, websocket: WebSocket):
        """新的 WebSocket 连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开 WebSocket 连接"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            try:
                self.disconnect(connection)
            except:
                pass

    async def _run_arbitrage_engine(self):
        """运行套利引擎（后台任务）"""
        try:
            await self.arbitrage_engine.initialize()

            while self.arbitrage_engine:
                # 获取价格
                await self.arbitrage_engine.fetch_all_prices()

                # 更新价格缓存
                self.latest_prices = self.arbitrage_engine.price_cache

                # 发现套利机会
                opportunities = self.arbitrage_engine.find_arbitrage_opportunities()

                # 转换为可序列化格式
                self.arbitrage_opportunities = [
                    {
                        'ticker': opp.ticker,
                        'buy_exchange': opp.buy_exchange,
                        'sell_exchange': opp.sell_exchange,
                        'buy_price': float(opp.buy_price),
                        'sell_price': float(opp.sell_price),
                        'spread': float(opp.spread),
                        'spread_percent': float(opp.spread_percent),
                        'estimated_profit': float(opp.estimated_profit),
                        'profit_percent': float(opp.profit_percent),
                        'score': float(opp.score),
                        'timestamp': opp.timestamp.isoformat()
                    }
                    for opp in opportunities[:10]  # 只保留前10个
                ]

                # 更新统计
                self.statistics.update({
                    'total_opportunities': self.arbitrage_engine.opportunities_found,
                    'total_trades': self.arbitrage_engine.trades_executed,
                    'total_profit': float(self.arbitrage_engine.total_profit),
                })

                # 广播更新
                await self.broadcast({
                    'type': 'arbitrage_update',
                    'data': {
                        'prices': {k: {tk: float(tv) for tk, tv in v.items()}
                                  for k, v in self.latest_prices.items()},
                        'opportunities': self.arbitrage_opportunities,
                        'statistics': self.statistics
                    }
                })

                await asyncio.sleep(self.arbitrage_engine.config.get('check_interval', 5))

        except Exception as e:
            logger.error(f"Error in arbitrage engine: {e}", exc_info=True)

    async def _run_alert_manager(self):
        """运行价格提醒管理器（后台任务）"""
        # TODO: 实现价格提醒的后台运行和数据推送
        pass

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """启动 Web 服务器"""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)


# 主函数
def create_app():
    """创建 FastAPI 应用"""
    dashboard = WebDashboard()
    return dashboard.app


if __name__ == "__main__":
    import sys
    sys.path.append('..')

    dashboard = WebDashboard()

    print("\n" + "=" * 80)
    print("🚀 Crypto Trading Dashboard")
    print("=" * 80)
    print(f"📍 Server: http://localhost:8000")
    print(f"📊 Dashboard: http://localhost:8000/dashboard")
    print(f"📡 WebSocket: ws://localhost:8000/ws")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print("=" * 80 + "\n")

    dashboard.run()
