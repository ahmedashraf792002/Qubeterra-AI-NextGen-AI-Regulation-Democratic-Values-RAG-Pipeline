let selectedProvider = 'ollama';
let chatHistory = [];

// === Init ===
async function init() {
    await loadProviders();
    await loadPersonas();
}

async function loadProviders() {
    const resp = await fetch('/api/providers');
    const data = await resp.json();
    const div = document.getElementById('providers');
    div.innerHTML = '';
    for (const [key, info] of Object.entries(data)) {
        const btn = document.createElement('button');
        btn.className = 'provider-btn' + (key === selectedProvider ? ' active' : '');
        btn.textContent = info.description;
        btn.onclick = () => selectProvider(key, btn);
        div.appendChild(btn);
    }
}

function selectProvider(key, btn) {
    selectedProvider = key;
    document.querySelectorAll('.provider-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

async function loadPersonas() {
    const resp = await fetch('/api/personas');
    const personas = await resp.json();

    document.getElementById('persona-checkboxes').innerHTML = personas.map(p =>
        `<label><input type="checkbox" value="${p.id}" class="persona-cb" checked> ${p.name} <span style="color:#aaa;font-size:12px">(${p.id})</span></label>`
    ).join('');

    document.getElementById('chat-persona').innerHTML = personas.map(p =>
        `<option value="${p.id}">${p.name}</option>`
    ).join('');
}

// === Tabs ===
function showTab(tab, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(tab).classList.remove('hidden');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
}

// === Pipeline ===
async function runPipeline() {
    const steps = [...document.querySelectorAll('.step-cb:checked')].map(cb => parseInt(cb.value));
    if (!steps.length) return alert('Select at least one step');
    const out = document.getElementById('pipeline-output');
    out.innerHTML = '<span class="loading"></span> Running...';
    try {
        const resp = await fetch('/api/pipeline/run', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({steps})
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            out.innerHTML = `<div class="result-card error"><h3>Pipeline Error</h3><div class="text">${err.detail || resp.statusText}</div></div>`;
            return;
        }
        const data = await resp.json();
        out.innerHTML = data.results.map(r =>
            `<div class="result-card ${r.status === 'ok' ? 'ok' : 'error'}">
                <h3>Step ${r.step} ${r.name || ''}</h3>
                <div class="meta">${r.status}</div>
                ${r.output ? `<pre class="text">${r.output}</pre>` : ''}
                ${r.error ? `<pre class="text" style="color:red">${r.error}</pre>` : ''}
            </div>`
        ).join('');
    } catch (e) {
        out.innerHTML = `<div class="result-card error"><h3>Network Error</h3><div class="text">${e.message}</div></div>`;
    }
}

// === Search ===
async function searchKB() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) return alert('Please enter a search query');
    const category = document.getElementById('search-category').value;
    let top_k = parseInt(document.getElementById('search-topk').value);
    if (isNaN(top_k) || top_k < 1) top_k = 5;
    if (top_k > 50) top_k = 50;
    const out = document.getElementById('search-results');
    out.innerHTML = '<span class="loading"></span> Searching...';
    try {
        const resp = await fetch('/api/search', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query, top_k, category})
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            out.innerHTML = `<div class="result-card error"><h3>Search Error</h3><div class="text">${err.detail || resp.statusText}</div></div>`;
            return;
        }
        const data = await resp.json();
        if (!data.results || !data.results.length) {
            out.innerHTML = '<p style="color:#888">No results found</p>';
            return;
        }
        out.innerHTML = data.results.map((r, i) => {
            const sim = r.similarity || 0;
            const simClass = sim >= 0.8 ? 'high' : sim >= 0.6 ? 'medium' : 'low';
            return `<div class="result-card ok">
                <h3>[${i+1}] ${r.title || 'Untitled'}</h3>
                <div class="meta">${r.url || ''} — <span class="similarity ${simClass}">${sim.toFixed(4)}</span></div>
                <div class="text">${(r.text||'').substring(0, 300)}${(r.text||'').length > 300 ? '...' : ''}</div>
            </div>`;
        }).join('');
    } catch (e) {
        out.innerHTML = `<div class="result-card error"><h3>Network Error</h3><div class="text">${e.message}</div></div>`;
    }
}

// === Scrape ===
async function scrapeURL() {
    const url = document.getElementById('scrape-url').value.trim();
    if (!url) return alert('Please enter a URL');
    const out = document.getElementById('scrape-output');
    out.innerHTML = '<span class="loading"></span> Scraping...';
    try {
        const resp = await fetch('/api/scrape', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url})
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            out.innerHTML = `<div class="result-card error"><h3>Scrape Error</h3><div class="text">${err.detail || resp.statusText}</div></div>`;
            return;
        }
        const data = await resp.json();
        if (!data.results || !data.results.length) {
            out.innerHTML = '<p style="color:#888">No content extracted</p>';
            return;
        }
        out.innerHTML = data.results.map(r =>
            `<div class="result-card ${r.status === 'ok' ? 'ok' : 'error'}">
                <h3>${r.url || 'Unknown'}</h3>
                <div class="meta">${r.status}</div>
                <div class="text">${(r.text||'').substring(0, 500)}${r.text && r.text.length > 500 ? '...' : ''}</div>
            </div>`
        ).join('');
    } catch (e) {
        out.innerHTML = `<div class="result-card error"><h3>Network Error</h3><div class="text">${e.message}</div></div>`;
    }
}

