// WebSocket 连接
let ws = null;
let reconnectInterval = null;
let profitChart = null;
let profitData = [];

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    initProfitChart();
    fetchInitialData();
});

// WebSocket 连接
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
        startHeartbeat();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
        stopHeartbeat();
        // 5秒后重连
        setTimeout(initWebSocket, 5000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// 心跳检测
let heartbeatInterval = null;

function startHeartbeat() {
    heartbeatInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    }, 30000); // 30秒一次
}

function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
}

// 处理 WebSocket 消息
function handleWebSocketMessage(data) {
    if (data.type === 'arbitrage_update') {
        updatePrices(data.data.prices);
        updateArbitrageOpportunities(data.data.opportunities);
        updateStatistics(data.data.statistics);
        updateLastUpdateTime();
    }
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');

    if (connected) {
        statusDot.classList.remove('offline');
        statusDot.classList.add('online');
        statusText.textContent = '在线';
    } else {
        statusDot.classList.remove('online');
        statusDot.classList.add('offline');
        statusText.textContent = '离线';
    }
}

// 获取初始数据
async function fetchInitialData() {
    try {
        // 获取价格
        const pricesRes = await fetch('/api/prices');
        const pricesData = await pricesRes.json();
        updatePrices(pricesData.prices);

        // 获取套利机会
        const oppoRes = await fetch('/api/arbitrage/opportunities');
        const oppoData = await oppoRes.json();
        updateArbitrageOpportunities(oppoData.opportunities);

        // 获取统计
        const statsRes = await fetch('/api/statistics');
        const statsData = await statsRes.json();
        updateStatistics(statsData.statistics);

        // 获取提醒历史
        const alertsRes = await fetch('/api/alerts/history');
        const alertsData = await alertsRes.json();
        updateAlertHistory(alertsData.alerts);

    } catch (e) {
        console.error('Error fetching initial data:', e);
    }
}

