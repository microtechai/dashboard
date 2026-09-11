// ═══════════════════════════════════════════════════════════
// VOICE SYSTEM - Web Speech API
// Dashboard microtechai.es - Fase 2: Sistema de Voz
// ═══════════════════════════════════════════════════════════

class VoiceSystem {
    constructor() {
        this.speechRecognition = null;
        this.speechSynthesis = window.speechSynthesis;
        this.isListening = false;
        this.commands = {};
        this.commandHistory = [];
        this.ui = {
            micButton: null,
            micIcon: null,
            waveform: null,
            output: null,
            statusText: null
        };
        
        this.init();
    }
    
    init() {
        // Check browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.warn('⚠️  Web Speech API not supported in this browser');
            this.isSupported = false;
            return;
        }
        
        this.isSupported = true;
        this.speechRecognition = new SpeechRecognition();
        this.speechRecognition.continuous = false;
        this.speechRecognition.lang = 'es-ES';
        this.speechRecognition.interimResults = false;
        
        // Setup event handlers
        this.speechRecognition.onstart = () => this.onListenStart();
        this.speechRecognition.onend = () => this.onListenEnd();
        this.speechRecognition.onresult = (event) => this.onResult(event);
        this.speechRecognition.onerror = (event) => this.onError(event);
        