async function scrapeQuery() {
    const text_query = document.getElementById('scrape-query').value.trim();
    if (!text_query) return alert('Please enter a search query');
    const out = document.getElementById('scrape-output');
    out.innerHTML = '<span class="loading"></span> Searching & scraping...';
    try {
        const resp = await fetch('/api/scrape', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text_query})
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            out.innerHTML = `<div class="result-card error"><h3>Scrape Error</h3><div class="text">${err.detail || resp.statusText}</div></div>`;
            return;
        }
        const data = await resp.json();
        if (!data.results || !data.results.length) {
            out.innerHTML = '<p style="color:#888">No documents found</p>';
            return;
        }
        out.innerHTML = `<p style="color:#888;font-size:13px;margin-bottom:8px">Found ${data.count} documents</p>` +
            data.results.map(r =>
            `<div class="result-card ${r.status === 'ok' ? 'ok' : 'error'}">
                <h3>${r.url || 'Unknown'}</h3>
                <div class="meta">${r.status}</div>
                <div class="text">${(r.text||'').substring(0, 500)}${r.text && r.text.length > 500 ? '...' : ''}</div>
            </div>`
        ).join('');
    } catch (e) {
        out.innerHTML = `<div class="result-card error"><h3>Network Error</h3><div class="text">${e.message}</div></div>`;
    }
}

// === Opinions ===
async function generateOpinions() {
    const topic = document.getElementById('opinion-topic').value.trim();
    const persona_ids = [...document.querySelectorAll('.persona-cb:checked')].map(cb => cb.value);
    if (!topic) return alert('Enter a topic');
    if (!persona_ids.length) return alert('Select at least one agent');
    const out = document.getElementById('opinions-output');
    out.innerHTML = '<span class="loading"></span> Generating opinions...';
    try {
        const resp = await fetch('/api/opinion', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({topic, persona_ids, provider: selectedProvider})
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            out.innerHTML = `<div class="result-card error"><h3>Error</h3><div class="text">${err.detail || resp.statusText}</div></div>`;
            return;
        }
        const data = await resp.json();
        if (!data.opinions || !data.opinions.length) {
            out.innerHTML = '<p style="color:#888">No opinions generated</p>';
            return;
        }
        out.innerHTML = data.opinions.map(o =>
            `<div class="opinion-box">
                <h3>${o.persona || 'Unknown'}</h3>
                ${o.tool_used ? `<span class="tool-badge">${o.tool_used}</span>` : ''}
                <div class="text">${o.opinion || 'No opinion'}</div>
                ${o.sources && o.sources.length ? `<div class="sources">Sources: ${o.sources.map(s => `<a href="${s.url}" target="_blank">${s.title}</a>`).join(', ')}</div>` : ''}
            </div>`
        ).join('');
    } catch (e) {
        out.innerHTML = `<div class="result-card error"><h3>Network Error</h3><div class="text">${e.message}</div></div>`;
    }
}

// === Chat ===
async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    const persona_id = document.getElementById('chat-persona').value;
    const box = document.getElementById('chat-history');

    box.innerHTML += `<div class="chat-msg user"><div class="bubble">${msg}</div></div>`;
    input.value = '';
    box.innerHTML += `<div class="chat-msg assistant" id="typing"><div class="bubble"><span class="loading"></span></div></div>`;
    box.scrollTop = box.scrollHeight;

    chatHistory.push({role: 'user', content: msg});

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg, persona_id, provider: selectedProvider, history: chatHistory.slice(-10)})
        });
        document.getElementById('typing')?.remove();
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            box.innerHTML += `<div class="chat-msg assistant"><div class="bubble" style="color:#dc2626">Error: ${err.detail || err.error || resp.statusText}</div></div>`;
        } else {
            const data = await resp.json();
            const toolBadge = data.tool_used ? `<span class="tool-badge">${data.tool_used}</span>` : '';
            box.innerHTML += `<div class="chat-msg assistant"><div class="bubble">${toolBadge}${data.response || 'No response'}</div></div>`;
            chatHistory.push({role: 'assistant', content: data.response});
        }
    } catch (e) {
        document.getElementById('typing')?.remove();
        box.innerHTML += `<div class="chat-msg assistant"><div class="bubble" style="color:#dc2626">Network Error: ${e.message}</div></div>`;
    }
    box.scrollTop = box.scrollHeight;
}

init();
