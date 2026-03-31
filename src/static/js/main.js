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
                
                const lines = logData.logs.split('\\n');
                let htmlLog = '';
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i].trim()) {
                        htmlLog += '<p class="mb-2"><span class="text-primary/40 mr-2">[' + new Date().toLocaleTimeString() + ']</span> ' + lines[i] + '</p>';
                    }
                }
                terminalBody.innerHTML = htmlLog;
                terminalBody.scrollTop = terminalBody.scrollHeight;

                if (logData.logs.indexOf('DEPLOYMENT_COMPLETE:') !== -1) {
                    clearInterval(pollInterval);
                    const parts = logData.logs.split('DEPLOYMENT_COMPLETE: ');
                    const folderId = parts[1].split('\\n')[0].trim();
                    showSuccess(folderId);
                }
                
                if (logData.logs.indexOf('FAILED:') !== -1) {
                    clearInterval(pollInterval);
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
    const dummy = "https://drive.google.com/drive/folders/docuagent-secure-archive"; // Consider dynamic if needed
    navigator.clipboard.writeText(dummy).then(function() {
        const btn = e ? e.currentTarget : document.querySelector('button[onclick^="copyToClipboard"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="material-symbols-outlined text-primary">done</span> Copied to Clipboard';
        setTimeout(function() {
            btn.innerHTML = originalText;
        }, 2000);
    });
}
