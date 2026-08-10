/**
 * Application Logic for my_neo-agent Dashboard
 * Handles WebSocket streaming, UI updates, Permission Modal, and API integration
 */
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    
    const modelSelect = document.getElementById('model-select');
    const reindexBtn = document.getElementById('reindex-btn');
    const connectionStatus = document.getElementById('connection-status');
    const fileTreeContainer = document.getElementById('file-tree-container');
    const fileCountBadge = document.getElementById('file-count-badge');
    const terminalBody = document.getElementById('terminal-body');
    const execStatusBadge = document.getElementById('exec-status-badge');

    // Modal Elements
    const permissionModal = document.getElementById('permission-modal');
    const permActionDesc = document.getElementById('perm-action-desc');
    const permRiskBadge = document.getElementById('perm-risk-badge');
    const permCommandCode = document.getElementById('perm-command-code');
    const permApproveBtn = document.getElementById('perm-approve-btn');
    const permDenyBtn = document.getElementById('perm-deny-btn');

    let ws = null;
    let currentAssistantBubble = null;
    let currentAssistantText = "";
    let activePermissionId = null;

    // Configure marked options
    if (window.marked) {
        marked.setOptions({
            highlight: function(code, lang) {
                if (window.hljs && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return code;
            },
            breaks: true
        });
    }

    // Initialize WebSocket Connection
    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        updateConnectionStatus('connecting');

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[WS] Connected to my_neo-agent server.');
            updateConnectionStatus('connected');
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleAgentEvent(msg);
            } catch (err) {
                console.error('[WS Error] Error parsing frame:', err);
            }
        };

        ws.onerror = (err) => {
            console.error('[WS Error]', err);
            updateConnectionStatus('disconnected');
        };

        ws.onclose = () => {
            console.warn('[WS] Connection closed. Retrying in 3s...');
            updateConnectionStatus('disconnected');
            setTimeout(initWebSocket, 3000);
        };
    }

    function updateConnectionStatus(state) {
        const dot = connectionStatus.querySelector('.status-dot');
        const text = connectionStatus.querySelector('.status-text');

        if (state === 'connected') {
            dot.className = 'status-dot connected';
            text.textContent = 'Online';
        } else if (state === 'connecting') {
            dot.className = 'status-dot disconnected';
            text.textContent = 'Connecting...';
        } else {
            dot.className = 'status-dot disconnected';
            text.textContent = 'Disconnected';
        }
    }

    // Handle Event Stream from Backend Agent Engine
    function handleAgentEvent(evt) {
        const type = evt.type;

        if (type === 'state') {
            const mascotState = evt.mascot_state || 'idle';
            const statusMsg = evt.status || 'Processing...';
            const step = evt.step;

            if (window.mascot) {
                window.mascot.setState(mascotState, statusMsg);
            }

            updateTimelineStep(step);
            if (execStatusBadge) {
                execStatusBadge.className = `exec-badge ${mascotState === 'executing' ? 'running' : 'idle'}`;
                execStatusBadge.textContent = mascotState.toUpperCase();
            }

        } else if (type === 'token') {
            if (!currentAssistantBubble) {
                createAssistantMessageBubble();
            }
            currentAssistantText += evt.content;
            renderAssistantContent(currentAssistantText);

        } else if (type === 'permission_request') {
            activePermissionId = evt.id;
            permActionDesc.textContent = evt.action || 'Execute operation';
            permCommandCode.textContent = evt.command || 'neo-agent command';
            permRiskBadge.textContent = `${evt.risk_level || 'MEDIUM'} RISK`;

            if (window.mascot) {
                window.mascot.setState('permission', 'Security Authorization Required!');
            }

            permissionModal.classList.add('active');

            // Render inline permission card inside chat stream as well
            const permMsgDiv = document.createElement('div');
            permMsgDiv.className = 'message system-message permission-inline-msg';
            permMsgDiv.innerHTML = `
                <div class="msg-avatar system-avatar" style="color: #f72585;">
                    <i class="fa-solid fa-shield-halved"></i>
                </div>
                <div class="msg-bubble" style="border: 1px solid rgba(247, 37, 133, 0.5); background: rgba(247, 37, 133, 0.08);">
                    <div class="msg-author" style="color: #f72585;">🔒 Security Authorization Required</div>
                    <div class="msg-content">
                        <p><strong>Action Requested:</strong> ${escapeHtml(evt.action || '')}</p>
                        <p style="margin-top:4px;"><code>${escapeHtml(evt.command || '')}</code></p>
                        <div style="margin-top: 12px; display: flex; gap: 10px;">
                            <button class="cyber-button success inline-approve-btn" style="padding: 6px 16px; font-size: 0.85rem;">
                                <i class="fa-solid fa-check"></i> Accept & Create File
                            </button>
                            <button class="cyber-button danger inline-deny-btn" style="padding: 6px 16px; font-size: 0.85rem;">
                                <i class="fa-solid fa-xmark"></i> Deny
                            </button>
                        </div>
                    </div>
                </div>
            `;
            chatMessages.appendChild(permMsgDiv);
            scrollToBottom();

            // Bind click events on inline buttons
            permMsgDiv.querySelector('.inline-approve-btn').addEventListener('click', () => {
                sendPermissionResponse(true);
                permMsgDiv.style.opacity = '0.6';
            });
            permMsgDiv.querySelector('.inline-deny-btn').addEventListener('click', () => {
                sendPermissionResponse(false);
                permMsgDiv.style.opacity = '0.6';
            });


        } else if (type === 'execution_log') {
            appendTerminalLog(`\n> [EXEC] ${evt.command || ''}\n${evt.output || ''}`);
        }
    }

    function updateTimelineStep(stepName) {
        const steps = ['step-plan', 'step-verify', 'step-executing', 'step-repair'];
        steps.forEach(s => {
            const el = document.getElementById(s);
            if (el) el.classList.remove('active');
        });

        if (stepName) {
            const activeEl = document.getElementById(`step-${stepName}`);
            if (activeEl) activeEl.classList.add('active');
        }
    }

    function createAssistantMessageBubble() {
        currentAssistantText = "";
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant-message';
        msgDiv.innerHTML = `
            <div class="msg-avatar assistant-avatar">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="msg-bubble">
                <div class="msg-author">my_neo-agent</div>
                <div class="msg-content markdown-body"></div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        currentAssistantBubble = msgDiv.querySelector('.msg-content');
        scrollToBottom();
    }

    function renderAssistantContent(rawText) {
        if (!currentAssistantBubble) return;
        if (window.marked) {
            currentAssistantBubble.innerHTML = marked.parse(rawText);
        } else {
            currentAssistantBubble.textContent = rawText;
        }

        // Apply syntax highlighting
        if (window.hljs) {
            currentAssistantBubble.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
        scrollToBottom();
    }

    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user-message';
        msgDiv.innerHTML = `
            <div class="msg-avatar user-avatar">
                <i class="fa-solid fa-user"></i>
            </div>
            <div class="msg-bubble">
                <div class="msg-author">You</div>
                <div class="msg-content"><p>${escapeHtml(text)}</p></div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendTerminalLog(text) {
        if (!terminalBody) return;
        terminalBody.textContent += text + "\n";
        terminalBody.scrollTop = terminalBody.scrollHeight;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Submit Prompt Form
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = userInput.value.trim();
        if (!query) return;

        if (ws && ws.readyState === WebSocket.OPEN) {
            appendUserMessage(query);
            currentAssistantBubble = null; // reset bubble target for streaming
            
            ws.send(JSON.stringify({
                type: 'chat',
                message: query
            }));

            userInput.value = '';
            appendTerminalLog(`\n[USER PROMPT] ${query}`);
        } else {
            alert('WebSocket is not connected to my_neo-agent server.');
        }
    });

    // Handle Enter Key inside textarea
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Modal Permission Responses
    permApproveBtn.addEventListener('click', () => {
        sendPermissionResponse(true);
    });

    permDenyBtn.addEventListener('click', () => {
        sendPermissionResponse(false);
    });

    function sendPermissionResponse(approved) {
        if (activePermissionId && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'permission_response',
                id: activePermissionId,
                approved: approved
            }));
        }
        permissionModal.classList.remove('active');
        activePermissionId = null;
    }

    // Model selection API call
    async function loadModels() {
        try {
            const res = await fetch('/api/models');
            const data = await res.json();
            if (data.available_models) {
                modelSelect.innerHTML = '';
                data.available_models.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = `${m.name} (${m.provider})`;
                    if (m.id === data.active_model) opt.selected = true;
                    modelSelect.appendChild(opt);
                });
            }
        } catch (err) {
            console.error('Error fetching models:', err);
        }
    }

    modelSelect.addEventListener('change', async () => {
        const modelId = modelSelect.value;
        try {
            const res = await fetch('/api/models/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id: modelId })
            });
            const data = await res.json();
            appendTerminalLog(`[SYSTEM] Active model switched to: ${data.selected_model}`);
        } catch (err) {
            console.error('Error selecting model:', err);
        }
    });

    // Re-index Workspace
    reindexBtn.addEventListener('click', async () => {
        reindexBtn.disabled = true;
        reindexBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Re-indexing...';
        try {
            const res = await fetch('/api/reindex', { method: 'POST' });
            const data = await res.json();
            appendTerminalLog(`[INDEXER] ${data.message}`);
            await fetchFiles();
        } catch (err) {
            console.error('Error re-indexing codebase:', err);
        } finally {
            reindexBtn.disabled = false;
            reindexBtn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Re-index Workspace';
        }
    });

    // Fetch File Explorer Tree
    async function fetchFiles() {
        try {
            const res = await fetch('/api/files');
            const data = await res.json();
            renderFileTree(data.tree || []);
        } catch (err) {
            console.error('Error fetching files:', err);
        }
    }

    function renderFileTree(tree) {
        fileTreeContainer.innerHTML = '';
        let totalCount = 0;

        function traverse(items, container) {
            items.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'tree-item';
                
                if (item.type === 'file') {
                    totalCount++;
                    itemDiv.innerHTML = `
                        <div class="item-left">
                            <i class="fa-solid fa-file-code"></i>
                            <span>${item.name}</span>
                        </div>
                        <span class="item-lines">${item.lines} lines</span>
                    `;
                } else {
                    itemDiv.innerHTML = `
                        <div class="item-left">
                            <i class="fa-solid fa-folder"></i>
                            <strong>${item.name}</strong>
                        </div>
                    `;
                }
                container.appendChild(itemDiv);
                if (item.children) {
                    const subContainer = document.createElement('div');
                    subContainer.style.paddingLeft = '14px';
                    traverse(item.children, subContainer);
                    container.appendChild(subContainer);
                }
            });
        }

        traverse(tree, fileTreeContainer);
        fileCountBadge.textContent = `${totalCount} files`;
    }

    clearChatBtn.addEventListener('click', () => {
        chatMessages.innerHTML = '';
    });

    // App Initialization
    initWebSocket();
    loadModels();
    fetchFiles();
});
