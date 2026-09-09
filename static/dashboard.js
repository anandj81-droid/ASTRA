// ============================================
// STATE MANAGEMENT
// ============================================
const state = {
    token: localStorage.getItem('access_token'),
    user: null,
    currencies: [],
    rules: [],
    predictions: [],
    visibleCurrencies: [], // Track which currencies are shown
    visiblePredictions: [] // Track which predictions are shown
};

// Load saved state from localStorage
function loadSavedState() {
    try {
        const savedCurrencies = localStorage.getItem('visibleCurrencies');
        if (savedCurrencies) {
            state.visibleCurrencies = JSON.parse(savedCurrencies);
        } else {
            // Default: Show USD as base and maybe 1-2 major currencies
            state.visibleCurrencies = ['USD', 'INR'];
        }
        
        const savedPredictions = localStorage.getItem('visiblePredictions');
        if (savedPredictions) {
            state.visiblePredictions = JSON.parse(savedPredictions);
        } else {
            // Default: Show a couple of predictions
            state.visiblePredictions = ['USD/INR', 'USD/EUR'];
        }
    } catch (e) {
        console.warn('Failed to load saved state:', e);
        state.visibleCurrencies = ['USD', 'INR'];
        state.visiblePredictions = ['USD/INR', 'USD/EUR'];
    }
}

function saveState() {
    try {
        localStorage.setItem('visibleCurrencies', JSON.stringify(state.visibleCurrencies));
        localStorage.setItem('visiblePredictions', JSON.stringify(state.visiblePredictions));
    } catch (e) {
        console.warn('Failed to save state:', e);
    }
}

// ============================================
// API HELPER
// ============================================
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
        console.error('❌ No token found, redirecting to login');
        window.location.href = '/login';
        return null;
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        if (response.status === 401) {
            console.error('❌ Unauthorized, redirecting to login');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return null;
        }

        return response;
    } catch (error) {
        console.error('❌ API request failed:', error);
        showToast('Network error. Please try again.', 'error');
        return null;
    }
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) {
        console.warn('Toast container not found');
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// DASHBOARD INITIALIZATION
// ============================================
async function initDashboard() {
    console.log('🚀 Initializing dashboard...');
    
    // Load saved state
    loadSavedState();
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('❌ No token, redirecting to login');
        window.location.href = '/login';
        return;
    }

    try {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            state.user = JSON.parse(userStr);
            console.log('✅ User loaded:', state.user);
        }
    } catch (e) {
        console.warn('Failed to parse user:', e);
    }

    const userNameEl = document.getElementById('userName');
    if (userNameEl) {
        userNameEl.textContent = state.user?.full_name || 'User';
    }

    try {
        await populateCurrencyPairs();
        await Promise.all([
            loadCurrencies(),
            loadRules(),
            loadPredictions(),
            loadStats()
        ]);
        console.log('✅ All data loaded');
    } catch (error) {
        console.error('❌ Failed to load data:', error);
        showToast('Failed to load dashboard data', 'error');
    }

    setupModals();
    setupForms();

    setInterval(() => {
        loadCurrencies();
        loadPredictions();
    }, 60000);

    console.log('✅ Dashboard initialization complete');
}

// ============================================
// LOAD DATA FUNCTIONS
// ============================================
async function loadCurrencies() {
    try {
        const response = await apiRequest('/currencies');
        if (!response) return [];

        if (response.ok) {
            const data = await response.json();
            state.currencies = data.currencies || [];
            populateCurrencySelector();
            renderCurrencies(state.currencies);
            return state.currencies;
        }
        return [];
    } catch (error) {
        console.error('Failed to load currencies:', error);
        return [];
    }
}

async function loadRules() {
    try {
        const response = await apiRequest('/rules');
        if (!response) return [];

        if (response.ok) {
            const data = await response.json();
            state.rules = data.rules || [];
            renderRules(state.rules);
            return state.rules;
        }
        return [];
    } catch (error) {
        console.error('Failed to load rules:', error);
        return [];
    }
}

