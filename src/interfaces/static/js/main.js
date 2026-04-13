const btnOpenMenu = document.getElementById('btnOpenMenu');
const btnCloseMenu = document.getElementById('btnCloseMenu');
const sideMenu = document.getElementById('sideMenu');
const menuOverlay = document.getElementById('menuOverlay');
const btnCreateEvent = document.getElementById('btnCreateEvent');
const btnSummaryEvent = document.getElementById('btnSummaryEvent');
const actionArea = document.getElementById('actionArea');
const btnInitialize = document.getElementById('btnInitialize');
const terminalArea = document.getElementById('terminalArea');
const terminalBody = document.getElementById('terminalBody');
const successArea = document.getElementById('successArea');
const initText = document.getElementById('initText');
const initLoader = document.getElementById('initLoader');
const eventNameInput = document.getElementById('eventNameInput');
const workflowBadge = document.getElementById('workflowBadge');
const workflowTitle = document.getElementById('workflowTitle');
const workflowDescription = document.getElementById('workflowDescription');
const successTitle = document.getElementById('successTitle');
const successDescription = document.getElementById('successDescription');
const successLink = document.getElementById('successLink');
const summaryResultArea = document.getElementById('summaryResultArea');
const summaryResultGrid = document.getElementById('summaryResultGrid');
const summaryRowLabel = document.getElementById('summaryRowLabel');
const btnCopyLink = document.getElementById('btnCopyLink');
const btnOpenLogs = document.getElementById('btnOpenLogs');
const btnCloseLogs = document.getElementById('btnCloseLogs');
const logsPanel = document.getElementById('logsPanel');
const globalLogsBody = document.getElementById('globalLogsBody');
const btnClearGlobalLogs = document.getElementById('btnClearGlobalLogs');
let globalLogPoll = null;

const toggleMenu = (open) => {
    if (open) {
        sideMenu.classList.remove('-translate-x-full');
        menuOverlay.classList.remove('opacity-0', 'pointer-events-none');
    } else {
        sideMenu.classList.add('-translate-x-full');
        menuOverlay.classList.add('opacity-0', 'pointer-events-none');
    }
};

btnOpenMenu.addEventListener('click', function() { toggleMenu(true); });
btnCloseMenu.addEventListener('click', function() { toggleMenu(false); });
menuOverlay.addEventListener('click', function() { toggleMenu(false); });

let selectedWorkflow = 'create';
let activePoll = null;
let successLinkUrl = null;

const workflowCopy = {
    create: {
        badge: 'Create',
        title: 'Archive Initialization',
        description: 'Enter the unique identifier for the new secure container.',
        button: 'Launch Protocol',
        statusTitle: 'Provisioning Complete',
        statusDescription: 'The secure event archive is now live and synchronized.',
        card: btnCreateEvent,
    },
    summary: {
        badge: 'Summary',
        title: 'Summary Extraction',
        description: 'Enter the event name to extract report, committee, registration, and feedback data.',
        button: 'Run Summary',
        statusTitle: 'Summary Sync Complete',
        statusDescription: 'The extracted summary is now written to the Activity Sheet.',
        card: btnSummaryEvent,
    }
};

function setWorkflow(mode) {
    selectedWorkflow = mode;

    const createState = mode === 'create';
    const summaryState = mode === 'summary';

    const activeCardClass = ['shadow-[0_0_30px_rgba(242,202,80,0.12)]', 'bg-surface-container-highest'];
    const inactiveCardClass = ['border-outline-variant/10'];

    [workflowCopy.create.card, workflowCopy.summary.card].forEach((card) => {
        if (!card) return;
        card.classList.remove(...activeCardClass);
        card.classList.add(...inactiveCardClass);
    });

    const activeCard = workflowCopy[mode].card;
    if (activeCard) {
        activeCard.classList.add(...activeCardClass);
    }

    if (workflowBadge) workflowBadge.textContent = workflowCopy[mode].badge;
    if (workflowTitle) workflowTitle.textContent = workflowCopy[mode].title;
    if (workflowDescription) workflowDescription.textContent = workflowCopy[mode].description;
    if (initText) initText.textContent = workflowCopy[mode].button;
    if (successTitle) successTitle.textContent = workflowCopy[mode].statusTitle;
    if (successDescription) successDescription.textContent = workflowCopy[mode].statusDescription;
    if (successLink) {
        successLink.innerHTML = `<span class="material-symbols-outlined">cloud_circle</span>${createState ? ' Open Drive Folder' : ' Open Activity Sheet'}`;
    }
    if (summaryResultArea) summaryResultArea.classList.toggle('hidden', !summaryState);
    if (summaryResultGrid && !summaryState) summaryResultGrid.innerHTML = '';
    if (summaryRowLabel && !summaryState) summaryRowLabel.textContent = '';
    if (btnCopyLink) btnCopyLink.classList.toggle('hidden', summaryState);
}

