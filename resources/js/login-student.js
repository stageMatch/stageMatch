const loginBtn = document.getElementById('loginBtn');

window.addEventListener("pageshow", () => {
    loginBtn.textContent = 'Accedi con Google';
    loginBtn.disabled = false;
    loginBtn.style.opacity = '1';
});

loginBtn.addEventListener('click', () => {
    loginBtn.textContent = 'Accesso in corso…';
    loginBtn.disabled = true;
    loginBtn.style.opacity = '0.7';

    setTimeout(() => {
        window.location.href = "/auth/login";
    }, 800);
});

function showNotification(message, type = "info", duration = 5000) {
    let toastContainer = document.querySelector(".toast-container");
    if (!toastContainer) {
        toastContainer = document.createElement("div");
        toastContainer.className = "toast-container";
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement("div");
    toast.className = `custom-toast ${type}`;
    toast.innerHTML = `<div class="toast-content"><div class="toast-message">${message}</div></div>
        <button class="toast-close" aria-label="Chiudi">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>`;

    toastContainer.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));

    let autoDismissTimer = setTimeout(() => dismissToast(), duration);

    function dismissToast() {
        toast.classList.remove("show");
        setTimeout(() => {
            toast.remove();
            if (toastContainer.childNodes.length === 0) toastContainer.remove();
        }, 500);
    }

    toast.querySelector(".toast-close").addEventListener("click", () => {
        clearTimeout(autoDismissTimer);
        dismissToast();
    });
}

const NOTICE_MESSAGES = {
    login_required: { message: "Devi accedere per continuare.", type: "warning" },
    session_expired: { message: "La tua sessione è scaduta. Accedi di nuovo.", type: "warning" },
    logged_out: { message: "Logout effettuato con successo.", type: "success" }
};

const notice = new URLSearchParams(window.location.search).get("notice");
if (notice && NOTICE_MESSAGES[notice]) {
    const { message, type } = NOTICE_MESSAGES[notice];
    showNotification(message, type);
}
