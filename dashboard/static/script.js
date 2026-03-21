// Final Consolidated script.js Logic v22.1 (Sync Fixed)
const socket = io();
let isRunning = false;

// Socket Listener: Single Stream Update
socket.on('raw_update', (data) => {
    // 1. DATA RESET HANDLING
    if (data.reset) {
        const logBox = document.getElementById('logs');
        if (logBox) logBox.innerHTML = '';
        drawChart([], []);
        isRunning = false;
    }

    // 2. METRICS UPDATES
    if (data.price) {
        if (document.getElementById('price')) document.getElementById('price').innerText = "$" + data.price.toLocaleString();
        if (document.getElementById('pnl')) {
            document.getElementById('pnl').innerText = (data.pnl >= 0 ? "+" : "") + "$" + data.pnl.toLocaleString();
            document.getElementById('pnl').style.color = data.pnl >= 0 ? '#64ffda' : '#ff4b5c';
        }
        // Di index.html ID-nya adalah 'balance' untuk Equity (Total)
        if (document.getElementById('balance')) document.getElementById('balance').innerText = "$" + data.equity.toLocaleString();
        if (document.getElementById('win-rate')) document.getElementById('win-rate').innerText = data.win_rate ? data.win_rate.toFixed(1) + "%" : "0%";
    }

    if (data.ai_status && document.getElementById('ai-status')) {
        document.getElementById('ai-status').innerText = data.ai_status;
    }

    if (data.sim_date && document.getElementById('sim-date')) {
        document.getElementById('sim-date').innerText = "HISTORICAL: " + data.sim_date;
    }

    if (data.true_signal && document.getElementById('true-signal')) {
        document.getElementById('true-signal').innerText = data.true_signal;
        // Warna dinamis untuk signal
        const color = data.true_signal === 'BUY' ? '#64ffda' : (data.true_signal === 'SELL' ? '#ff4b5c' : '#94a3b8');
        document.getElementById('true-signal').style.color = color;
    }

    // 3. LOG UPDATES
    if (data.logs) {
        const logBox = document.getElementById('logs');
        if (logBox) {
            logBox.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
            logBox.scrollTop = logBox.scrollHeight;
        }
    }

    // 4. POSITION UPDATES
    if (data.pos) {
        const pos = data.pos;
        if (document.getElementById('pos-type')) {
            document.getElementById('pos-type').innerText = pos.type;
            document.getElementById('pos-type').style.color = pos.type === 'LONG' ? '#64ffda' : '#ff4b5c';
        }
        if (document.getElementById('pos-entry')) document.getElementById('pos-entry').innerText = "$" + pos.entry.toLocaleString();
        if (document.getElementById('pos-size')) document.getElementById('pos-size').innerText = pos.size.toFixed(4) + " BTC";
    } else {
        if (document.getElementById('pos-type')) {
            document.getElementById('pos-type').innerText = "NONE";
            document.getElementById('pos-type').style.color = '#94a3b8';
        }
        if (document.getElementById('pos-entry')) document.getElementById('pos-entry').innerText = "-";
        if (document.getElementById('pos-size')) document.getElementById('pos-size').innerText = "-";
    }

    // 5. CHART UPDATES
    if (data.equity_history) {
        drawChart(data.equity_history, data.markers, data.current_idx);
    }

    // 6. TOGGLE BUTTON & UI STATE
    isRunning = (data.engine_running !== undefined) ? data.engine_running : isRunning;
    const startBtn = document.getElementById('start-btn');
    if (!startBtn) return;

    if (!isRunning || (data.ai_status && data.ai_status.includes('FINISHED'))) {
        startBtn.innerText = "START TRADING ENGINE";
        startBtn.style.background = "#64ffda";
        startBtn.style.color = "#020617";
        startBtn.style.boxShadow = "0 0 15px rgba(100, 255, 218, 0.3)";
        startBtn.style.pointerEvents = "auto";
        document.getElementById('initial-modal').disabled = false;
        document.getElementById('strategy-select').disabled = false;
        document.getElementById('speed-select').disabled = false;
        isRunning = false;
    } else {
        startBtn.innerText = "STOP TRADING (FORCE)";
        startBtn.style.background = "#ff4b5c";
        startBtn.style.color = "#fff";
        startBtn.style.boxShadow = "0 0 15px rgba(255, 75, 92, 0.3)";
        startBtn.style.pointerEvents = "auto";
        document.getElementById('initial-modal').disabled = true;
        document.getElementById('strategy-select').disabled = true;
        document.getElementById('speed-select').disabled = true;
        isRunning = true;
    }
});