btnCreateEvent.addEventListener('click', function() {
    setWorkflow('create');
    actionArea.classList.remove('hidden');
    actionArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

if (btnSummaryEvent) {
    btnSummaryEvent.addEventListener('click', function() {
        setWorkflow('summary');
        actionArea.classList.remove('hidden');
        actionArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
}

setWorkflow('create');

btnInitialize.addEventListener('click', async function() {
    if (!eventNameInput.value) {
        eventNameInput.classList.add('border-error');
        setTimeout(function() { eventNameInput.classList.remove('border-error'); }, 1000);
        return;
    }

    const eventName = eventNameInput.value;
    initText.classList.add('hidden');
    initLoader.classList.remove('hidden');
    btnInitialize.disabled = true;
    btnInitialize.classList.add('opacity-50');

    terminalArea.classList.remove('hidden');
    terminalArea.scrollIntoView({ behavior: 'smooth', block: 'center' });

    await startWorkflow(eventName, selectedWorkflow);
});

function renderSummaryResult(result) {
    if (!summaryResultArea || !summaryResultGrid) return;

    const summary = result?.summary || {};
    const row = result?.row;
    const fields = [
        ['Event Name', summary['Event Name']],
        ['Event Date', summary['Event Date']],
        ['Participants', summary['No. of Participants']],
        ['Participation', summary['Percentage Participation']],
        ['Coordinators', summary['Coordinators']],
        ['Contacts', summary['Contact Number of Coordinators']],
    ];

    summaryResultGrid.innerHTML = fields.map(([label, value]) => `
        <div class="rounded-lg border border-outline-variant/15 bg-surface-container-low p-4">
            <p class="text-[10px] font-bold tracking-[0.2em] uppercase text-primary mb-2">${label}</p>
            <p class="text-sm text-on-surface leading-relaxed break-words">${value || 'Not available'}</p>
        </div>
    `).join('');

    if (summaryRowLabel) {
        summaryRowLabel.textContent = row ? `Row ${row}` : '';
    }
}

function resetWorkflowState() {
    initText.classList.remove('hidden');
    initLoader.classList.add('hidden');
    btnInitialize.disabled = false;
    btnInitialize.classList.remove('opacity-50');
}

async function startWorkflow(eventName, mode) {
    terminalBody.innerHTML = '';
    successArea.classList.add('hidden');
    successLinkUrl = null;
    if (summaryResultArea) summaryResultArea.classList.add('hidden');
    const statusMessage = document.getElementById('statusMessage');
    const progressBar = document.getElementById('progressBar');
    const pPercent = document.getElementById('statusPercent');

    if (statusMessage) statusMessage.textContent = mode === 'summary' ? 'Preparing summary extraction...' : 'Awaiting Launch Protocol...';
    if (progressBar) progressBar.style.width = '0%';
    if (pPercent) pPercent.textContent = '0%';

    try {
        const endpoint = mode === 'summary' ? '/api/summary' : '/api/create';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_name: eventName })
        });

        if (!response.ok) throw new Error('Failed to start workflow.');

        if (activePoll) clearInterval(activePoll);

        activePoll = setInterval(async function() {
            try {
                const logRes = await fetch('/api/logs');
                const logData = await logRes.json();
                
                const lines = logData.logs.split('\n');
                let htmlLog = '';
                let latestStatus = '';
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i].trim()) {
                        htmlLog += '<p class="mb-2"><span class="text-primary/40 mr-2">[' + new Date().toLocaleTimeString() + ']</span> ' + lines[i] + '</p>';
                        
                        if (lines[i].includes(' - INFO - ')) {
                            latestStatus = lines[i].split(' - INFO - ')[1];
                        }
                    }
                }
                terminalBody.innerHTML = htmlLog;
                terminalBody.scrollTop = terminalBody.scrollHeight;
                
                const statusMessage = document.getElementById('statusMessage');
                const progressBar = document.getElementById('progressBar');
                const pPercent = document.getElementById('statusPercent');
                if (statusMessage && latestStatus) {
                    statusMessage.textContent = latestStatus;
                    let curW = parseInt(progressBar.style.width) || 0;
                    if (curW < 90) {
                        curW += 5;
                        progressBar.style.width = curW + '%';
                        pPercent.textContent = curW + '%';
                    }
                }

                const successToken = mode === 'summary' ? 'SUMMARY_COMPLETE' : 'DEPLOYMENT_COMPLETE:';
                if (logData.logs.indexOf(successToken) !== -1) {
                    clearInterval(activePoll);
                    activePoll = null;

                    let folderId = null;
                    let summarySheetUrl = null;
                    if (mode === 'create') {
                        const parts = logData.logs.split('DEPLOYMENT_COMPLETE: ');
                        folderId = parts[1] ? parts[1].split('\n')[0].trim() : null;
                    }

                    if (mode === 'summary') {
                        try {
                            const resultRes = await fetch('/api/summary-result');
                            if (resultRes.ok) {
                                const result = await resultRes.json();
                                folderId = result.folder_id || null;
                                summarySheetUrl = result.activity_sheet_url || null;
                                renderSummaryResult(result);
                            }
                        } catch (e) {
                            console.error('Failed to load summary result', e);
                        }
                    }

                    if (statusMessage) {
                        statusMessage.textContent = mode === 'summary' ? 'Summary Sync Complete' : 'Deployment Complete!';
                        progressBar.style.width = '100%';
                        pPercent.textContent = '100%';
                    }
                    showSuccess(mode, folderId, summarySheetUrl);
                }
                
                if (logData.logs.indexOf('FAILED:') !== -1) {
                    clearInterval(activePoll);
                    activePoll = null;
                    if (statusMessage) statusMessage.textContent = 'Deployment Failed.';
                    resetWorkflowState();
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 1500);

    } catch (error) {
        terminalBody.innerHTML = '<p class="mb-2 text-error">> ERROR: ' + error.message + '</p>';
        resetWorkflowState();
    }
}

