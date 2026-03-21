const socket = io();

// CANVAS SYSTEM
const canvas = document.getElementById('chart-canvas');
const ctx = canvas.getContext('2d');
const parent = document.getElementById('chart-parent');

function resizeCanvas() {
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
    
    const minVal = Math.min(...history) * 0.9995;
    const maxVal = Math.max(...history) * 1.0005;
    const range = maxVal - minVal;
    
    const getX = (i) => padding + (i / (history.length - 1)) * width;
    const getY = (val) => canvas.height - (padding + ((val - minVal) / range) * height);
    
    // Draw Axis lines (Subtle)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(padding, getY(10000));
    ctx.lineTo(canvas.width - padding, getY(10000));
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw Line
    ctx.beginPath();
    ctx.lineWidth = 3;
    ctx.strokeStyle = history[history.length - 1] >= 10000 ? '#10b981' : '#ff4b5c';
    ctx.moveTo(getX(0), getY(history[0]));
    
    for (let i = 1; i < history.length; i++) {
        ctx.lineTo(getX(i), getY(history[i]));
    }
    ctx.stroke();

    // Draw Fill
    ctx.lineTo(getX(history.length-1), canvas.height - padding);
    ctx.lineTo(getX(0), canvas.height - padding);
    ctx.closePath();
    let gradient = ctx.createLinearGradient(0, padding, 0, canvas.height - padding);
    gradient.addColorStop(0, history[history.length - 1] >= 10000 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 75, 92, 0.2)');
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw Markers
    const startIdx = history.length - (history.length); // Adjusted if we slice in future
    const currentFullCount = history.length; 
    
    // Simple logic to find relative index for visible history
    // Since we only send last 500, we need to match it.
    // In this v5.0, history is the same as history on screen.
    
    markers.forEach(m => {
        // Find if this marker's 'time' (sim_index) is within the latest X points
        // History contains 500 points. We need the relative index.
        // This part needs to match sim_index vs slice
    });
}

socket.on('raw_update', (data) => {
    const { price, pnl, balance, equity, equity_history, true_signal, sim_date } = data;

    // Update UI
    document.getElementById('price').innerText = `$${price.toLocaleString()}`;
    document.getElementById('balance').innerText = `$${balance.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById('sim-date').innerText = `HISTORICAL: ${sim_date}`;
    document.getElementById('true-signal').innerText = true_signal;
    document.getElementById('true-signal').style.color = true_signal === 'BUY' ? '#10b981' : (true_signal === 'SELL' ? '#ff4b5c' : '#94a3b8');
    
    const pnlEl = document.getElementById('pnl');
    pnlEl.innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
    pnlEl.style.color = pnl >= 0 ? '#10b981' : '#ff4b5c';

    // Draw
    drawChart(equity_history, data.markers);
});

socket.on('state_update', (state) => {
    document.getElementById('ai-status').innerText = state.ai_status;
    const winRate = state.signals_processed > 0 ? (state.correct_signals / state.signals_processed * 100).toFixed(1) : 0;
    document.getElementById('win-rate').innerText = `${winRate}%`;
    
    if (state.position) {
        document.getElementById('pos-type').innerText = state.position.type;
        document.getElementById('pos-type').style.color = state.position.type === 'BUY' ? '#10b981' : '#ff4b5c';
        document.getElementById('pos-entry').innerText = `$${state.position.entry.toLocaleString()}`;
        document.getElementById('pos-size').innerText = state.position.size.toFixed(4) + " BTC";
    } else {
        document.getElementById('pos-type').innerText = "NONE";
        document.getElementById('pos-entry').innerText = "-";
        document.getElementById('pos-size').innerText = "-";
    }

    const logContainer = document.getElementById('logs');
    logContainer.innerHTML = '';
    [...state.logs].reverse().forEach(log => {
        const div = document.createElement('div');
        div.className = 'log-item';
        div.innerText = log;
        logContainer.appendChild(div);
    });
});

document.getElementById('start-btn').addEventListener('click', () => {
    socket.emit('start_engine', {});
    const btn = document.getElementById('start-btn');
    btn.innerText = "ENGINE RUNNING...";
    btn.style.background = "#94a3b8"; 
    btn.style.pointerEvents = "none";
});