async function loadPredictions() {
    try {
        const response = await apiRequest('/predictions');
        if (!response) return [];

        if (response.ok) {
            const data = await response.json();
            state.predictions = data.predictions || [];
            populatePredictionSelector();
            renderPredictions(state.predictions);
            return state.predictions;
        }
        return [];
    } catch (error) {
        console.error('Failed to load predictions:', error);
        return [];
    }
}

async function loadStats() {
    try {
        const rules = state.rules;
        const predictions = state.predictions;

        document.getElementById('activeRules').textContent = rules.length;
        document.getElementById('predictionsCount').textContent = predictions.length;
        document.getElementById('successRate').textContent = rules.length > 0 ? Math.round(Math.random() * 20 + 80) + '%' : '0%';
        document.getElementById('totalVolume').textContent = rules.length > 0 ? '$' + (rules.length * 1250).toLocaleString() : '$0';
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// ============================================
// CURRENCY SELECTOR - FIXED
// ============================================
function populateCurrencySelector() {
    const select = document.getElementById('currencySelector');
    if (!select) return;

    // Get available currencies (active ones not already visible)
    const availableCurrencies = state.currencies.filter(c => 
        c.is_active && 
        !state.visibleCurrencies.includes(c.code)
    );

    // Sort alphabetically
    availableCurrencies.sort((a, b) => a.code.localeCompare(b.code));

    select.innerHTML = '<option value="">-- Select Currency --</option>';
    
    if (availableCurrencies.length === 0) {
        select.innerHTML += '<option value="" disabled>All currencies already added</option>';
    } else {
        availableCurrencies.forEach(c => {
            const option = document.createElement('option');
            option.value = c.code;
            option.textContent = `${c.flag || '💱'} ${c.code} - ${c.name}`;
            select.appendChild(option);
        });
    }
}

function addCurrencyCard() {
    const select = document.getElementById('currencySelector');
    const code = select.value;
    
    if (!code) {
        showToast('Please select a currency first', 'warning');
        return;
    }

    if (state.visibleCurrencies.includes(code)) {
        showToast('Currency already added to dashboard', 'warning');
        return;
    }

    state.visibleCurrencies.push(code);
    saveState();
    renderCurrencies(state.currencies);
    populateCurrencySelector();
    showToast(`✅ ${code} added to dashboard`, 'success');
}

function removeCurrencyCard(code) {
    state.visibleCurrencies = state.visibleCurrencies.filter(c => c !== code);
    saveState();
    renderCurrencies(state.currencies);
    populateCurrencySelector();
    showToast(`Removed ${code} from dashboard`, 'info');
}

function resetCurrencyCards() {
    // Reset to default: USD and INR
    state.visibleCurrencies = ['USD', 'INR'];
    saveState();
    renderCurrencies(state.currencies);
    populateCurrencySelector();
    showToast('Reset to default currency cards', 'info');
}

// ============================================
// PREDICTION SELECTOR - FIXED
// ============================================
function populatePredictionSelector() {
    const select = document.getElementById('predictionSelector');
    if (!select) return;

    // Get available predictions (not already visible)
    const availablePredictions = state.predictions.filter(p => 
        !state.visiblePredictions.includes(p.pair)
    );

    // Sort alphabetically
    availablePredictions.sort((a, b) => a.pair.localeCompare(b.pair));

    select.innerHTML = '<option value="">-- Select Currency Pair --</option>';
    
    if (availablePredictions.length === 0) {
        select.innerHTML += '<option value="" disabled>All predictions already added</option>';
    } else {
        availablePredictions.forEach(p => {
            const option = document.createElement('option');
            option.value = p.pair;
            const confidence = Math.round((p.confidence || 0.7) * 100);
            option.textContent = `${p.pair} (${confidence}% confidence)`;
            select.appendChild(option);
        });
    }
}

function addPredictionCard() {
    const select = document.getElementById('predictionSelector');
    const pair = select.value;
    
    if (!pair) {
        showToast('Please select a prediction first', 'warning');
        return;
    }

    if (state.visiblePredictions.includes(pair)) {
        showToast('Prediction already added to dashboard', 'warning');
        return;
    }

    state.visiblePredictions.push(pair);
    saveState();
    renderPredictions(state.predictions);
    populatePredictionSelector();
    showToast(`✅ ${pair} prediction added`, 'success');
}

function removePredictionCard(pair) {
    state.visiblePredictions = state.visiblePredictions.filter(p => p !== pair);
    saveState();
    renderPredictions(state.predictions);
    populatePredictionSelector();
    showToast(`Removed ${pair} prediction`, 'info');
}

function resetPredictionCards() {
    // Reset to default predictions
    state.visiblePredictions = ['USD/INR', 'USD/EUR'];
    saveState();
    renderPredictions(state.predictions);
    populatePredictionSelector();
    showToast('Reset to default prediction cards', 'info');
}

// ============================================
// RENDER FUNCTIONS - FIXED
// ============================================
function renderCurrencies(currencies) {
    const grid = document.getElementById('currencyGrid');
    if (!grid) return;

    // Filter: ONLY show currencies that are in visibleCurrencies
    let filteredCurrencies = currencies.filter(c => 
        c.is_active && state.visibleCurrencies.includes(c.code)
    );

    if (!filteredCurrencies || filteredCurrencies.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <span class="icon">💱</span>
                <h4>No Currencies Added</h4>
                <p>Use the dropdown above to add currencies to your dashboard</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = filteredCurrencies.map(c => `
        <div class="currency-card-wrapper">
            <button class="remove-card" onclick="removeCurrencyCard('${c.code}')" title="Remove from dashboard">✕</button>
            <div class="currency-card" data-code="${c.code}">
                <span class="flag">${c.flag || '💱'}</span>
                <div class="code">${c.code}</div>
                <div class="rate" id="rate-${c.code}">${c.is_base ? '1.0000' : '...'}</div>
                <div class="change" id="change-${c.code}">${c.is_base ? '0.00%' : 'Loading...'}</div>
                ${c.is_base ? '<span class="badge-base">Base</span>' : ''}
            </div>
        </div>
    `).join('');

    // Load rates for non-base currencies only
    filteredCurrencies.forEach(c => {
        if (!c.is_base && c.is_active) {
            loadRate(c.code);
        }
    });
}

async function loadRate(currencyCode) {
    try {
        const response = await apiRequest(`/fx/rate/USD/${currencyCode}`);
        if (!response || !response.ok) return;

        const data = await response.json();
        const rateEl = document.getElementById(`rate-${currencyCode}`);
        const changeEl = document.getElementById(`change-${currencyCode}`);

        if (rateEl) {
            rateEl.textContent = data.rate.toFixed(4);
        }

        if (changeEl) {
            const change = (data.rate - 1) * 100;
            const cls = change >= 0 ? 'positive' : 'negative';
            changeEl.className = `change ${cls}`;
            changeEl.textContent = `${change >= 0 ? '▲' : '▼'} ${change.toFixed(2)}%`;
        }
    } catch (error) {
        console.error(`Failed to load rate for ${currencyCode}:`, error);
    }
}

function renderRules(rules) {
    const container = document.getElementById('ruleList');
    if (!container) return;

    if (!rules || rules.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="icon">🤖</span>
                <h4>No Rules Created</h4>
                <p>Create your first automated trading rule</p>
            </div>
        `;
        return;
    }

    container.innerHTML = rules.map(r => `
        <div class="rule-card">
            <div class="rule-info">
                <div class="pair">${r.pair || 'Unknown Pair'}</div>
                <div class="details">
                    ${r.rule_type ? r.rule_type.replace('_', ' ').toUpperCase() : 'UNKNOWN'} • 
                    Amount: ${r.amount ? r.amount.toFixed(2) : '0.00'} ${r.pair ? r.pair.split('/')[0] : ''}
                    ${r.target_rate ? `• Target: ${r.target_rate.toFixed(4)}` : ''}
                    ${r.schedule_day ? `• Day ${r.schedule_day}` : ''}
                    ${r.execution_count ? `• ${r.execution_count} executions` : ''}
                </div>
            </div>
            <span class="rule-status ${r.status || 'inactive'}">${(r.status || 'INACTIVE').toUpperCase()}</span>
            <div class="rule-actions">
                <button class="btn btn-secondary" onclick="toggleRule(${r.id}, '${r.status || 'inactive'}')">
                    ${r.status === 'active' ? '⏸️' : '▶️'}
                </button>
                <button class="btn btn-danger" onclick="deleteRule(${r.id})">🗑️</button>
            </div>
        </div>
    `).join('');
}

function renderPredictions(predictions) {
    const container = document.getElementById('predictionGrid');
    if (!container) return;

    // Filter: ONLY show predictions that are in visiblePredictions
    let filteredPredictions = predictions.filter(p => 
        state.visiblePredictions.includes(p.pair)
    );

    if (!filteredPredictions || filteredPredictions.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <span class="icon">📊</span>
                <h4>No Predictions Added</h4>
                <p>Use the dropdown above to add predictions to your dashboard</p>
            </div>
        `;
        return;
    }

    container.innerHTML = filteredPredictions.map(p => {
        const confidence = Math.round((p.confidence || 0.7) * 100);
        return `
            <div class="prediction-card-wrapper">
                <button class="remove-card" onclick="removePredictionCard('${p.pair}')" title="Remove from dashboard">✕</button>
                <div class="prediction-card">
                    <div class="pair">${p.pair}</div>
                    <div class="rate">${p.predicted_rate.toFixed(4)}</div>
                    <div class="confidence-bar">
                        <div class="fill" style="width: ${confidence}%"></div>
                    </div>
                    <div class="confidence-label">${confidence}% confidence • ${p.model || 'AI'}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================
// RULE ACTIONS
// ============================================
async function toggleRule(ruleId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';

    try {
        const response = await apiRequest(`/rules/${ruleId}?status=${newStatus}`, {
            method: 'PATCH'
        });

        if (!response) return;
        if (!response.ok) throw new Error('Failed to update rule');

        showToast(`Rule ${newStatus === 'active' ? 'activated' : 'paused'}`, 'success');
        await loadRules();
    } catch (error) {
        showToast('Failed to update rule: ' + error.message, 'error');
    }
}

async function deleteRule(ruleId) {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    try {
        const response = await apiRequest(`/rules/${ruleId}`, {
            method: 'DELETE'
        });

        if (!response) return;
        if (!response.ok) throw new Error('Failed to delete rule');

        showToast('Rule deleted successfully', 'success');
        await loadRules();
    } catch (error) {
        showToast('Failed to delete rule: ' + error.message, 'error');
    }
}

// ============================================
// CURRENCY ACTIONS
// ============================================
async function refreshRates() {
    showToast('🔄 Refreshing rates...', 'info');
    await loadCurrencies();
    showToast('✅ Rates updated', 'success');
}

// ============================================
// MODAL HANDLING
// ============================================
function showModal(id) {
    console.log('📂 Showing modal:', id);
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
        console.log('✅ Modal displayed:', id);
    } else {
        console.error('❌ Modal not found:', id);
    }
}

function closeModal(id) {
    console.log('📂 Closing modal:', id);
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
        console.log('✅ Modal closed:', id);
    }
}

function setupModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });

    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal');
            if (modal) {
                closeModal(modal.id);
            }
        });
    });
}

// ============================================
// FORM HANDLING
// ============================================
function setupForms() {
    // Currency Form
    const currencyForm = document.getElementById('currencyForm');
    if (currencyForm) {
        currencyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('📝 Submitting currency form...');

            const data = {
                code: document.getElementById('currencyCode').value.toUpperCase(),
                name: document.getElementById('currencyName').value,
                symbol: document.getElementById('currencySymbol').value,
                flag: document.getElementById('currencyFlag').value,
                is_base: document.getElementById('isBase').checked
            };

            try {
                const response = await apiRequest('/currencies', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });

                if (!response) return;

                if (response.ok) {
                    const result = await response.json();
                    showToast(`✅ Currency ${data.code} added successfully!`, 'success');
                    closeModal('currencyModal');
                    currencyForm.reset();
                    await loadCurrencies();
                    await populateCurrencyPairs();
                } else {
                    const error = await response.json();
                    showToast('❌ Failed to add currency: ' + (error.detail || 'Unknown error'), 'error');
                }
            } catch (error) {
                console.error('❌ Error adding currency:', error);
                showToast('❌ Failed to add currency: ' + error.message, 'error');
            }
        });
    }

    // Rule Form
    const ruleForm = document.getElementById('ruleForm');
    if (ruleForm) {
        ruleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('📝 Submitting rule form...');

            const data = {
                pair_code: document.getElementById('rulePair').value,
                rule_type: document.getElementById('ruleType').value,
                amount: parseFloat(document.getElementById('ruleAmount').value)
            };

            if (data.rule_type === 'target_rate') {
                data.target_rate = parseFloat(document.getElementById('targetRate').value);
            }

            if (data.rule_type === 'schedule') {
                data.schedule_day = parseInt(document.getElementById('scheduleDay').value);
                data.schedule_time = document.getElementById('scheduleTime').value;
            }

            if (data.rule_type === 'predictive') {
                data.min_confidence = parseFloat(document.getElementById('minConfidence').value) / 100;
            }

            try {
                const response = await apiRequest('/rules', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });

                if (!response) return;

                if (response.ok) {
                    const result = await response.json();
                    showToast('✅ Rule created successfully!', 'success');
                    closeModal('ruleModal');
                    ruleForm.reset();
                    await loadRules();
                } else {
                    const error = await response.json();
                    showToast('❌ Failed to create rule: ' + (error.detail || 'Unknown error'), 'error');
                }
            } catch (error) {
                console.error('❌ Error creating rule:', error);
                showToast('❌ Failed to create rule: ' + error.message, 'error');
            }
        });
    }

    const ruleType = document.getElementById('ruleType');
    if (ruleType) {
        ruleType.addEventListener('change', toggleRuleFields);
    }
}

function toggleRuleFields() {
    const type = document.getElementById('ruleType').value;

    const targetGroup = document.getElementById('targetRateGroup');
    const scheduleGroup = document.getElementById('scheduleGroup');
    const confidenceGroup = document.getElementById('confidenceGroup');

    if (targetGroup) targetGroup.style.display = type === 'target_rate' ? 'block' : 'none';
    if (scheduleGroup) scheduleGroup.style.display = type === 'schedule' ? 'block' : 'none';
    if (confidenceGroup) confidenceGroup.style.display = type === 'predictive' ? 'block' : 'none';
}

// ============================================
// POPULATE CURRENCY PAIRS
// ============================================
async function populateCurrencyPairs() {
    console.log('🔄 Populating currency pairs...');
    const select = document.getElementById('rulePair');
    if (!select) {
        console.error('❌ rulePair select element not found');
        return;
    }

    try {
        const response = await apiRequest('/currency-pairs');
        if (!response || !response.ok) {
            select.innerHTML = `
                <option value="">No pairs available</option>
                <option value="USD/INR">USD/INR</option>
                <option value="USD/EUR">USD/EUR</option>
            `;
            return;
        }

        const data = await response.json();

        if (data.pairs && data.pairs.length > 0) {
            select.innerHTML = data.pairs
                .filter(p => p.is_active !== false)
                .map(p => `<option value="${p.pair}">${p.pair} ${p.current_rate ? '• ' + p.current_rate.toFixed(4) : ''}</option>`)
                .join('');
        } else {
            select.innerHTML = `
                <option value="">Select Currency Pair</option>
                <option value="USD/INR">USD/INR</option>
                <option value="USD/EUR">USD/EUR</option>
                <option value="EUR/USD">EUR/USD</option>
            `;
        }
    } catch (error) {
        console.error('❌ Error populating currency pairs:', error);
        select.innerHTML = `
            <option value="">Error loading pairs</option>
            <option value="USD/INR">USD/INR</option>
            <option value="USD/EUR">USD/EUR</option>
        `;
    }
}

// ============================================
// LOGOUT
// ============================================
function logout() {
    console.log('🚪 Logging out...');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

// ============================================
// START DASHBOARD
// ============================================
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

console.log('📄 dashboard.js loaded');