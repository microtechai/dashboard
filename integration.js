// ═══════════════════════════════════════════════════════════
// DASHBOARD INTEGRATION SCRIPT
// Dashboard microtechai.es - Integración de nuevas funcionalidades
// ═══════════════════════════════════════════════════════════

// Check if Three.js is loaded
function checkThree() {
    return new Promise((resolve) => {
        if (typeof THREE !== 'undefined') {
            resolve(true);
        } else {
            console.error('❌ Three.js no está cargado');
            resolve(false);
        }
    });
}

// The main scene owns fire creation and updates; never create a second group.
function loadFire() {
    return Boolean(window.dashboardFireController);
}

// Load voice system
function loadVoice() {
    try {
        // El archivo voice/speech.js se carga como script
        // Esperar a que se inicie
        setTimeout(() => {
            if (window.voiceSystem) {
                console.log('✅ Sistema de voz cargado');
            } else {
                console.warn('⚠️  Voice system no encontrado - Web Speech API no soportado');
            }
        }, 1000);
        return true;
    } catch (e) {
        console.error('❌ Error cargando voz:', e);
        return false;
    }
}

// Load task executor UI
function loadTaskExecutor() {
    if (document.getElementById('task-executor-panel')) return true;
    try {
        // Crear panel de executor
        const panel = document.createElement('div');
        panel.id = 'task-executor-panel';
        panel.innerHTML = `
            <div id="executor-window" style="
                position: fixed;
                bottom: 20px;
                left: 20px;
                width: min(300px, calc(100vw - 40px));
                background: rgba(10, 15, 30, 0.95);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(74, 158, 255, 0.3);
                border-radius: 12px;
                padding: 16px;
                z-index: 1000;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            ">
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                ">
                    <h3 style="
                        font-size: 11px;
                        font-weight: 600;
                        color: #4a9eff;
                        letter-spacing: 1px;
                        text-transform: uppercase;
                    ">⚙️ Task Executor</h3>
                    <button id="toggle-executor" type="button" aria-label="Minimizar Task Executor" title="Minimizar Task Executor" aria-controls="executor-body" aria-expanded="true" style="
                        background: none;
                        border: none;
                        color: #667;
                        font-size: 18px;
                        cursor: pointer;
                    ">−</button>
                </div>
                <div id="executor-body">
                <div id="executor-commands" style="
                    max-height: 200px;
                    overflow-y: auto;
                    margin-bottom: 12px;
                "></div>
                <textarea id="executor-input" placeholder="O ingresa comando manual..." style="
                    width: 100%;
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(74, 158, 255, 0.2);
                    border-radius: 6px;
                    color: #c0d0ff;
                    padding: 8px;
                    font-size: 10px;
                    font-family: 'JetBrains Mono', monospace;
                    resize: none;
                    height: 60px;
                "></textarea>
                <button id="executor-run" style="
                    width: 100%;
                    padding: 8px;
                    background: rgba(74, 158, 255, 0.2);
                    border: 1px solid rgba(74, 158, 255, 0.4);
                    border-radius: 6px;
                    color: #4a9eff;
                    font-size: 10px;
                    cursor: pointer;
                    margin-top: 8px;
                ">🚀 Ejecutar</button>
                <div id="executor-output" style="
                    margin-top: 10px;
                    padding: 8px;
                    background: rgba(0, 0, 0, 0.5);
                    border-radius: 6px;
                    font-size: 9px;
                    font-family: 'JetBrains Mono', monospace;
                    color: #8ab4ff;
                    max-height: 100px;
                    overflow-y: auto;
                "></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(panel);
        const toggle = panel.querySelector('#toggle-executor');
        const body = panel.querySelector('#executor-body');
        const box = panel.querySelector('#executor-window');
        const desktopStorageKey = 'jarvis.executor.minimized';
        const mobileLayout = window.matchMedia('(max-width: 760px)');
        const storageKey = () => mobileLayout.matches ? 'jarvis.executor.mobile.minimized' : desktopStorageKey;
        function setMinimized(minimized) {
            body.hidden = minimized;
            toggle.textContent = minimized ? '+' : '−';
            const label = minimized ? 'Restaurar Task Executor' : 'Minimizar Task Executor';
            toggle.setAttribute('aria-label', label);
            toggle.title = label;
            toggle.setAttribute('aria-expanded', String(!minimized));
            box.style.width = minimized ? 'min(210px, calc(100vw - 40px))' : 'min(300px, calc(100vw - 40px))';
            toggle.parentElement.style.marginBottom = minimized ? '0' : '12px';
            try { localStorage.setItem(storageKey(), String(minimized)); } catch (_) {}
        }
        function restoreLayout() {
            let minimized = mobileLayout.matches;
            try {
                const saved = localStorage.getItem(storageKey());
                if (saved !== null) minimized = saved === 'true';
            } catch (_) {}
            setMinimized(minimized);
        }
        restoreLayout();
        mobileLayout.addEventListener('change', restoreLayout);
        toggle.addEventListener('click', () => setMinimized(!body.hidden));
        console.log('✅ Task Executor UI cargado');
        
        // Cargar comandos
        fetch('/api/commands')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const container = document.getElementById('executor-commands');
                    container.innerHTML = data.commands.map(cmd => `
                        <button data-command="${cmd.command}" style="
                            width: 100%;
                            padding: 6px;
                            margin-bottom: 4px;
                            background: rgba(74, 158, 255, 0.08);
                            border: 1px solid rgba(74, 158, 255, 0.2);
                            border-radius: 4px;
                            color: #667;
                            font-size: 9px;
                            cursor: pointer;
                            text-align: left;
                        ">
                            ${cmd.description}
                        </button>
                    `).join('');
                    
                    // Add event listeners to buttons
                    document.querySelectorAll('#executor-commands button').forEach(btn => {
                        btn.addEventListener('click', () => {
                            document.getElementById('executor-input').value = btn.dataset.command;
                            runCommand(btn.dataset.command);
                        });
                    });
                }
            })
            .catch(e => console.warn('⚠️  No se pudo cargar comandos del API'));
        
        // Run command handler
        document.getElementById('executor-run').addEventListener('click', () => {
            const cmd = document.getElementById('executor-input').value;
            if (cmd) runCommand(cmd);
        });
        
        return true;
    } catch (e) {
        console.error('❌ Error cargando Task Executor:', e);
        return false;
    }
}

async function runCommand(command) {
    const output = document.getElementById('executor-output');
    output.textContent = ' ejecutando...';
    
    try {
        const response = await fetch('/api/exec', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command, user: 'dashboard-user' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            output.innerHTML = `<span style="color:#4ade80">✅ Success (code: ${data.result.exit_code})</span>\n\n${data.result.stdout}`;
        } else {
            output.innerHTML = `<span style="color:#ef4444">❌ Error</span>\n${data.result.stderr}`;
        }
    } catch (e) {
        output.innerHTML = `<span style="color:#facc15">⚠️  API no disponible - usando simulación</span>\n${command} (simulado)`;
    }
}

// Main initialization
async function initDashboard() {
    console.log('🚀 Inicializando dashboard mejorado...');
    
    const threeReady = await checkThree();
    
    if (threeReady) {
        await loadFire();
    }
    
    loadVoice();
    loadTaskExecutor();
    
    console.log('✅ Dashboard mejorado inicializado');
}

// Exponer función global
window.initDashboard = initDashboard;

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