function drawChart(history, markers, currentIdx) {
    // ID di index.html adalah 'chart-canvas'
    const canvas = document.getElementById('chart-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.parentElement.clientWidth;
    const h = canvas.height = canvas.parentElement.clientHeight;

    ctx.clearRect(0, 0, w, h);
    if (!history || history.length < 2) return;

    const min = Math.min(...history) * 0.9995;
    const max = Math.max(...history) * 1.0005;
    const range = max - min;

    // Gradient Background
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(100, 255, 218, 0.1)');
    grad.addColorStop(1, 'transparent');

    ctx.beginPath();
    ctx.moveTo(0, h - ((history[0] - min) / range) * h);
    for (let i = 1; i < history.length; i++) {
        const x = (i / (history.length - 1)) * w;
        const y = h - ((history[i] - min) / range) * h;
        ctx.lineTo(x, y);
    }

    ctx.strokeStyle = '#64ffda';
    ctx.lineWidth = 2;
    ctx.stroke();
    // Fill background
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.fillStyle = grad;
    ctx.fill();

    // Draw Markers
    if (markers && markers.length > 0 && currentIdx !== undefined) {
        markers.forEach(m => {
            const windowSize = 500;
            const startIdx = Math.max(0, currentIdx - windowSize + 1);
            const relativeIdx = Math.floor(m.time - startIdx);

            if (relativeIdx >= 0 && relativeIdx < history.length) {
                const x = (relativeIdx / (history.length - 1)) * w;
                const equityVal = history[relativeIdx];
                const y = h - ((equityVal - min) / range) * h;

                ctx.save();
                ctx.shadowBlur = 15;

                if (m.type === 'BUY') {
                    // Triangle Up (Green) - REFINED SIZE
                    ctx.fillStyle = '#64ffda';
                    ctx.shadowColor = '#64ffda';
                    ctx.beginPath();
                    ctx.moveTo(x, y - 10);
                    ctx.lineTo(x - 8, y + 6);
                    ctx.lineTo(x + 8, y + 6);
                    ctx.closePath();
                    ctx.fill();
                } else if (m.type === 'SELL') {
                    // Triangle Down (Red) - REFINED SIZE
                    ctx.fillStyle = '#ff4b5c';
                    ctx.shadowColor = '#ff4b5c';
                    ctx.beginPath();
                    ctx.moveTo(x, y + 10);
                    ctx.lineTo(x - 8, y - 6);
                    ctx.lineTo(x + 8, y - 6);
                    ctx.closePath();
                    ctx.fill();
                } else {
                    // Diamond (Gold)
                    ctx.fillStyle = '#facc15';
                    ctx.shadowColor = '#facc15';
                    ctx.beginPath();
                    ctx.moveTo(x, y - 8);
                    ctx.lineTo(x + 8, y);
                    ctx.lineTo(x, y + 8);
                    ctx.lineTo(x - 8, y);
                    ctx.closePath();
                    ctx.fill();
                }
                ctx.restore();
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-btn');
    const pdfBtn = document.getElementById('pdf-btn');

    if (startBtn) {
        startBtn.addEventListener('click', () => {
            if (!isRunning) {
                const modal = document.getElementById('initial-modal').value || 100;
                const strategy = document.getElementById('strategy-select').value || 'geminipro';
                const speed = document.getElementById('speed-select').value || 'normal';
                socket.emit('start_engine', { initial_balance: parseFloat(modal), strategy, speed });
            } else {
                socket.emit('stop_engine');
            }
        });
    }

    if (pdfBtn) {
        pdfBtn.addEventListener('click', () => {
            fetch('/generate_report')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') alert('PDF Report Generated: ' + data.filename);
                    else alert('Error: ' + data.message);
                });
        });
    }
});