// 更新价格显示
function updatePrices(prices) {
    const priceGrid = document.getElementById('priceGrid');

    if (!prices || Object.keys(prices).length === 0) {
        priceGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⏳</div>
                <div class="empty-text">正在加载价格数据...</div>
            </div>
        `;
        return;
    }

    let html = '';
    for (const [exchange, tickers] of Object.entries(prices)) {
        for (const [ticker, price] of Object.entries(tickers)) {
            const changePercent = ((Math.random() - 0.5) * 2).toFixed(2); // 模拟涨跌幅
            const changeClass = changePercent >= 0 ? 'positive' : 'negative';
            const changeSign = changePercent >= 0 ? '+' : '';

            html += `
                <div class="price-card">
                    <div class="price-info">
                        <div class="price-ticker">${ticker}</div>
                        <div class="price-exchange">${exchange.toUpperCase()}</div>
                    </div>
                    <div class="price-value">
                        <div class="price-amount">$${parseFloat(price).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                        <div class="price-change ${changeClass}">${changeSign}${changePercent}%</div>
                    </div>
                </div>
            `;
        }
    }

    priceGrid.innerHTML = html;
}

// 更新套利机会
function updateArbitrageOpportunities(opportunities) {
    const arbitrageList = document.getElementById('arbitrageList');
    const oppoBadge = document.getElementById('oppoBadge');
    const oppoCount = document.getElementById('opportunitiesCount');

    oppoBadge.textContent = opportunities.length;
    oppoCount.textContent = opportunities.length;

    if (!opportunities || opportunities.length === 0) {
        arbitrageList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <div class="empty-text">暂无套利机会</div>
            </div>
        `;
        return;
    }

    let html = '';
    opportunities.forEach(opp => {
        const scoreClass = opp.score >= 75 ? 'high-score' : (opp.score >= 50 ? 'medium-score' : 'low-score');

        html += `
            <div class="opportunity-card ${scoreClass}">
                <div class="opportunity-header">
                    <div class="opportunity-ticker">${opp.ticker}</div>
                    <div class="opportunity-score">${opp.score.toFixed(1)}</div>
                </div>
                <div class="opportunity-route">
                    <span>买入@${opp.buy_exchange.toUpperCase()}</span>
                    <span>→</span>
                    <span>卖出@${opp.sell_exchange.toUpperCase()}</span>
                </div>
                <div class="opportunity-stats">
                    <div class="opportunity-stat">
                        <div class="opportunity-stat-label">价差</div>
                        <div class="opportunity-stat-value">$${opp.spread.toFixed(2)} (${opp.spread_percent.toFixed(2)}%)</div>
                    </div>
                    <div class="opportunity-stat">
                        <div class="opportunity-stat-label">预估利润</div>
                        <div class="opportunity-stat-value positive">$${opp.estimated_profit.toFixed(2)} (${opp.profit_percent.toFixed(2)}%)</div>
                    </div>
                    <div class="opportunity-stat">
                        <div class="opportunity-stat-label">买入价</div>
                        <div class="opportunity-stat-value">$${opp.buy_price.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                    </div>
                    <div class="opportunity-stat">
                        <div class="opportunity-stat-label">卖出价</div>
                        <div class="opportunity-stat-value">$${opp.sell_price.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                    </div>
                </div>
            </div>
        `;
    });

    arbitrageList.innerHTML = html;
}

// 更新统计数据
function updateStatistics(stats) {
    if (!stats) return;

    document.getElementById('totalProfit').textContent =
        `$${(stats.total_profit || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    document.getElementById('totalTrades').textContent = stats.total_trades || 0;

    const successRate = stats.success_rate || ((stats.total_trades > 0) ? 95 : 0);
    document.getElementById('successRate').textContent = `${successRate.toFixed(1)}%`;

    document.getElementById('alertsTriggered').textContent = stats.alerts_triggered || 0;

    // 更新利润图表
    if (stats.total_profit) {
        updateProfitChart(stats.total_profit);
    }
}

// 更新提醒历史
function updateAlertHistory(alerts) {
    const alertsList = document.getElementById('alertsList');

    if (!alerts || alerts.length === 0) {
        alertsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔕</div>
                <div class="empty-text">暂无提醒记录</div>
            </div>
        `;
        return;
    }

    let html = '';
    alerts.slice(-10).reverse().forEach(alert => {
        html += `
            <div class="alert-item">
                <div class="alert-time">${new Date(alert.timestamp).toLocaleString('zh-CN')}</div>
                <div class="alert-message">${alert.message || alert.trigger_reason}</div>
            </div>
        `;
    });

    alertsList.innerHTML = html;
}

// 初始化利润图表
function initProfitChart() {
    const ctx = document.getElementById('profitChart');
    if (!ctx) return;

    profitChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '累计利润 ($)',
                data: [],
                borderColor: '#4ade80',
                backgroundColor: 'rgba(74, 222, 128, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#2a2a3e'
                    },
                    ticks: {
                        color: '#a0a0a0'
                    }
                },
                x: {
                    grid: {
                        color: '#2a2a3e'
                    },
                    ticks: {
                        color: '#a0a0a0'
                    }
                }
            }
        }
    });
}

// 更新利润图表
function updateProfitChart(profit) {
    if (!profitChart) return;

    const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

    profitChart.data.labels.push(now);
    profitChart.data.datasets[0].data.push(profit);

    // 只保留最近20个数据点
    if (profitChart.data.labels.length > 20) {
        profitChart.data.labels.shift();
        profitChart.data.datasets[0].data.shift();
    }

    profitChart.update('none'); // 无动画更新
}

// 更新最后更新时间
function updateLastUpdateTime() {
    const now = new Date().toLocaleTimeString('zh-CN');
    document.getElementById('lastUpdate').textContent = now;
}

// 刷新价格
async function refreshPrices() {
    try {
        const res = await fetch('/api/prices');
        const data = await res.json();
        updatePrices(data.prices);
        updateLastUpdateTime();
    } catch (e) {
        console.error('Error refreshing prices:', e);
    }
}
