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
    const saInspectorPrompt = document.getElementById('sa-inspector-prompt');
    const saInspectorCode = document.getElementById('sa-inspector-code');
    const saInspectorClose = document.getElementById('sa-inspector-close');
    const saTabLogs = document.getElementById('sa-tab-logs');
    const saTabPrompt = document.getElementById('sa-tab-prompt');
    const saTabCode = document.getElementById('sa-tab-code');
    const saContentLogs = document.getElementById('sa-content-logs');
    const saContentPrompt = document.getElementById('sa-content-prompt');
    const saContentCode = document.getElementById('sa-content-code');

    let ws = null;
    let currentAssistantContainer = null;
    let currentAssistantBubble = null;
    let currentAssistantText = "";
    let currentThinkingCard = null;
    let currentThoughtStream = null;
    let currentThinkingTableWrapper = null;
    let currentThinkingBadge = null;
    let currentThinkingSummary = null;
    let currentThinkingSpinner = null;
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

        } else if (type === 'agent_thinking_init') {
            createAgentThinkingWidget(evt);

        } else if (type === 'agent_thought_stream') {
            if (currentThoughtStream) {
                currentThoughtStream.textContent += evt.content;
                scrollToBottom();
            }

        } else if (type === 'sub_agent_substep') {
            if (evt.sub_agent) {
                subAgentsMap[evt.agent_id] = evt.sub_agent;
            }

        } else if (type === 'agent_thinking_complete') {
            if (currentThinkingSummary) {
                currentThinkingSummary.textContent = evt.summary || `${evt.total_steps || 22} agent steps completed — ${evt.total_duration || '160.8s total'}`;
            }
            if (currentThinkingSpinner) {
                currentThinkingSpinner.className = 'fa-solid fa-circle-check thinking-spinner-icon done';
            }

        } else if (type === 'token') {
            if (!currentAssistantBubble) {
                createAssistantMessageContainer();
            }
            currentAssistantBubble.style.display = 'block';
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

        saInspectorLogs.textContent = sa.logs && sa.logs.length ? sa.logs.join('\n') : 'Dependencies satisfied. All sub-steps executed successfully.';
        saInspectorCode.textContent = sa.generated_code || '// Output generated by specialist sub-agent...';
        
        if (saInspectorPrompt) {
            saInspectorPrompt.textContent = sa.prompt_sent || 'Delegation prompt formulated by Lead Orchestrator.';
        }

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
        if (saTabPrompt) saTabPrompt.classList.remove('active');
        saTabCode.classList.remove('active');
        saContentLogs.classList.add('active');
        if (saContentPrompt) saContentPrompt.classList.remove('active');
        saContentCode.classList.remove('active');
    });

    if (saTabPrompt) {
        saTabPrompt.addEventListener('click', () => {
            saTabPrompt.classList.add('active');
            saTabLogs.classList.remove('active');
            saTabCode.classList.remove('active');
            if (saContentPrompt) saContentPrompt.classList.add('active');
            saContentLogs.classList.remove('active');
            saContentCode.classList.remove('active');
        });
    }

    saTabCode.addEventListener('click', () => {
        saTabCode.classList.add('active');
        saTabLogs.classList.remove('active');
        if (saTabPrompt) saTabPrompt.classList.remove('active');
        saContentCode.classList.add('active');
        saContentLogs.classList.remove('active');
        if (saContentPrompt) saContentPrompt.classList.remove('active');
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

    function createAssistantMessageContainer() {
        currentAssistantText = "";
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const container = document.createElement('div');
        container.className = 'assistant-msg-container';
        container.innerHTML = `
            <div class="assistant-header-row">
                <div class="agent-avatar-circle">
                    <i class="fa-solid fa-atom"></i>
                </div>
                <div class="agent-name-timestamp">AskEcoIQ ${timeStr}</div>
            </div>
            <div class="inspect-hint-label">
                <i class="fa-solid fa-circle-info"></i> Click any row to inspect details
            </div>
            <div class="agent-response-content markdown-body" style="display: none;"></div>
        `;
        chatMessages.appendChild(container);
        currentAssistantContainer = container;
        currentAssistantBubble = container.querySelector('.agent-response-content');
        scrollToBottom();
    }

    function createAgentThinkingWidget(evt) {
        if (!currentAssistantContainer) {
            createAssistantMessageContainer();
        }
        const totalSteps = evt.total_steps || 22;
        const subAgents = evt.sub_agents || [];

        const thinkingCard = document.createElement('div');
        thinkingCard.className = 'agent-thinking-card';

        // Header
        const header = document.createElement('div');
        header.className = 'thinking-header';
        header.innerHTML = `
            <div class="thinking-header-left">
                <i class="fa-solid fa-gear thinking-spinner-icon"></i>
                <span class="thinking-summary-text">${escapeHtml(evt.summary || `${totalSteps} agent steps completed — generating answer...`)}</span>
            </div>
            <div class="thinking-header-badge">${totalSteps}/${totalSteps} <i class="fa-solid fa-chevron-down toggle-icon"></i></div>
        `;

        // Table Wrapper
        const tableWrapper = document.createElement('div');
        tableWrapper.className = 'thinking-table-wrapper';

        let rowsHtml = '';
        subAgents.forEach(sa => {
            const subStepsCount = sa.sub_steps ? sa.sub_steps.length : 1;
            const subStepsPill = `<button class="substeps-toggle-btn" data-agent-id="${sa.id}">${subStepsCount}/${subStepsCount} sub-steps <i class="fa-solid fa-chevron-down"></i></button>`;
            const badgeIcon = sa.badge_icon || '🤖';
            const badgeLabel = sa.badge_label || sa.name;
            
            rowsHtml += `
                <tr class="thinking-row" data-agent-id="${sa.id}">
                    <td>
                        <div class="operation-col">
                            <span class="status-check-icon"><i class="fa-solid fa-check"></i></span>
                            <span class="agent-title-text">${escapeHtml(sa.name)}</span>
                            <span class="agent-pill-tag"><strong>[${escapeHtml(badgeIcon)}]</strong> ${escapeHtml(badgeLabel)}</span>
                            ${subStepsPill}
                            <span class="inspect-arrow-btn" title="Inspect Sub-Agent Prompt & Output"><i class="fa-solid fa-arrow-up-right-from-square"></i></span>
                        </div>
                    </td>
                    <td style="text-align: right;">
                        <span class="duration-badge-pill">${escapeHtml(sa.duration || '0.0s')}</span>
                    </td>
                    <td class="size-text">${escapeHtml(sa.size || '0.0k')}</td>
                    <td class="start-text">${escapeHtml(sa.start_offset || '+0.0s')}</td>
                </tr>
                <tr class="substeps-drawer-row" id="drawer-${sa.id}" style="display: none;">
                    <td colspan="4" style="padding: 0;">
                        <div class="substeps-accordion-drawer">
                            ${(sa.sub_steps || []).map((ss, idx) => `
                                <div class="substep-item">
                                    <div class="substep-item-left">
                                        <span class="substep-dot"></span>
                                        <span>${idx + 1}. ${escapeHtml(ss.name)}</span>
                                    </div>
                                    <span class="substep-duration">${escapeHtml(ss.duration || '1.0s')}</span>
                                </div>
                            `).join('')}
                        </div>
                    </td>
                </tr>
            `;
        });

        tableWrapper.innerHTML = `
            <table class="thinking-table">
                <thead>
                    <tr>
                        <th class="text-left">Tool / Operation</th>
                        <th class="text-right">Duration</th>
                        <th class="text-right">Size</th>
                        <th class="text-right">Start</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
            <div class="live-thought-stream" style="display: block;"></div>
        `;

        thinkingCard.appendChild(header);
        thinkingCard.appendChild(tableWrapper);

        const responseDiv = currentAssistantContainer.querySelector('.agent-response-content');
        if (responseDiv) {
            currentAssistantContainer.insertBefore(thinkingCard, responseDiv);
        } else {
            currentAssistantContainer.appendChild(thinkingCard);
        }

        // Toggle dropdown
        header.addEventListener('click', () => {
            const isCollapsed = tableWrapper.classList.toggle('collapsed');
            const chevron = header.querySelector('.toggle-icon');
            if (chevron) {
                chevron.className = isCollapsed ? 'fa-solid fa-chevron-up toggle-icon' : 'fa-solid fa-chevron-down toggle-icon';
            }
        });

        // Wire substeps accordion buttons
        tableWrapper.querySelectorAll('.substeps-toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const agId = btn.getAttribute('data-agent-id');
                const drawer = tableWrapper.querySelector(`#drawer-${agId}`);
                if (drawer) {
                    const isHidden = drawer.style.display === 'none';
                    drawer.style.display = isHidden ? 'table-row' : 'none';
                    btn.querySelector('i').className = isHidden ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
                }
            });
        });

        // Wire inspect arrow & row click
        tableWrapper.querySelectorAll('.thinking-row').forEach(row => {
            const agId = row.getAttribute('data-agent-id');
            row.addEventListener('click', () => {
                openSubAgentInspector(agId);
            });
        });

        currentThinkingCard = thinkingCard;
        currentThoughtStream = tableWrapper.querySelector('.live-thought-stream');
        currentThinkingTableWrapper = tableWrapper;
        currentThinkingSummary = header.querySelector('.thinking-summary-text');
        currentThinkingSpinner = header.querySelector('.thinking-spinner-icon');
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
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const container = document.createElement('div');
        container.className = 'user-msg-container';

        let imgHtml = '';
        if (images && images.length > 0) {
            imgHtml = `<div class="user-msg-attachments" style="margin-top: 8px;">` + 
                images.map(img => `<img src="${img.dataUrl}" class="user-msg-thumb" alt="User image attachment" style="max-height: 120px; border-radius: 8px; margin-right: 6px;">`).join('') + 
                `</div>`;
        }

        container.innerHTML = `
            <div class="user-timestamp-label">You ${timeStr}</div>
            <div class="user-bubble-pill">
                <p style="margin: 0;">${escapeHtml(text)}</p>
                ${imgHtml}
            </div>
        `;
        chatMessages.appendChild(container);
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

    // Enterprise Intelligence Showcase Demo (matches screenshot 1 & 2)
    function renderShowcaseDemo() {
        chatMessages.innerHTML = '';

        // 1. User Message
        appendUserMessage("What IBM Business Partners are actively working at Citigroup in the USA? Can you identify the areas they are working in? Are there opportunities to sell IBM technology in those areas through those partners? Explain why.");

        // 2. Assistant Container
        createAssistantMessageContainer();

        // 3. Thinking Widget with 22 Steps
        const demoEvt = {
            total_steps: 22,
            summary: "22 agent steps completed — 160.8s total",
            sub_agents: [
                {
                    id: "draup",
                    name: "Draup Agent",
                    role: "Market Intelligence & Partner Ecosystem",
                    description: "Extract active service-provider footprints, outsourcing indices, and top vendor rankings.",
                    duration: "10.8s",
                    size: "56.2k",
                    start_offset: "+5.7s",
                    badge_icon: "D",
                    badge_label: "Draup Agent",
                    status: "completed",
                    progress: 100,
                    prompt_sent: `=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===
SPECIALIST IDENTITY: Draup Agent
SPECIALIST ROLE: Market Intelligence & Partner Ecosystem Specialist
TARGET DELIVERABLE: Draup Market Footprint Handoff
PRIMARY USER QUERY: What IBM Business Partners are actively working at Citigroup in the USA?

=== 1. YOUR CORE MISSION & OBJECTIVES ===
Extract active service-provider footprints, outsourcing indices, and top vendor rankings at Citigroup in the USA.

=== 2. UPSTREAM ARTIFACTS & HANDOFF CONTEXT ===
Lead Orchestrator query parsed: Entity="Citigroup Inc.", AccountID=763241, Region="USA".

=== 3. WORKSPACE DOMAIN CONTEXT ===
Enterprise Intelligence Directory: Citigroup vendor engagement database.

=== 4. MANDATORY EXECUTION CONSTRAINTS ===
1. ZERO PLACEHOLDERS: Generate 100% complete, verified partner names and metrics.
2. PRECISION & RIGOR: Provide verified outsourcing index ratio (9.99/10) and active count (135).
3. FORMAT RIGOR: Output structured partner rankings with verified signals.

Execute your specialized task with maximum rigor now.`,
                    logs: [
                        "✓ Sub-step 1/6: Resolve Account Entity ID & Metadata (1.2s)",
                        "✓ Sub-step 2/6: Query Service-Provider Ranking Index (2.4s)",
                        "✓ Sub-step 3/6: Fetch Top-10 Active Partner Footprints (3.1s)",
                        "✓ Sub-step 4/6: Parse Geo Boundaries (USA Focus) (1.8s)",
                        "✓ Sub-step 5/6: Synthesize Outsourcing Index Ratios (1.5s)",
                        "✓ Sub-step 6/6: Format Primary Vendor Engagement Matrix (0.8s)",
                        "Handoff complete; downstream agents may proceed."
                    ],
                    generated_code: `# Draup Market Intelligence Handoff
Account: Citigroup Inc. (ID: 763241)
Total Active Service-Provider Partners: 135
Outsourcing Index: 9.99/10 (High Market Concentration)
Primary USA Partners: TCS, Wipro, LTIMindtree, Infosys, Accenture, Cognizant, Capgemini, HCLTech, Kyndryl, DXC.`,
                    sub_steps: [
                        { name: "Resolve Account Entity ID & Metadata", duration: "1.2s" },
                        { name: "Query Service-Provider Ranking Index", duration: "2.4s" },
                        { name: "Fetch Top-10 Active Partner Footprints", duration: "3.1s" },
                        { name: "Parse Geo Boundaries (USA Focus)", duration: "1.8s" },
                        { name: "Synthesize Outsourcing Index Ratios", duration: "1.5s" },
                        { name: "Format Primary Vendor Engagement Matrix", duration: "0.8s" },
                    ]
                },
                {
                    id: "nl2sql",
                    name: "NL2SQL Agent",
                    role: "Enterprise SQL & Sales Data Specialist",
                    description: "Run structured queries against enterprise sales-out data and transaction records.",
                    duration: "24.5s",
                    size: "2.7k",
                    start_offset: "+7.4s",
                    badge_icon: "💻",
                    badge_label: "NL2SQL Agent",
                    status: "completed",
                    progress: 100,
                    prompt_sent: `=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===
SPECIALIST IDENTITY: NL2SQL Agent
SPECIALIST ROLE: Enterprise SQL & Sales Data Specialist
TARGET DELIVERABLE: SQL Sales Out Aggregates
PRIMARY USER QUERY: What IBM Business Partners are actively working at Citigroup in the USA?

=== 1. YOUR CORE MISSION & OBJECTIVES ===
Execute structured SQL aggregation against Q2C Sales Out data for Citigroup service providers.

=== 2. UPSTREAM ARTIFACTS & HANDOFF CONTEXT ===
--- [UPSTREAM HANDOFF FROM: DRAUP AGENT] ---
Entity="Citigroup Inc." (ID: 763241), 135 active partners identified.

=== 3. MANDATORY EXECUTION CONSTRAINTS ===
1. Generate valid ANSI SQL AST without injection flaws.
2. Reconcile transaction signals across fiscal quarters.`,
                    logs: [
                        "✓ Sub-step 1/3: Generate Schema-Aligned SQL AST (5.2s)",
                        "✓ Sub-step 2/3: Execute Q2C Sales Out Aggregate Query (12.1s)",
                        "✓ Sub-step 3/3: Validate Transaction Signal Integrity (7.2s)",
                        "Handoff complete; downstream agents may proceed."
                    ],
                    generated_code: `SELECT partner_name, SUM(revenue_usd) as total_sales_out, COUNT(deal_id) as transactions
FROM q2c_sales_out
WHERE account_id = 763241 AND region = 'USA'
GROUP BY partner_name ORDER BY total_sales_out DESC;`,
                    sub_steps: [
                        { name: "Generate Schema-Aligned SQL AST", duration: "5.2s" },
                        { name: "Execute Q2C Sales Out Aggregate Query", duration: "12.1s" },
                        { name: "Validate Transaction Signal Integrity", duration: "7.2s" },
                    ]
                },
                {
                    id: "coverage",
                    name: "Coverage Agent",
                    role: "Account Coverage & Alignment Mapping",
                    description: "Map managing directors, technical specialists, and partner practice leads.",
                    duration: "45.6s",
                    size: "14.2k",
                    start_offset: "+10.1s",
                    badge_icon: "👥",
                    badge_label: "Coverage Agent",
                    status: "completed",
                    progress: 100,
                    prompt_sent: `=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===
SPECIALIST IDENTITY: Coverage Agent
SPECIALIST ROLE: Account Coverage & Alignment Mapping Specialist
TARGET DELIVERABLE: Verified Coverage Contact Matrix

=== 1. YOUR CORE MISSION & OBJECTIVES ===
Map US Managing Directors, Technical Partner Specialists (TPS), and Data/Automation PTS leads for all active partners at Citigroup.`,
                    logs: [
                        "✓ Sub-step 1/12: Scan Geo Managing Director Directory (4.1s)",
                        "✓ Sub-step 2/12: Extract Technical Partner Specialists (TPS) (6.3s)",
                        "✓ Sub-step 3/12: Map Data PTS & Automation Practice Leads (8.5s)",
                        "✓ Sub-step 4/12: Filter US-Specific Coverage Matrix (5.2s)",
                        "✓ Sub-step 5/12: Correlate Partner Signals (400+ signals) (9.4s)",
                        "✓ Sub-step 6/12: Query Portfolio Simplification Initiatives (3.1s)",
                        "✓ Sub-step 7/12: Match TCS Legacy Modernization Coverage (2.5s)",
                        "✓ Sub-step 8/12: Map Wipro Cloud Migration Coverage (2.2s)",
                        "✓ Sub-step 9/12: Map LTM Stranded-Cost Modernization Coverage (2.8s)",
                        "✓ Sub-step 10/12: Correlate IBM Technology Sales Channels (3.4s)",
                        "✓ Sub-step 11/12: Resolve Partner Contact Escalation Hierarchy (3.2s)",
                        "✓ Sub-step 12/12: Generate Verified Coverage Contact Roster (4.9s)",
                        "Handoff complete; downstream agents may proceed."
                    ],
                    generated_code: `# Verified IBM Coverage Matrix
TCS Coverage: MD Sharon Fortune-Bowden | TPS: Renzo Peralta | Data PTS: Arvind Rajpurohit | Automation PTS: Derek Fu
Wipro Coverage: MD Sharon Fortune-Bowden | TPS: Renzo Peralta | Data PTS: Arvind Rajpurohit | Automation PTS: Derek Fu
LTIMindtree Coverage: MD Sharon Fortune-Bowden | TPS: Renzo Peralta | Data PTS: Arvind Rajpurohit | Automation PTS: Derek Fu`,
                    sub_steps: [
                        { name: "Scan Geo Managing Director Directory", duration: "4.1s" },
                        { name: "Extract Technical Partner Specialists (TPS)", duration: "6.3s" },
                        { name: "Map Data PTS & Automation Practice Leads", duration: "8.5s" },
                        { name: "Filter US-Specific Coverage Matrix", duration: "5.2s" },
                        { name: "Correlate Partner Signals (400+ signals)", duration: "9.4s" },
                        { name: "Query Portfolio Simplification Initiatives", duration: "3.1s" },
                        { name: "Match TCS Legacy Modernization Coverage", duration: "2.5s" },
                        { name: "Map Wipro Cloud Migration Coverage", duration: "2.2s" },
                        { name: "Map LTM Stranded-Cost Modernization Coverage", duration: "2.8s" },
                        { name: "Correlate IBM Technology Sales Channels", duration: "3.4s" },
                        { name: "Resolve Partner Contact Escalation Hierarchy", duration: "3.2s" },
                        { name: "Generate Verified Coverage Contact Roster", duration: "4.9s" },
                    ]
                },
                {
                    id: "design_in",
                    name: "Design-In Agent",
                    role: "Solution Design-In & Opportunity Discovery",
                    description: "Pinpoint enterprise solution opportunities and technology sales angles.",
                    duration: "0.0s",
                    size: "9.8k",
                    start_offset: "+27.4s",
                    badge_icon: "⚙",
                    badge_label: "Design-In Agent",
                    status: "completed",
                    progress: 100,
                    prompt_sent: `=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===
SPECIALIST IDENTITY: Design-In Agent
SPECIALIST ROLE: Solution Design-In & Opportunity Discovery Specialist
TARGET DELIVERABLE: Technology Modernization Vectors`,
                    logs: [
                        "✓ Sub-step 1/1: Synthesize Technology Modernization Vectors (0.0s)",
                        "Handoff complete; downstream agents may proceed."
                    ],
                    generated_code: `# IBM Technology Sell-Through Vectors
1. watsonx.data & watsonx.ai for AI-at-scale pilots
2. Red Hat OpenShift & Cloud Paks for Stranded-Cost and Legacy Modernization
3. IBM API Connect & MQ for core banking transactional middleware`,
                    sub_steps: [
                        { name: "Synthesize Technology Modernization Vectors", duration: "0.0s" },
                    ]
                }
            ]
        };

        // Populate subAgentsMap
        demoEvt.sub_agents.forEach(sa => {
            subAgentsMap[sa.id] = sa;
        });
        renderSubAgentsList();

        createAgentThinkingWidget(demoEvt);

        if (currentThinkingSummary) {
            currentThinkingSummary.textContent = "22 agent steps completed — 160.8s total";
        }
        if (currentThinkingSpinner) {
            currentThinkingSpinner.className = "fa-solid fa-circle-check thinking-spinner-icon done";
        }
        if (currentThoughtStream) {
            currentThoughtStream.textContent = `I'll pull together market intelligence, sales data, offerings, and coverage contacts for Citigroup simultaneously. I'll query both questions in parallel against I'll start by resolving the account ID. the Q2C Sales Out data. I'll look up all 10 partners simultaneously with blank geo. Resolved: id=763241, key="Citigroup Inc.". Now dispatching all Step 2 calls in parallel. [WORKER: DraupAgent | Account: Citigroup | Status: OK | Tools: 6 called]`;
        }

        // 4. Response Content
        const demoMarkdown = `
## Section 1 — Which IBM Business Partners are actively working at Citigroup, and in what areas?

Citigroup runs an exceptionally large ecosystem — **135 active service-provider partners** with a maximum outsourcing index of **9.99/10** *(source: Draup)*. The table below consolidates market engagement, work areas, and IBM coverage owners, filtered to the top active partners in the USA.

| Partner (engagement rank) | Areas they work in at Citigroup | IBM coverage owner (US / geo) |
| :--- | :--- | :--- |
| **TCS** *(400 signals – #1)* | AI-at-scale pilots, legacy consolidation, stranded-cost modernization, portfolio simplification, Wealth & PB operations, Citi Ventures co-investments, Cloud Migration CoE, App Modernization Factories. | **US:** MD Sharon Fortune-Bowden; TPS Renzo Peralta; Data PTS Arvind Rajpurohit; Automation PTS Derek Fu<br>**India:** Md Arshad Warsi |
| **Wipro** *(380 signals – #2)* | Global wealth management, cross-border payments, legacy maintenance, mainframe re-platforming, automated regulatory compliance, data migration pipelines, cyber resiliency. | **US:** MD Sharon Fortune-Bowden; TPS Renzo Peralta; Data PTS Arvind Rajpurohit; Automation PTS Derek Fu |
| **LTIMindtree** *(340 signals – #3)* | Stranded-cost modernization, core banking services, digital engineering, API integrations, payments modernization, test automation pipelines. | **US:** MD Sharon Fortune-Bowden; TPS Renzo Peralta; Data PTS Arvind Rajpurohit; Automation PTS Derek Fu |
| **Infosys** *(310 signals – #4)* | Enterprise risk modeling, cloud analytics, Finacle platform consulting, trade finance systems, digital transformation, DevSecOps enablement. | **US:** MD Sharon Fortune-Bowden; TPS Renzo Peralta; Data PTS Arvind Rajpurohit; Automation PTS Derek Fu |
| **Accenture** *(290 signals – #5)* | Enterprise architecture, digital banking strategy, hybrid multicloud transformation, regulatory reporting, AI governance frameworks. | **US:** MD Sharon Fortune-Bowden; TPS Renzo Peralta; Data PTS Arvind Rajpurohit; Automation PTS Derek Fu |
| **Cognizant** *(260 signals – #6)* | Quality engineering, fraud detection analytics, cards & personal loans servicing, API platform management. | **US:** MD Sharon Fortune-Bowden; TPS Renzo Peralta; Data PTS Arvind Rajpurohit; Automation PTS Derek Fu |

---

## Section 2 — Opportunities to Sell IBM Technology Through These Partners

Citigroup's massive outsourcing ratio creates prime opportunities to embed IBM technology directly into partner solution delivery:

1. **watsonx (watsonx.ai & watsonx.data)**:
   - **TCS & Infosys** are leading AI-at-scale pilots and risk analytics across Citigroup's Treasury and Trade Solutions (TTS). Embedding *watsonx.governance* provides compliant GenAI validation required by US banking regulators.

2. **Red Hat OpenShift & Cloud Paks**:
   - **Wipro & LTIMindtree** manage mainframe re-platforming and cloud migration pipelines. Utilizing *Red Hat OpenShift on AWS/Azure* enables Citigroup to build hybrid multicloud workloads with portable microservices.

3. **IBM API Connect & MQ**:
   - High-throughput cross-border payments and core banking modernization run on IBM integration middleware managed in partner App Modernization Factories.

---

### 📋 What I Did (Summary of Agent Actions)
- **Step 1 (Draup Agent)**: Extracted partner ecosystem intelligence; resolved account ID \`763241\`, identified **135 active service-provider partners** at Citigroup with an outsourcing index of **9.99/10**.
- **Step 2 (NL2SQL Agent)**: Formulated and executed Q2C Sales Out SQL queries across 10 top vendor footprints in 24.5s.
- **Step 3 (Coverage Agent)**: Completed 12 sub-steps correlating 400+ partner signals, mapping US Managing Directors, TPS, and Data/Automation PTS owners.
- **Step 4 (Design-In Agent)**: Pinpointed enterprise opportunities across watsonx, OpenShift, and Cloud Pak middleware.
- **Synthesis Complete**: 22 agent steps delivered across 4 specialized DAG sub-agents in 160.8s.
`;

        currentAssistantBubble.style.display = 'block';
        currentAssistantText = demoMarkdown;
        renderAssistantContent(demoMarkdown);
        scrollToBottom();
    }

    // Wire Quick Prompt Chips & Showcase Button
    document.querySelectorAll('.quick-prompt-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query && userInput) {
                userInput.value = query;
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    const eagleAuditBtn = document.getElementById('eagle-audit-btn');
    if (eagleAuditBtn) {
        eagleAuditBtn.addEventListener('click', () => {
            if (userInput && chatForm) {
                userInput.value = "🦅 Run Eagle Agent: perform a whole-folder deep audit, auto-repair all broken handlers/syntax on disk, and synthesize an application review.";
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    const loadShowcaseBtn = document.getElementById('load-showcase-btn');
    if (loadShowcaseBtn) {
        loadShowcaseBtn.addEventListener('click', () => {
            renderShowcaseDemo();
        });
    }

    // App Initialization
    initWebSocket();
    loadModels();
    fetchFiles();
});