function showSuccess(mode, folderId, summarySheetUrl) {
    successArea.classList.remove('hidden');
    successArea.scrollIntoView({ behavior: 'smooth' });
    
    if (successTitle) {
        successTitle.textContent = mode === 'summary' ? 'Summary Sync Complete' : 'Provisioning Complete';
    }
    if (successDescription) {
        successDescription.textContent = mode === 'summary'
            ? 'The extracted summary has been written back to the Activity Sheet.'
            : 'The secure event archive is now live and synchronized.';
    }
    
    const driveLink = document.querySelector('#successArea a');
    successLinkUrl = mode === 'summary'
        ? (summarySheetUrl || 'https://docs.google.com/spreadsheets')
        : (folderId ? ('https://drive.google.com/drive/folders/' + folderId) : 'https://drive.google.com');

    if (driveLink) {
        driveLink.href = successLinkUrl;
    }

    if (summaryResultArea) {
        summaryResultArea.classList.toggle('hidden', mode !== 'summary');
    }

    resetWorkflowState();
}

function copyToClipboard(e) {
    if (e) e.preventDefault();
    
    // Get the actual dynamic link created upon success
    const driveLinkAnchor = document.querySelector('#successArea a');
    const actualLink = successLinkUrl || (driveLinkAnchor ? driveLinkAnchor.href : "https://drive.google.com");

    // Visual snap effect for the button click
    const btn = e ? e.currentTarget : document.querySelector('button[onclick^="copyToClipboard"]');
    if (btn) {
        btn.style.transform = "scale(0.95)";
        setTimeout(() => { btn.style.transform = "scale(1)"; }, 150);
    }

    navigator.clipboard.writeText(actualLink).then(function() {
        if (btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="material-symbols-outlined material-symbols-filled text-primary">done</span> Copied to Clipboard';
            setTimeout(function() {
                btn.innerHTML = originalText;
            }, 2000);
        }
        
        // Show toaster
        const toast = document.getElementById('toastMessage');
        if (toast) {
            toast.classList.remove('translate-y-20', 'opacity-0');
            setTimeout(() => {
                toast.classList.add('translate-y-20', 'opacity-0');
            }, 3000);
        }
    });
}

const toggleLogsPanel = (open) => {
    if (open) {
        logsPanel.classList.remove('translate-x-full');
        startGlobalLogPoll();
    } else {
        logsPanel.classList.add('translate-x-full');
        stopGlobalLogPoll();
    }
};

const startGlobalLogPoll = () => {
    if (globalLogPoll) return;
    
    const fetchGlobalLogs = async () => {
        try {
            const res = await fetch('/api/logs');
            const data = await res.json();
            if (data.logs) {
                const lines = data.logs.split('\n');
                let html = '';
                lines.forEach(line => {
                    if (line.trim()) {
                        html += `<p class="mb-1 border-l-2 border-primary/20 pl-3 py-0.5 hover:bg-white/5 transition-colors">${line}</p>`;
                    }
                });
                globalLogsBody.innerHTML = html;
                globalLogsBody.scrollTop = globalLogsBody.scrollHeight;
            }
        } catch (e) {
            console.error("Global log poll error", e);
        }
    };

    fetchGlobalLogs();
    globalLogPoll = setInterval(fetchGlobalLogs, 2000);
};

const stopGlobalLogPoll = () => {
    if (globalLogPoll) {
        clearInterval(globalLogPoll);
        globalLogPoll = null;
    }
};

if (btnOpenLogs) btnOpenLogs.addEventListener('click', (e) => { e.preventDefault(); toggleLogsPanel(true); });
if (btnCloseLogs) btnCloseLogs.addEventListener('click', () => toggleLogsPanel(false));
if (btnClearGlobalLogs) btnClearGlobalLogs.addEventListener('click', () => { globalLogsBody.innerHTML = ''; });
