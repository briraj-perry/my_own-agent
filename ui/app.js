/**
 * Application Logic for my_neo-agent Dashboard (v2.0 Sub-Agent Edition)
 * Handles WebSocket streaming, Sub-Agent Visual Inspector, Folder Selection Prompt, and UI updates
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
    const refreshFilesBtn = document.getElementById('refresh-files-btn');
    const connectionStatus = document.getElementById('connection-status');
    const fileTreeContainer = document.getElementById('file-tree-container');
    const fileCountBadge = document.getElementById('file-count-badge');
    const terminalBody = document.getElementById('terminal-body');
    const execStatusBadge = document.getElementById('exec-status-badge');
    const currentFolderLabel = document.getElementById('current-folder-label');
    const subagentsList = document.getElementById('subagents-list');
    const subagentCountBadge = document.getElementById('subagent-count-badge');
    const workflowMessage = document.getElementById('workflow-message');
    const workflowStatus = document.getElementById('workflow-status');

    // Permission Modal Elements
    const permissionModal = document.getElementById('permission-modal');
    const permActionDesc = document.getElementById('perm-action-desc');
    const permRiskBadge = document.getElementById('perm-risk-badge');
    const permCommandCode = document.getElementById('perm-command-code');
    const permApproveBtn = document.getElementById('perm-approve-btn');
    const permDenyBtn = document.getElementById('perm-deny-btn');

    // Folder Modal Elements (Requirement 4)
    const folderModal = document.getElementById('folder-modal');
    const folderOptionsGrid = document.getElementById('folder-options-grid');
    const customFolderInput = document.getElementById('custom-folder-input');
    const folderConfirmBtn = document.getElementById('folder-confirm-btn');
    const folderConfirmRootBtn = document.getElementById('folder-confirm-root-btn');

    // Framework Modal Elements (Next.js vs HTML)
    let activeFrameworkReqId = null;
    let selectedFrameworkChoice = 'nextjs';
    const frameworkModal = document.getElementById('framework-modal');
    const frameworkCardNextjs = document.getElementById('framework-card-nextjs');
    const frameworkCardHtml = document.getElementById('framework-card-html');
    const frameworkConfirmNextjsBtn = document.getElementById('framework-confirm-nextjs-btn');
    const frameworkConfirmHtmlBtn = document.getElementById('framework-confirm-html-btn');

    // Sub-Agent Inspector Modal Elements (Requirement 2)

    const subagentModal = document.getElementById('subagent-modal');
    const saInspectorTitle = document.getElementById('sa-inspector-title');
    const saInspectorRole = document.getElementById('sa-inspector-role');
    const saInspectorStatus = document.getElementById('sa-inspector-status');
    const saInspectorFile = document.getElementById('sa-inspector-file');
    const saInspectorLogs = document.getElementById('sa-inspector-logs');
    const saInspectorCode = document.getElementById('sa-inspector-code');
    const saInspectorClose = document.getElementById('sa-inspector-close');
    const saTabLogs = document.getElementById('sa-tab-logs');
    const saTabCode = document.getElementById('sa-tab-code');
    const saContentLogs = document.getElementById('sa-content-logs');
    const saContentCode = document.getElementById('sa-content-code');

    let ws = null;
    let currentAssistantBubble = null;
    let currentAssistantText = "";
    let activePermissionId = null;
    let activeFolderReqId = null;
    let selectedFolderPath = ".";
    
    // Sub-Agent tracking dictionary
    const subAgentsMap = {};
    let inspectingSubAgentId = null;

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
            if (mascotState === 'idle' || mascotState === 'completed') {
                fetchFiles();
            }

        } else if (type === 'plan_generated') {
            const plan = evt.plan || {};
            const planMsgDiv = document.createElement('div');
            planMsgDiv.className = 'message system-message plan-generated-msg';
            let stepsHtml = (plan.steps || []).map(s => `
                <div style="margin-top:6px; padding:6px 10px; background:rgba(0,245,212,0.06); border-radius:6px; border-left:3px solid #00f5d4;">
                    <strong style="color:#00f5d4;">${escapeHtml(s.step_id)}: ${escapeHtml(s.title)}</strong>
                    <div style="font-size:0.85rem; color:#a0aec0;">Target File: <code style="color:#e0aaff;">${escapeHtml(s.target_file || 'N/A')}</code> | Role: ${escapeHtml(s.assigned_role || 'Agent')}</div>
                    <div style="font-size:0.85rem; margin-top:2px;">${escapeHtml(s.description || '')}</div>
                </div>
            `).join('');

            planMsgDiv.innerHTML = `
                <div class="msg-avatar system-avatar" style="color: #00f5d4;">
                    <i class="fa-solid fa-brain"></i>
                </div>
                <div class="msg-bubble" style="border: 1px solid rgba(0, 245, 212, 0.4); background: rgba(0, 245, 212, 0.05);">
                    <div class="msg-author" style="color: #00f5d4;">🧠 Dynamic Execution Plan Generated</div>
                    <div class="msg-content">
                        <p><strong>${escapeHtml(plan.title || '')}</strong></p>
                        <p style="font-size:0.9rem; color:#a0aec0;">${escapeHtml(plan.summary || '')}</p>
                        <div style="margin-top:10px;">${stepsHtml}</div>
                    </div>
                </div>
            `;
            chatMessages.appendChild(planMsgDiv);
            scrollToBottom();

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

            permMsgDiv.querySelector('.inline-approve-btn').addEventListener('click', () => {
                sendPermissionResponse(true);
                permMsgDiv.style.opacity = '0.6';
            });
            permMsgDiv.querySelector('.inline-deny-btn').addEventListener('click', () => {
                sendPermissionResponse(false);
                permMsgDiv.style.opacity = '0.6';
            });

        } else if (type === 'folder_selection_required') {
            activeFolderReqId = evt.id;
            const folders = evt.available_folders || ['.'];
            renderFolderSelectionOptions(folders);
            folderModal.classList.add('active');

        } else if (type === 'framework_selection_required') {
            activeFrameworkReqId = evt.id;
            if (frameworkModal) frameworkModal.classList.add('active');

            // Render inline framework choice card inside chat stream
            const fwMsgDiv = document.createElement('div');
            fwMsgDiv.className = 'message system-message framework-inline-msg';
            fwMsgDiv.innerHTML = `
                <div class="msg-avatar system-avatar" style="color: #4cc9f0;">
                    <i class="fa-solid fa-cubes"></i>
                </div>
                <div class="msg-bubble" style="border: 1px solid rgba(76, 201, 240, 0.5); background: rgba(76, 201, 240, 0.08);">
                    <div class="msg-author" style="color: #4cc9f0;">⚡ Framework Choice Required</div>
                    <div class="msg-content">
                        <p><strong>Do you want to build this using Next.js or normal HTML?</strong></p>
                        <div style="margin-top: 12px; display: flex; gap: 10px;">
                            <button class="cyber-button primary inline-nextjs-btn" style="padding: 8px 16px; font-size: 0.85rem;">
                                <i class="fa-brands fa-react"></i> Next.js (Claw Agent)
                            </button>
                            <button class="cyber-button secondary inline-html-btn" style="padding: 8px 16px; font-size: 0.85rem;">
                                <i class="fa-brands fa-html5"></i> Normal HTML (Neo Agent)
                            </button>
                        </div>
                    </div>
                </div>
            `;
            chatMessages.appendChild(fwMsgDiv);
            scrollToBottom();

            fwMsgDiv.querySelector('.inline-nextjs-btn').addEventListener('click', () => {
                sendFrameworkResponse('nextjs');
                fwMsgDiv.style.opacity = '0.6';
            });
            fwMsgDiv.querySelector('.inline-html-btn').addEventListener('click', () => {
                sendFrameworkResponse('html');
                fwMsgDiv.style.opacity = '0.6';
            });

        } else if (type === 'coordination_update') {

            if (workflowMessage) workflowMessage.textContent = evt.message || 'Coordination update received.';
            if (workflowStatus) workflowStatus.textContent = 'IN PROGRESS';
            appendTerminalLog(`[COORDINATION] ${evt.title || 'Workflow'}: ${evt.message || ''}`);

        } else if (type === 'sub_agent_spawn') {
            const sa = evt.sub_agent;
            subAgentsMap[sa.id] = sa;
            renderSubAgentsList();
            appendTerminalLog(`[SUB-AGENT SPAWNED] ${sa.name} (${sa.role}) -> ${sa.target_file}`);

        } else if (type === 'sub_agent_update') {
            const sa = evt.sub_agent;
            subAgentsMap[sa.id] = sa;
            renderSubAgentsList();
            if (inspectingSubAgentId === sa.id) {
                updateSubAgentInspector(sa);
            }

        } else if (type === 'sub_agent_log') {
            const saId = evt.id;
            if (subAgentsMap[saId]) {
                subAgentsMap[saId].logs.push(evt.log);
                if (inspectingSubAgentId === saId) {
                    saInspectorLogs.textContent = subAgentsMap[saId].logs.join('\n');
                }
            }

        } else if (type === 'sub_agent_complete') {
            const sa = evt.sub_agent;
            subAgentsMap[sa.id] = sa;
            renderSubAgentsList();
            if (inspectingSubAgentId === sa.id) {
                updateSubAgentInspector(sa);
            }
            appendTerminalLog(`[SUB-AGENT COMPLETED] ${sa.name} written: ${sa.target_file}`);
            fetchFiles();

        } else if (type === 'execution_log') {
            appendTerminalLog(`\n> [EXEC] ${evt.command || ''}\n${evt.output || ''}`);
        }
    }

    // Render Sub-Agents List in Right Panel (Requirements 1 & 2)
    function renderSubAgentsList() {
        const saArray = Object.values(subAgentsMap);
        if (saArray.length === 0) {
            subagentsList.innerHTML = `
                <div class="subagent-placeholder">
                    <i class="fa-solid fa-robot"></i>
                    <p>No sub-agents active. Ask Neo a complex task to spawn sub-agents!</p>
                </div>
            `;
            subagentCountBadge.textContent = '0 ACTIVE';
            subagentCountBadge.className = 'exec-badge idle';
            return;
        }

        subagentCountBadge.textContent = `${saArray.length} SPAWNED`;
        subagentCountBadge.className = 'exec-badge running';

        subagentsList.innerHTML = '';
        saArray.forEach(sa => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'subagent-item';
            itemDiv.innerHTML = `
                <div class="subagent-item-top">
                    <span class="subagent-name">${escapeHtml(sa.name)}</span>
                    <span class="subagent-status-badge ${sa.status}">${sa.status.toUpperCase()}</span>
                </div>
                <div class="subagent-desc">${escapeHtml(sa.description)}</div>
                <div class="subagent-dependencies">${sa.dependencies && sa.dependencies.length ? `Depends on: ${escapeHtml(sa.dependencies.join(' -> '))}` : 'Starts the workflow'}</div>
                <div class="subagent-progress-bar">
                    <div class="subagent-progress-fill" style="width: ${sa.progress}%;"></div>
                </div>
            `;
            itemDiv.addEventListener('click', () => {
                openSubAgentInspector(sa.id);
            });
            subagentsList.appendChild(itemDiv);
        });
        updateWorkflowRail(saArray);
    }

    function updateWorkflowRail(agents) {
        const stageStates = new Map(agents.map(agent => [agent.id, agent.status]));
        document.querySelectorAll('[data-stage]').forEach(node => {
            const status = stageStates.get(node.dataset.stage);
            node.className = status ? `stage-${status}` : '';
        });
        if (workflowStatus && agents.length) {
            const complete = agents.filter(agent => agent.status === 'completed').length;
            workflowStatus.textContent = complete === agents.length ? 'COMPLETE' : `${complete}/${agents.length} DONE`;
        }
    }

    // Open Sub-Agent Inspector Modal (Requirement 2)
    function openSubAgentInspector(saId) {
        inspectingSubAgentId = saId;
        const sa = subAgentsMap[saId];
        if (!sa) return;

        updateSubAgentInspector(sa);
        subagentModal.classList.add('active');
    }

    function updateSubAgentInspector(sa) {
        saInspectorTitle.textContent = sa.name;
        saInspectorRole.textContent = `Role: ${sa.role} | ${sa.description}`;
        saInspectorStatus.textContent = sa.status.toUpperCase();
        saInspectorStatus.className = `badge subagent-status-badge ${sa.status}`;
        saInspectorFile.textContent = sa.target_file || 'N/A';

        saInspectorLogs.textContent = sa.logs ? sa.logs.join('\n') : 'No logs recorded.';
        saInspectorCode.textContent = sa.generated_code || '// Code generating by sub-agent...';
        if (window.hljs) {
            hljs.highlightElement(saInspectorCode);
        }
    }

    saInspectorClose.addEventListener('click', () => {
        subagentModal.classList.remove('active');
        inspectingSubAgentId = null;
    });

    saTabLogs.addEventListener('click', () => {
        saTabLogs.classList.add('active');
        saTabCode.classList.remove('active');
        saContentLogs.classList.add('active');
        saContentCode.classList.remove('active');
    });

    saTabCode.addEventListener('click', () => {
        saTabCode.classList.add('active');
        saTabLogs.classList.remove('active');
        saContentCode.classList.add('active');
        saContentLogs.classList.remove('active');
    });

    // Folder Selection Options Grid (Requirement 4)
    function renderFolderSelectionOptions(folders) {
        folderOptionsGrid.innerHTML = '';
        selectedFolderPath = '.';

        folders.forEach(f => {
            const pill = document.createElement('div');
            pill.className = `folder-option-pill ${f === '.' ? 'active' : ''}`;
            pill.innerHTML = `<i class="fa-solid fa-folder"></i> <span>${escapeHtml(f)}</span>`;
            pill.addEventListener('click', () => {
                document.querySelectorAll('.folder-option-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                selectedFolderPath = f;
                customFolderInput.value = '';
            });
            folderOptionsGrid.appendChild(pill);
        });
    }

    folderConfirmBtn.addEventListener('click', () => {
        let finalFolder = selectedFolderPath;
        if (customFolderInput.value.trim()) {
            finalFolder = customFolderInput.value.trim();
        }
        sendFolderResponse(finalFolder);
    });

    folderConfirmRootBtn.addEventListener('click', () => {
        sendFolderResponse('.');
    });

    function sendFolderResponse(folder) {
        if (activeFolderReqId && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'folder_response',
                id: activeFolderReqId,
                folder: folder
            }));
        }
        folderModal.classList.remove('active');
        currentFolderLabel.textContent = folder;
        activeFolderReqId = null;
    }

    if (frameworkCardNextjs && frameworkCardHtml) {
        frameworkCardNextjs.addEventListener('click', () => {
            selectedFrameworkChoice = 'nextjs';
            frameworkCardNextjs.style.border = '2px solid #4cc9f0';
            frameworkCardNextjs.style.background = 'rgba(76, 201, 240, 0.18)';
            frameworkCardHtml.style.border = '2px solid rgba(247, 37, 133, 0.4)';
            frameworkCardHtml.style.background = 'rgba(247, 37, 133, 0.06)';
        });
        frameworkCardHtml.addEventListener('click', () => {
            selectedFrameworkChoice = 'html';
            frameworkCardHtml.style.border = '2px solid #f72585';
            frameworkCardHtml.style.background = 'rgba(247, 37, 133, 0.18)';
            frameworkCardNextjs.style.border = '2px solid rgba(76, 201, 240, 0.4)';
            frameworkCardNextjs.style.background = 'rgba(76, 201, 240, 0.06)';
        });
    }

    if (frameworkConfirmNextjsBtn) {
        frameworkConfirmNextjsBtn.addEventListener('click', () => {
            sendFrameworkResponse('nextjs');
        });
    }

    if (frameworkConfirmHtmlBtn) {
        frameworkConfirmHtmlBtn.addEventListener('click', () => {
            sendFrameworkResponse('html');
        });
    }

    function sendFrameworkResponse(choice) {
        if (activeFrameworkReqId && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'framework_response',
                id: activeFrameworkReqId,
                choice: choice
            }));
        }
        if (frameworkModal) frameworkModal.classList.remove('active');
        activeFrameworkReqId = null;
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

        if (window.hljs) {
            currentAssistantBubble.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
        scrollToBottom();
    }

    // Image Upload State & Handlers
    const uploadImageBtn = document.getElementById('upload-image-btn');
    const imageUploadInput = document.getElementById('image-upload-input');
    const imagePreviewBar = document.getElementById('image-preview-bar');
    let attachedImages = [];

    if (uploadImageBtn && imageUploadInput) {
        uploadImageBtn.addEventListener('click', () => {
            imageUploadInput.click();
        });

        imageUploadInput.addEventListener('change', (e) => {
            handleImageFiles(e.target.files);
            imageUploadInput.value = '';
        });
    }

    // Drag and Drop Images
    const textareaWrapper = document.querySelector('.textarea-wrapper');
    if (textareaWrapper) {
        textareaWrapper.addEventListener('dragover', (e) => {
            e.preventDefault();
            textareaWrapper.style.borderColor = 'var(--cyan-accent)';
        });
        textareaWrapper.addEventListener('dragleave', (e) => {
            e.preventDefault();
            textareaWrapper.style.borderColor = '';
        });
        textareaWrapper.addEventListener('drop', (e) => {
            e.preventDefault();
            textareaWrapper.style.borderColor = '';
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                const imgFiles = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
                if (imgFiles.length > 0) handleImageFiles(imgFiles);
            }
        });
    }

    // Clipboard Paste Image Support
    if (userInput) {
        userInput.addEventListener('paste', (e) => {
            const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
            if (items) {
                const imgFiles = [];
                for (let item of items) {
                    if (item.type && item.type.indexOf('image') === 0) {
                        const blob = item.getAsFile();
                        if (blob) imgFiles.push(blob);
                    }
                }
                if (imgFiles.length > 0) {
                    handleImageFiles(imgFiles);
                }
            }
        });
    }

    function handleImageFiles(files) {
        if (!files || files.length === 0) return;
        Array.from(files).forEach(file => {
            if (!file.type.startsWith('image/')) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                const dataUrl = event.target.result;
                const base64 = dataUrl.split(',')[1] || dataUrl;
                const imgObj = { id: Date.now() + Math.random().toString(36).substr(2, 4), dataUrl, base64 };
                attachedImages.push(imgObj);
                renderImagePreviews();
            };
            reader.readAsDataURL(file);
        });
    }

    function renderImagePreviews() {
        if (!imagePreviewBar) return;
        if (attachedImages.length === 0) {
            imagePreviewBar.classList.add('hidden');
            imagePreviewBar.innerHTML = '';
            return;
        }
        imagePreviewBar.classList.remove('hidden');
        imagePreviewBar.innerHTML = '';
        attachedImages.forEach((img, idx) => {
            const chip = document.createElement('div');
            chip.className = 'img-preview-chip';
            chip.innerHTML = `
                <img src="${img.dataUrl}" alt="Attached image ${idx+1}">
                <button type="button" class="remove-img-btn" title="Remove">&times;</button>
            `;
            chip.querySelector('.remove-img-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                attachedImages = attachedImages.filter(i => i.id !== img.id);
                renderImagePreviews();
            });
            imagePreviewBar.appendChild(chip);
        });
    }

    function appendUserMessage(text, images = []) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user-message';
        let imgHtml = '';
        if (images && images.length > 0) {
            imgHtml = `<div class="user-msg-attachments">` + 
                images.map(img => `<img src="${img.dataUrl}" class="user-msg-thumb" alt="User image attachment">`).join('') + 
                `</div>`;
        }
        msgDiv.innerHTML = `
            <div class="msg-avatar user-avatar">
                <i class="fa-solid fa-user"></i>
            </div>
            <div class="msg-bubble">
                <div class="msg-author">You</div>
                <div class="msg-content">
                    <p>${escapeHtml(text)}</p>
                    ${imgHtml}
                </div>
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
        if (!chatMessages) return;
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
        setTimeout(() => {
            if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 50);
    }


    function escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Submit Prompt Form
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = userInput.value.trim();
        if (!query && attachedImages.length === 0) return;

        if (ws && ws.readyState === WebSocket.OPEN) {
            const currentImages = [...attachedImages];
            appendUserMessage(query || "Inspect attached image(s)", currentImages);
            currentAssistantBubble = null;
            
            const payload = {
                type: 'chat',
                message: query || "Analyze the attached image and assist with code or task."
            };

            if (currentImages.length > 0) {
                payload.images = currentImages.map(img => img.base64);
            }

            ws.send(JSON.stringify(payload));

            userInput.value = '';
            attachedImages = [];
            renderImagePreviews();
            appendTerminalLog(`\n[USER PROMPT] ${query} ${currentImages.length ? `(${currentImages.length} images attached)` : ''}`);
        } else {
            alert('WebSocket is not connected to my_neo-agent server.');
        }
    });

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
                    opt.textContent = m.name;
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

    if (refreshFilesBtn) {
        refreshFilesBtn.addEventListener('click', async () => {
            refreshFilesBtn.disabled = true;
            const icon = refreshFilesBtn.querySelector('i');
            if (icon) icon.className = 'fa-solid fa-rotate-right fa-spin';
            await fetchFiles();
            if (icon) icon.className = 'fa-solid fa-rotate-right';
            refreshFilesBtn.disabled = false;
        });
    }

    window.addEventListener('focus', () => {
        fetchFiles();
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
                    const isPy = item.name.endsWith('.py') || item.name.endsWith('.pyw');
                    const iconClass = isPy ? 'fa-brands fa-python' : 'fa-solid fa-file-code';
                    const iconStyle = isPy ? 'color: #00f5d4;' : '';
                    itemDiv.style.cursor = 'pointer';
                    itemDiv.innerHTML = `
                        <div class="item-left">
                            <i class="${iconClass}" style="${iconStyle}"></i>
                            <span style="${isPy ? 'font-weight:600; color:#e0aaff;' : ''}">${item.name}</span>
                        </div>
                        <span class="item-lines">${item.lines} lines</span>
                    `;
                    itemDiv.addEventListener('click', (e) => {
                        e.stopPropagation();
                        openFileViewer(item.path, item.name, isPy);
                    });
                } else {
                    itemDiv.style.cursor = 'pointer';
                    itemDiv.innerHTML = `
                        <div class="item-left">
                            <i class="fa-solid fa-folder" style="color: #00f5d4;"></i>
                            <strong style="color: #e0aaff;">${item.name}</strong>
                        </div>
                    `;
                    itemDiv.addEventListener('click', (e) => {
                        e.stopPropagation();
                        openFileViewer(item.path, item.name, false);
                    });
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

    // File Viewer Modal Logic
    const fileViewerModal = document.getElementById('file-viewer-modal');
    const fileViewerTitle = document.getElementById('file-viewer-title');
    const fileViewerPath = document.getElementById('file-viewer-path');
    const fileViewerLines = document.getElementById('file-viewer-lines');
    const fileViewerCode = document.getElementById('file-viewer-code-content');
    const fileViewerIcon = document.getElementById('file-viewer-icon');
    const fileViewerClose = document.getElementById('file-viewer-close');
    const fileViewerCloseBtn = document.getElementById('file-viewer-close-btn');
    const fileViewerCopyBtn = document.getElementById('file-viewer-copy-btn');

    async function openFileViewer(filePath, fileName, isPy) {
        if (!fileViewerModal) return;
        try {
            const res = await fetch(`/api/file/content?path=${encodeURIComponent(filePath)}`);
            const data = await res.json();
            if (data.status === 'success') {
                fileViewerTitle.textContent = fileName || filePath;
                fileViewerPath.textContent = data.full_path || filePath;
                fileViewerLines.textContent = `${data.lines} LINES`;
                fileViewerCode.textContent = data.content;
                if (fileViewerIcon) {
                    fileViewerIcon.className = isPy ? 'fa-brands fa-python' : 'fa-solid fa-file-code';
                }
                if (window.hljs) {
                    hljs.highlightElement(fileViewerCode);
                }
                fileViewerModal.classList.add('active');
            } else if (data.status === 'is_directory') {
                // User clicked or opened a directory! Set workspace root and refresh file tree
                await fetch('/api/workspace/set_root', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder: data.full_path || filePath })
                });
                if (currentWorkingFolderBadge) {
                    const shortName = fileName || filePath.split('/').pop().split('\\').pop();
                    currentWorkingFolderBadge.innerHTML = `<i class="fa-solid fa-folder-open"></i> ${shortName}`;
                }
                fetchFiles();
            } else {
                alert(`Could not open file: ${data.message || 'Unknown error'}`);
            }
        } catch (err) {
            alert(`Error opening file: ${err.message}`);
        }
    }

    if (fileViewerClose) fileViewerClose.addEventListener('click', () => fileViewerModal.classList.remove('active'));
    if (fileViewerCloseBtn) fileViewerCloseBtn.addEventListener('click', () => fileViewerModal.classList.remove('active'));
    if (fileViewerCopyBtn) {
        fileViewerCopyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(fileViewerCode.textContent);
            fileViewerCopyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
            setTimeout(() => {
                fileViewerCopyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Copy Code';
            }, 2000);
        });
    }

    // App Initialization
    initWebSocket();
    loadModels();
    fetchFiles();
});
