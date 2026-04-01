const btnOpenMenu = document.getElementById('btnOpenMenu');
const btnCloseMenu = document.getElementById('btnCloseMenu');
const sideMenu = document.getElementById('sideMenu');
const menuOverlay = document.getElementById('menuOverlay');

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

const btnCreateEvent = document.getElementById('btnCreateEvent');
const actionArea = document.getElementById('actionArea');
const btnInitialize = document.getElementById('btnInitialize');
const terminalArea = document.getElementById('terminalArea');
const terminalBody = document.getElementById('terminalBody');
const successArea = document.getElementById('successArea');
const initText = document.getElementById('initText');
const initLoader = document.getElementById('initLoader');
const eventNameInput = document.getElementById('eventNameInput');

btnCreateEvent.addEventListener('click', function() {
    actionArea.classList.remove('hidden');
    actionArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

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

    await startCreation(eventName);
});

async function startCreation(eventName) {
    terminalBody.innerHTML = ''; 
    const statusMessage = document.getElementById('statusMessage');
    const progressBar = document.getElementById('progressBar');
    const pPercent = document.getElementById('statusPercent');

    if (statusMessage) statusMessage.textContent = 'Awaiting Launch Protocol...';
    if (progressBar) progressBar.style.width = '0%';
    if (pPercent) pPercent.textContent = '0%';
    
    try {
        const response = await fetch('/api/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_name: eventName })
        });

        if (!response.ok) throw new Error('Failed to start creation.');

        const pollInterval = setInterval(async function() {
            try {
                const logRes = await fetch('/api/logs');
                const logData = await logRes.json();
                
                const lines = logData.logs.split('\n');
                let htmlLog = '';
                let latestStatus = '';
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i].trim()) {
                        htmlLog += '<p class="mb-2"><span class="text-primary/40 mr-2">[' + new Date().toLocaleTimeString() + ']</span> ' + lines[i] + '</p>';
                        
                        // Extract the readable part of the log for the non-techie UI
                        if (lines[i].includes(' - INFO - ')) {
                            latestStatus = lines[i].split(' - INFO - ')[1];
                        }
                    }
                }
                terminalBody.innerHTML = htmlLog;
                terminalBody.scrollTop = terminalBody.scrollHeight;
                
                // Update the visual status text and purely visual progress bar
                const statusMessage = document.getElementById('statusMessage');
                const progressBar = document.getElementById('progressBar');
                const pPercent = document.getElementById('statusPercent');
                if (statusMessage && latestStatus) {
                    statusMessage.textContent = latestStatus;
                    // Provide a nice visual bump on every new log
                    let curW = parseInt(progressBar.style.width) || 0;
                    if (curW < 90) {
                        curW += 5;
                        progressBar.style.width = curW + '%';
                        pPercent.textContent = curW + '%';
                    }
                }

                if (logData.logs.indexOf('DEPLOYMENT_COMPLETE:') !== -1) {
                    clearInterval(pollInterval);
                    const parts = logData.logs.split('DEPLOYMENT_COMPLETE: ');
                    const folderId = parts[1].split('\n')[0].trim();
                    if (statusMessage) {
                        statusMessage.textContent = 'Deployment Complete!';
                        progressBar.style.width = '100%';
                        pPercent.textContent = '100%';
                    }
                    showSuccess(folderId);
                }
                
                if (logData.logs.indexOf('FAILED:') !== -1) {
                    clearInterval(pollInterval);
                    if (statusMessage) statusMessage.textContent = 'Deployment Failed.';
                    resetUIStatus();
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 1500);

    } catch (error) {
        terminalBody.innerHTML = '<p class="mb-2 text-error">> ERROR: ' + error.message + '</p>';
        resetUIStatus();
    }
}


function showSuccess(folderId) {
    successArea.classList.remove('hidden');
    successArea.scrollIntoView({ behavior: 'smooth' });
    
    const driveLink = document.querySelector('#successArea a');
    if (folderId && driveLink) {
        driveLink.href = 'https://drive.google.com/drive/folders/' + folderId;
    }

    resetUIStatus();
}

function resetUIStatus() {
    initText.classList.remove('hidden');
    initLoader.classList.add('hidden');
    btnInitialize.disabled = false;
    btnInitialize.classList.remove('opacity-50');
}

function copyToClipboard(e) {
    if (e) e.preventDefault();
    
    // Get the actual dynamic link created upon success
    const driveLinkAnchor = document.querySelector('#successArea a');
    const actualLink = driveLinkAnchor ? driveLinkAnchor.href : "https://drive.google.com";

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
