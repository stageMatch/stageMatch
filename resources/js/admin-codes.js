const generateBtn = document.getElementById("generateBtn");
const copyBtn = document.getElementById("copyBtn");
const newCode = document.getElementById("newCode");
const newCodeValue = document.getElementById("newCodeValue");
const statusEl = document.getElementById("status");
const codesBody = document.getElementById("codesBody");
const emptyMsg = document.getElementById("emptyMsg");

function setStatus(message, isError = false) {
    statusEl.textContent = message;
    statusEl.classList.toggle("is-error", isError);
}

function formatDate(iso) {
    // Le date sono UTC senza offset: si forza la lettura come UTC.
    const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);

    return date.toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" });
}

function renderCodes(codes) {
    codesBody.replaceChildren();
    emptyMsg.hidden = codes.length > 0;

    codes.forEach((item) => {
        const row = document.createElement("tr");

        const codeCell = document.createElement("td");
        const code = document.createElement("code");
        code.textContent = item.code;
        codeCell.appendChild(code);

        const dateCell = document.createElement("td");
        dateCell.textContent = formatDate(item.created_at);

        const statusCell = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = item.used ? "badge" : "badge is-available";
        badge.textContent = item.used ? "Utilizzato" : "Disponibile";
        statusCell.appendChild(badge);

        row.append(codeCell, dateCell, statusCell);
        codesBody.appendChild(row);
    });
}

async function loadCodes() {
    try {
        const response = await fetch("/api/admin/codes");

        if (!response.ok) throw new Error(response.status);

        renderCodes(await response.json());
    } catch (error) {
        setStatus("Impossibile caricare i codici. Riprova.", true);
    }
}

generateBtn.addEventListener("click", async () => {
    generateBtn.disabled = true;
    setStatus("");

    try {
        const response = await fetch("/api/admin/codes", { method: "POST" });

        if (!response.ok) throw new Error(response.status);

        const { code } = await response.json();
        newCodeValue.textContent = code;
        newCode.hidden = false;
        setStatus("Codice generato: copialo e invialo all'azienda.");
        await loadCodes();
    } catch (error) {
        setStatus("Generazione non riuscita. Riprova.", true);
    } finally {
        generateBtn.disabled = false;
    }
});

copyBtn.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(newCodeValue.textContent);
        setStatus("Codice copiato negli appunti.");
    } catch (error) {
        setStatus("Copia non riuscita: selezionalo e copialo a mano.", true);
    }
});

loadCodes();