        this.loadCommands();
    }
    
    loadCommands() {
        // Default commands (Spanish)
        this.commands = {
            'reiniciar nginx': {
                command: 'nginx-restart',
                description: 'Reiniciar servidor nginx',
                response: 'Reiniciando nginx...'
            },
            'ver logs': {
                command: 'view-logs',
                description: 'Ver últimos logs de nginx',
                response: 'Mostrando logs...'
            },
            'health check': {
                command: 'health-check',
                description: 'Ver estado del sistema',
                response: 'Verificando estado del sistema...'
            },
            'reiniciar sistema': {
                command: 'restart',
                description: 'Reiniciar dashboard',
                response: 'Reiniciando dashboard...'
            },
            'ayuda': {
                command: 'help',
                description: 'Mostrar comandos disponibles',
                response: 'Comandos disponibles: reiniciar nginx, ver logs, health check, ayuda'
            }
        };
    }
    
    // === LISTENING CONTROL ===
    
    startListening() {
        if (!this.isSupported) return;
        
        try {
            this.speechRecognition.start();
            this.isListening = true;
            this.updateUIState(true);
        } catch (e) {
            console.error('Error starting speech recognition:', e);
            this.onListenEnd();
        }
    }
    
    stopListening() {
        if (this.isListening && this.speechRecognition) {
            this.speechRecognition.stop();
            this.isListening = false;
            this.updateUIState(false);
        }
    }
    
    // === EVENT HANDLERS ===
    
    onListenStart() {
        console.log('🎤 Micrófono activo - Escuchando...');
        this.updateUIState(true);
        this.speak('Estoy escuchando');
    }
    
    onListenEnd() {
        this.isListening = false;
        this.updateUIState(false);
    }
    
    onResult(event) {
        const transcript = event.results[0][0].transcript;
        console.log('🗣️  Escuchado:', transcript);
        
        this.processCommand(transcript);
    }
    
    onError(event) {
        console.error('🎤 Error en reconocimiento de voz:', event.error);
        this.speak('Lo siento, no pude entender. Intenta de nuevo.');
        this.isListening = false;
        this.updateUIState(false);
    }
    
    // === COMMAND PROCESSING ===
    
    processCommand(transcript) {
        // Normalize transcript
        const normalized = transcript.toLowerCase().trim();
        
        // Find matching command
        let matchedCommand = null;
        let bestMatchScore = 0;
        
        for (const [keyword, cmd] of Object.entries(this.commands)) {
            const score = this.similarity(normalized, keyword);
            if (score > bestMatchScore && score > 0.6) {
                bestMatchScore = score;
                matchedCommand = cmd;
            }
        }
        
        if (matchedCommand) {
            this.executeCommand(matchedCommand);
        } else {
            this.speak('No reconozco ese comando. Di "ayuda" para ver los comandos disponibles.');
        }
        
        this.commandHistory.push({
            timestamp: Date.now(),
            input: transcript,
            command: matchedCommand?.command || null,
            response: matchedCommand?.response || null
        });
    }
    
    executeCommand(command) {
        console.log('⚙️  Ejecutando:', command.description);
        this.speak(command.response);
        
        // Execute based on command type
        switch (command.command) {
            case 'nginx-restart':
                this.triggerEvent('nginx-restart');
                break;
            case 'view-logs':
                this.triggerEvent('view-logs');
                break;
            case 'health-check':
                this.triggerEvent('health-check');
                break;
            case 'restart':
                this.triggerEvent('dashboard-restart');
                break;
            case 'help':
                this.speak('Comandos disponibles: reiniciar nginx, ver logs, health check.');
                break;
        }
    }
    
    triggerEvent(type) {
        // Dispatch custom event for other parts of the app
        const event = new CustomEvent('voice-command', { 
            detail: { type, command: type }
        });
        window.dispatchEvent(event);
    }
    
    // === TEXT TO SPEECH ===
    
    speak(text, lang = 'es-ES') {
        if (!this.speechSynthesis) return;
        
        // Cancel any current speech
        this.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = lang;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        
        // Try to find a Spanish voice
        const voices = this.speechSynthesis.getVoices();
        const spanishVoice = voices.find(v => v.lang.startsWith('es'));
        if (spanishVoice) {
            utterance.voice = spanishVoice;
        }
        
        this.speechSynthesis.speak(utterance);
    }
    
    // === UI UPDATES ===
    
    setupUI() {
        // Create mic button
        this.ui.micButton = document.createElement('button');
        this.ui.micButton.id = 'voice-mic-btn';
        this.ui.micButton.className = 'voice-mic-btn';
        this.ui.micButton.innerHTML = '🎤';
        this.ui.micButton.title = 'Hablar (Ctrl+M)';
        this.ui.micButton.style.cssText = `
            position: fixed;
            bottom: 50px;
            right: 20px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: rgba(74, 158, 255, 0.2);
            border: 2px solid rgba(74, 158, 255, 0.5);
            color: #4a9eff;
            font-size: 28px;
            cursor: pointer;
            z-index: 1000;
            transition: all 0.3s ease;
            backdrop-filter: blur(8px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        `;
        
        // Mic icon animation
        this.ui.micIcon = this.ui.micButton;
        
        // Waveform visual
        this.ui.waveform = document.createElement('div');
        this.ui.waveform.id = 'voice-waveform';
        this.ui.waveform.style.cssText = `
            position: fixed;
            bottom: 120px;
            right: 30px;
            display: none;
            gap: 4px;
            z-index: 1001;
        `;
        
        for (let i = 0; i < 5; i++) {
            const bar = document.createElement('div');
            bar.className = 'voice-bar';
            bar.style.cssText = `
                width: 6px;
                height: 20px;
                background: rgba(74, 158, 255, 0.8);
                border-radius: 3px;
                animation: voice-wave 0.5s ease-in-out infinite;
                animation-delay: ${i * 0.1}s;
            `;
            this.ui.waveform.appendChild(bar);
        }
        
        // Status text
        this.ui.statusText = document.createElement('div');
        this.ui.statusText.id = 'voice-status';
        this.ui.statusText.style.cssText = `
            position: fixed;
            bottom: 160px;
            right: 20px;
            background: rgba(10, 15, 30, 0.9);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(74, 158, 255, 0.3);
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 10px;
            color: #8ab4ff;
            z-index: 1000;
            display: none;
        `;
        
        // Append to DOM
        document.body.appendChild(this.ui.micButton);
        document.body.appendChild(this.ui.waveform);
        document.body.appendChild(this.ui.statusText);
        
        // Event listener
        this.ui.micButton.addEventListener('click', () => {
            if (this.isListening) {
                this.stopListening();
            } else {
                this.startListening();
            }
        });
        
        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'm') {
                e.preventDefault();
                if (this.isListening) {
                    this.stopListening();
                } else {
                    this.startListening();
                }
            }
        });
    }
    
    updateUIState(listening) {
        if (!this.ui.micButton) this.setupUI();
        
        if (listening) {
            this.ui.micButton.style.background = 'rgba(255, 100, 50, 0.3)';
            this.ui.micButton.style.borderColor = 'rgba(255, 100, 50, 0.8)';
            this.ui.micButton.style.boxShadow = '0 0 20px rgba(255, 100, 50, 0.4)';
            this.ui.micButton.innerHTML = '🔴';
            
            this.ui.waveform.style.display = 'flex';
            this.ui.statusText.style.display = 'block';
            this.ui.statusText.textContent = '🎤 Escuchando...';
            
            this.ui.micButton.classList.add('listening');
        } else {
            this.ui.micButton.style.background = 'rgba(74, 158, 255, 0.2)';
            this.ui.micButton.style.borderColor = 'rgba(74, 158, 255, 0.5)';
            this.ui.micButton.style.boxShadow = 'none';
            this.ui.micButton.innerHTML = '🎤';
            
            this.ui.waveform.style.display = 'none';
            this.ui.statusText.textContent = '';
            
            this.ui.micButton.classList.remove('listening');
        }
    }
    
    // === UTILITIES ===
    
    similarity(s1, s2) {
        let longer = s1;
        let shorter = s2;
        
        if (s1.length < s2.length) {
            longer = s2;
            shorter = s1;
        }
        
        const longerLength = longer.length;
        if (longerLength === 0) {
            return 1.0;
        }
        
        const changes = this.levenshteinDistance(longer, shorter);
        return (longerLength - changes) / longerLength;
    }
    
    levenshteinDistance(a, b) {
        const matrix = [];
        
        for (let i = 0; i <= b.length; i++) {
            matrix[i] = [i];
        }
        
        for (let j = 0; j <= a.length; j++) {
            matrix[0][j] = j;
        }
        
        for (let i = 1; i <= b.length; i++) {
            for (let j = 1; j <= a.length; j++) {
                if (b.charAt(i - 1) === a.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }
        
        return matrix[b.length][a.length];
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.voiceSystem = new VoiceSystem();
    });
} else {
    window.voiceSystem = new VoiceSystem();
}

// Add CSS animation for waveform
const style = document.createElement('style');
style.textContent = `
    @keyframes voice-wave {
        0%, 100% { height: 20px; opacity: 0.5; }
        50% { height: 40px; opacity: 1; }
    }
`;
document.head.appendChild(style);
