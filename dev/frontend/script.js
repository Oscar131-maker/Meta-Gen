document.addEventListener('DOMContentLoaded', () => {
    const btnUrl = document.getElementById('mode-url');
    const btnText = document.getElementById('mode-text');
    const formUrl = document.getElementById('form-url');
    const formText = document.getElementById('form-text');

    // Loading Section
    const loadingSection = document.getElementById('loading-section');
    const loadingText = document.getElementById('loading-text');

    const resultsSection = document.getElementById('results-section');
    const outputText = document.getElementById('output-text');
    const btnProcessUrl = document.getElementById('btn-process-url');
    const btnProcessText = document.getElementById('btn-process-text');
    const historyList = document.getElementById('history-list');
    const inputSection = document.getElementById('input-section');

    // Modal elements
    const deleteModal = document.getElementById('delete-modal');
    const btnModalConfirm = document.getElementById('btn-modal-confirm');
    const btnModalCancel = document.getElementById('btn-modal-cancel');
    let itemToDeleteId = null;

    let history = [];

    // Load history from server
    fetchHistory();

    async function fetchHistory() {
        try {
            const res = await fetch('/api/history');
            if (res.ok) {
                history = await res.json();
                renderHistory();
            }
        } catch (e) {
            console.error("Error fetching history:", e);
        }
    }

    // Event Listeners for Main UI
    btnUrl.addEventListener('change', () => {
        formUrl.classList.add('active-form');
        formText.classList.remove('active-form');
    });

    btnText.addEventListener('change', () => {
        formText.classList.add('active-form');
        formUrl.classList.remove('active-form');
    });

    btnProcessUrl.addEventListener('click', () => startProcess('url'));
    btnProcessText.addEventListener('click', () => startProcess('text'));

    document.getElementById('btn-new').addEventListener('click', () => {
        inputSection.classList.remove('hidden');
        loadingSection.classList.add('hidden');
        resultsSection.classList.add('hidden');

        document.getElementById('input-url').value = '';
        document.getElementById('input-text').value = '';

        // Reset state
        currentLoadedId = null;
        resultTitleNode.textContent = 'Resultados';

        // Reset toggle to URL default
        btnUrl.checked = true;
        formUrl.classList.add('active-form');
        formText.classList.remove('active-form');
    });

    // Modal Logic
    function openDeleteModal(id) {
        itemToDeleteId = id;
        deleteModal.classList.add('active');
    }

    function closeDeleteModal() {
        itemToDeleteId = null;
        deleteModal.classList.remove('active');
    }

    btnModalCancel.addEventListener('click', closeDeleteModal);

    btnModalConfirm.addEventListener('click', async () => {
        if (itemToDeleteId) {
            try {
                const res = await fetch(`/api/history/${itemToDeleteId}`, {
                    method: 'DELETE'
                });
                if (res.ok) {
                    history = history.filter(h => h.id !== itemToDeleteId);
                    renderHistory();
                    closeDeleteModal();

                    // If we deleted the currently viewed item, reset view
                    if (currentLoadedId === itemToDeleteId) {
                        currentLoadedId = null;
                        resultTitleNode.textContent = 'Resultados';
                        outputText.value = '';
                        resultsSection.classList.add('hidden');
                        inputSection.classList.remove('hidden');
                    }
                }
            } catch (e) {
                console.error("Error deleting item:", e);
                alert("Error eliminando elemento");
            }
        }
    });

    // Close modal if clicked outside
    deleteModal.addEventListener('click', (e) => {
        if (e.target === deleteModal) closeDeleteModal();
    });

    // Processes
    async function startProcess(type) {
        let content = '';
        if (type === 'url') {
            content = document.getElementById('input-url').value.trim();
        } else {
            content = document.getElementById('input-text').value.trim();
        }

        if (!content) {
            alert('Por favor ingresa contenido válido');
            return;
        }

        // Transition UI
        inputSection.classList.add('hidden');
        loadingSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');

        loadingText.textContent = 'Iniciando sistema...';

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, content })
            });

            if (!response.ok) throw new Error('Error en el servidor');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let finalOutput = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);

                        // Update loading text with process status
                        if (data.message) {
                            loadingText.textContent = data.message;
                        }

                        if (data.status === 'complete') {
                            finalOutput = data.data;
                            // Save via API
                            const newItem = await saveHistory(type, content, finalOutput);
                            if (newItem) {
                                loadHistoryItem(newItem);
                            }
                        } else if (data.status === 'error') {
                            loadingText.textContent = `Error: ${data.message}`;
                        }
                    } catch (e) {
                        console.error('JSON Parse error:', e);
                    }
                }
            }
        } catch (e) {
            loadingText.textContent = `Error de conexión: ${e.message}`;
            setTimeout(() => inputSection.classList.remove('hidden'), 2000);
        }
    }

    function showResult(text) {
        loadingSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        outputText.value = text;
    }

    async function saveHistory(type, inputContent, output) {
        const dateStr = new Date().toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });

        let title = "Sin título";

        if (type === 'url') {
            try {
                // Remove protocol
                let clean = inputContent.replace(/^https?:\/\//, '').replace(/^www\./, '');
                if (clean.endsWith('/')) clean = clean.slice(0, -1);

                const parts = clean.split('/');
                const domain = parts[0];
                const slug = parts.length > 1 ? parts[parts.length - 1] : '';

                // Domain + slug(10)
                const shortSlug = slug.substring(0, 10);
                title = `${domain}${shortSlug ? '/' + shortSlug : ''}`;
            } catch (e) {
                title = inputContent.substring(0, 20);
            }
        } else {
            const count = history.filter(h => h.title.includes('Sin título')).length + 1;
            title = `Sin título ${count}`;
        }

        try {
            const res = await fetch('/api/history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title,
                    date_str: dateStr,
                    full_input: inputContent,
                    output,
                    type
                })
            });

            if (res.ok) {
                const newItem = await res.json();
                history.unshift(newItem);
                renderHistory();
                return newItem;
            } else {
                throw new Error("Failed to save history");
            }
        } catch (e) {
            console.error("Save error:", e);
            alert("No se pudo guardar el historial en la nube");
            return null;
        }
    }

    // Track current loaded item
    let currentLoadedId = null;
    const resultTitleNode = document.getElementById('result-title');

    function loadHistoryItem(item) {
        currentLoadedId = item.id;
        inputSection.classList.add('hidden');
        loadingSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        outputText.value = item.output;
        resultTitleNode.textContent = item.title;
    }

    // Update renderHistory to handle sync
    function renderHistory() {
        historyList.innerHTML = '';
        const template = document.getElementById('history-item-template');

        history.forEach(item => {
            const clone = template.content.cloneNode(true);
            const li = clone.querySelector('li');
            const titleSpan = clone.querySelector('.item-title');

            titleSpan.textContent = item.title;
            clone.querySelector('.item-date').textContent = item.date_str || item.date; // handle potential migration

            // Load
            li.addEventListener('click', (e) => {
                // Ignore if clicking buttons or input
                if (e.target.closest('button') || e.target.closest('input')) return;
                loadHistoryItem(item);
            });

            // Delete
            const btnDelete = clone.querySelector('.delete-item');
            btnDelete.addEventListener('click', (e) => {
                e.stopPropagation();
                openDeleteModal(item.id);
            });

            // Edit
            const btnEdit = clone.querySelector('.edit-item');
            btnEdit.addEventListener('click', (e) => {
                e.stopPropagation();

                // If already editing, do nothing
                if (titleSpan.querySelector('input')) return;

                const currentTitle = item.title;
                const input = document.createElement('input');
                input.type = 'text';
                input.value = currentTitle;
                input.className = 'title-input';

                // Replace text with input
                titleSpan.textContent = '';
                titleSpan.appendChild(input);
                input.focus();

                // Prevent click on input from bubbling to item load
                input.addEventListener('click', (ev) => ev.stopPropagation());

                const saveEdit = async () => {
                    const newVal = input.value.trim();
                    if (newVal && newVal !== currentTitle) {
                        // PUT update
                        try {
                            const res = await fetch(`/api/history/${item.id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ title: newVal })
                            });

                            if (res.ok) {
                                item.title = newVal;
                                // If this item is currently displayed, update the header title
                                if (currentLoadedId === item.id) {
                                    resultTitleNode.textContent = newVal;
                                }
                            }
                        } catch (e) {
                            console.error("Update title error:", e);
                            alert("Error actualizando título");
                        }
                    }
                    renderHistory(); // Re-render to show plain text again
                };

                // Save on blur
                input.addEventListener('blur', saveEdit);

                // Save on Enter
                input.addEventListener('keydown', (ev) => {
                    if (ev.key === 'Enter') {
                        input.blur(); // Trigger blur
                    }
                });
            });

            historyList.appendChild(clone);
        });
    }

    // Settings Logic
    const settingsModal = document.getElementById('settings-modal');
    const btnSettings = document.getElementById('btn-settings');
    const btnCloseSettings = document.querySelector('.close-settings');
    const btnCancelSettings = document.getElementById('btn-cancel-settings');
    const btnSaveSettings = document.getElementById('btn-save-settings');

    const pOpenAISys = document.getElementById('p-openai-sys');
    const pOpenAIUser = document.getElementById('p-openai-user');
    const pAnthropicSys = document.getElementById('p-anthropic-sys');
    const pAnthropicUser = document.getElementById('p-anthropic-user');

    function openSettings() {
        settingsModal.classList.add('active');
        fetch('/api/prompts')
            .then(res => res.json())
            .then(data => {
                pOpenAISys.value = data.openai_system;
                pOpenAIUser.value = data.openai_user;
                pAnthropicSys.value = data.anthropic_system;
                pAnthropicUser.value = data.anthropic_user;
            })
            .catch(err => console.error('Error fetching prompts:', err));
    }

    function closeSettings() {
        settingsModal.classList.remove('active');
    }

    async function saveSettings() {
        const btn = btnSaveSettings;
        const originalText = btn.textContent;
        btn.textContent = 'Guardando...';
        btn.disabled = true;

        const data = {
            openai_system: pOpenAISys.value,
            openai_user: pOpenAIUser.value,
            anthropic_system: pAnthropicSys.value,
            anthropic_user: pAnthropicUser.value
        };

        try {
            const res = await fetch('/api/prompts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();

            if (result.status === 'success') {
                btn.textContent = '¡Guardado!';
                setTimeout(() => {
                    closeSettings();
                    btn.textContent = originalText;
                    btn.disabled = false;
                }, 1000);
            } else {
                throw new Error(result.message);
            }
        } catch (e) {
            alert('Error al guardar: ' + e.message);
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }

    btnSettings.addEventListener('click', openSettings);
    btnCloseSettings.addEventListener('click', closeSettings);
    btnCancelSettings.addEventListener('click', closeSettings);
    btnSaveSettings.addEventListener('click', saveSettings);

    // Close settings on outside click
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettings();
    });
});
