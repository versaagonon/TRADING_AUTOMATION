document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // CANVAS SYSTEM
    const canvas = document.getElementById('chart-canvas');
    const ctx = canvas.getContext('2d');
    const parent = document.getElementById('chart-parent');

    function resizeCanvas() {
        if (!parent) return;
        canvas.width = parent.clientWidth;
        canvas.height = parent.clientHeight;
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    function drawChart(history, markers) {
        if (history.length < 2) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const padding = 60;
        const width = canvas.width - padding * 2;
        const height = canvas.height - padding * 2;
        
        const minVal = Math.min(...history);
        const maxVal = Math.max(...history);
        const range = Math.max(maxVal - minVal, 10); 
        
        const getX = (i) => padding + (i / (history.length - 1)) * width;
        const getY = (val) => canvas.height - (padding + ((val - minVal) / range) * height);
        
        // Baseline
        if (10000 >= minVal && 10000 <= maxVal) {
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            ctx.moveTo(padding, getY(10000));
            ctx.lineTo(canvas.width - padding, getY(10000));
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Equity Line
        ctx.beginPath();
        ctx.lineWidth = 3;
        ctx.shadowBlur = 10;
        const isProfit = history[history.length - 1] >= 10000;
        ctx.strokeStyle = isProfit ? '#10b981' : '#ff4b5c';
        ctx.shadowColor = isProfit ? 'rgba(16, 185, 129, 0.5)' : 'rgba(255, 75, 92, 0.5)';
        ctx.moveTo(getX(0), getY(history[0]));
        for (let i = 1; i < history.length; i++) {
            ctx.lineTo(getX(i), getY(history[i]));
        }
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Gradient
        ctx.lineTo(getX(history.length-1), canvas.height - padding);
        ctx.lineTo(getX(0), canvas.height - padding);
        ctx.closePath();
        let gradient = ctx.createLinearGradient(0, padding, 0, canvas.height - padding);
        gradient.addColorStop(0, isProfit ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 75, 92, 0.15)');
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.fill();
    }

    // ULTRA-SYNC LISTENER
    socket.on('raw_update', (data) => {
        // Update SEMUA UI dalam satu detak agar sinkron
        const { price, pnl, balance, equity, equity_history, true_signal, sim_date, logs, pos, win_rate, ai_status } = data;

        document.getElementById('price').innerText = `$${price.toLocaleString()}`;
        document.getElementById('balance').innerText = `$${balance.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('sim-date').innerText = `HISTORICAL: ${sim_date}`;
        document.getElementById('true-signal').innerText = true_signal;
        document.getElementById('true-signal').style.color = true_signal === 'BUY' ? '#10b981' : (true_signal === 'SELL' ? '#ff4b5c' : '#94a3b8');
        document.getElementById('ai-status').innerText = ai_status;
        document.getElementById('win-rate').innerText = `${win_rate.toFixed(1)}%`;

        const pnlEl = document.getElementById('pnl');
        pnlEl.innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
        pnlEl.style.color = pnl >= 0 ? '#10b981' : '#ff4b5c';

        // Logs Sync
        const logContainer = document.getElementById('logs');
        logContainer.innerHTML = '';
        [...logs].reverse().forEach(log => {
            const div = document.createElement('div');
            div.className = 'log-item';
            div.innerText = log;
            logContainer.appendChild(div);
        });

        // Posisi UI
        if (pos) {
            document.getElementById('pos-type').innerText = pos.type;
            document.getElementById('pos-type').style.color = pos.type === 'BUY' ? '#10b981' : '#ff4b5c';
            document.getElementById('pos-entry').innerText = `$${pos.entry.toLocaleString()}`;
            document.getElementById('pos-size').innerText = pos.size.toFixed(4) + " BTC";
        } else {
            document.getElementById('pos-type').innerText = "NONE";
            document.getElementById('pos-type').style.color = '#94a3b8';
            document.getElementById('pos-entry').innerText = "-";
            document.getElementById('pos-size').innerText = "-";
        }

        drawChart(equity_history, data.markers);
    });

    const startBtn = document.getElementById('start-btn');
    startBtn.addEventListener('click', () => {
        socket.emit('start_engine', {});
        startBtn.innerText = "ENGINE RUNNING...";
        startBtn.style.background = "#94a3b8"; 
        startBtn.style.pointerEvents = "none";
    });
});
