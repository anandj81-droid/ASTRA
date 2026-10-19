// ──────────────────────────────────────────────────────────────
// 1. DASHBOARD INITIALIZATION
// ──────────────────────────────────────────────────────────────

let currentToken = localStorage.getItem('access_token');
let refreshInterval = null;

async function initDashboard() {
    if (!currentToken) {
        window.location.href = '/login';
        return;
    }
    
    // Start refresh interval (every 1 hour)
    refreshInterval = setInterval(refreshAll, 3600000); // 1 hour
    
    // Initial load
    await refreshAll();
    
    // Start onboarding tour
    if (!localStorage.getItem('onboarding_completed')) {
        startOnboarding();
    }
}

async function refreshAll() {
    try {
        await Promise.all([
            loadCurrencies(),
            loadRules(),
            loadPredictions(),
            loadStats()
        ]);
    } catch (error) {
        console.error('Refresh failed:', error);
    }
}

// ──────────────────────────────────────────────────────────────
// 2. CURRENCY MANAGEMENT
// ──────────────────────────────────────────────────────────────

async function loadCurrencies() {
    const response = await fetch('/currencies', {
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (!response.ok) throw new Error('Failed to load currencies');
    
    const data = await response.json();
    renderCurrencies(data.currencies);
}

function renderCurrencies(currencies) {
    const grid = document.getElementById('currency-grid');
    grid.innerHTML = currencies
        .filter(c => c.is_active)
        .map(c => `
            <div class="currency-card bg-white p-4 rounded-lg shadow hover:shadow-lg transition">
                <div class="flex items-center justify-between">
                    <div>
                        <span class="text-2xl">${c.flag || '💱'}</span>
                        <span class="font-bold ml-2">${c.code}</span>
                    </div>
                    <span class="text-sm ${c.is_base ? 'text-blue-500' : 'text-gray-500'}">
                        ${c.is_base ? '⭐ Base' : ''}
                    </span>
                </div>
                <div class="mt-2">
                    <div class="text-lg font-bold" id="rate-${c.code}">
                        ${c.code === 'USD' ? '1.0000' : '...'}
                    </div>
                    <div class="text-sm text-gray-500" id="change-${c.code}">
                        Loading...
                    </div>
                </div>
            </div>
        `).join('');
    
    // Load rates for each currency
    currencies.forEach(c => {
        if (c.code !== 'USD') {
            loadRate(c.code);
        }
    });
}

async function loadRate(currencyCode) {
    try {
        const response = await fetch(`/fx/rate/USD/${currencyCode}`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            const rateElement = document.getElementById(`rate-${currencyCode}`);
            const changeElement = document.getElementById(`change-${currencyCode}`);
            
            if (rateElement) {
                rateElement.textContent = data.rate.toFixed(4);
            }
            
            if (changeElement) {
                const change = (data.rate - 1) * 100;
                changeElement.innerHTML = `
                    <span class="${change >= 0 ? 'text-green-500' : 'text-red-500'}">
                        ${change >= 0 ? '▲' : '▼'} ${change.toFixed(2)}%
                    </span>
                `;
            }
        }
    } catch (error) {
        console.error(`Failed to load rate for ${currencyCode}:`, error);
    }
}

// Add Currency
document.getElementById('currencyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        code: document.getElementById('currencyCode').value.toUpperCase(),
        name: document.getElementById('currencyName').value,
        symbol: document.getElementById('currencySymbol').value,
        flag: document.getElementById('currencyFlag').value,
        is_base: document.getElementById('isBase').checked
    };
    
    try {
        const response = await fetch('/currencies', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) throw new Error('Failed to add currency');
        
        const result = await response.json();
        showNotification(`✅ Currency ${data.code} added successfully!`, 'success');
        closeModal('currencyModal');
        
        // Refresh dashboard
        await loadCurrencies();
        
        // Show backfill status
        if (result.pairs_created.length > 0) {
            showNotification(`📊 Historical data backfill started for ${result.pairs_created.length} pairs`, 'info');
        }
        
    } catch (error) {
        showNotification('❌ Failed to add currency: ' + error.message, 'error');
    }
});

// ──────────────────────────────────────────────────────────────
// 3. RULE MANAGEMENT
// ──────────────────────────────────────────────────────────────

async function loadRules() {
    const response = await fetch('/rules', {
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (!response.ok) throw new Error('Failed to load rules');
    
    const data = await response.json();
    renderRules(data.rules);
}

function renderRules(rules) {
    const container = document.getElementById('rule-list');
    
    if (rules.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <p class="text-2xl mb-2">🤖</p>
                <p>No rules created yet. Create your first rule!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = rules.map(r => `
        <div class="rule-card bg-white p-4 rounded-lg shadow hover:shadow-md transition">
            <div class="flex justify-between items-start">
                <div>
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-lg">${r.pair}</span>
                        <span class="text-sm px-2 py-1 rounded ${getStatusClass(r.status)}">
                            ${r.status.toUpperCase()}
                        </span>
                    </div>
                    <div class="text-sm text-gray-600 mt-1">
                        Type: ${r.rule_type.replace('_', ' ').toUpperCase()}
                    </div>
                    <div class="text-sm text-gray-600">
                        Amount: ${r.amount.toFixed(2)} ${r.pair.split('/')[0]}
                    </div>
                    ${r.target_rate ? `
                        <div class="text-sm text-gray-600">
                            Target Rate: ${r.target_rate.toFixed(4)}
                        </div>
                    ` : ''}
                    ${r.schedule_day ? `
                        <div class="text-sm text-gray-600">
                            Schedule: Day ${r.schedule_day} at ${r.schedule_time || '00:00'}
                        </div>
                    ` : ''}
                    <div class="text-xs text-gray-400 mt-2">
                        Executions: ${r.execution_count} | 
                        Created: ${new Date(r.created_at).toLocaleDateString()}
                    </div>
                </div>
                <div class="flex flex-col gap-1">
                    <button onclick="toggleRuleStatus(${r.id}, '${r.status}')" 
                            class="text-sm px-3 py-1 rounded ${r.status === 'active' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}">
                        ${r.status === 'active' ? '⏸️ Pause' : '▶️ Activate'}
                    </button>
                    <button onclick="deleteRule(${r.id})" 
                            class="text-sm px-3 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200">
                        🗑️ Delete
                    </button>
                    <button onclick="viewRuleDetails(${r.id})" 
                            class="text-sm px-3 py-1 rounded bg-blue-100 text-blue-700 hover:bg-blue-200">
                        📊 Details
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function getStatusClass(status) {
    const classes = {
        'active': 'bg-green-100 text-green-700',
        'paused': 'bg-yellow-100 text-yellow-700',
        'inactive': 'bg-gray-100 text-gray-700',
        'completed': 'bg-blue-100 text-blue-700',
        'failed': 'bg-red-100 text-red-700'
    };
    return classes[status] || 'bg-gray-100 text-gray-700';
}

async function toggleRuleStatus(ruleId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';
    
    try {
        const response = await fetch(`/rules/${ruleId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) throw new Error('Failed to update rule');
        
        await loadRules();
        showNotification(`✅ Rule ${newStatus === 'active' ? 'activated' : 'paused'}`, 'success');
    } catch (error) {
        showNotification('❌ Failed to update rule: ' + error.message, 'error');
    }
}

async function deleteRule(ruleId) {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    
    try {
        const response = await fetch(`/rules/${ruleId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (!response.ok) throw new Error('Failed to delete rule');
        
        await loadRules();
        showNotification('✅ Rule deleted successfully', 'success');
    } catch (error) {
        showNotification('❌ Failed to delete rule: ' + error.message, 'error');
    }
}

// Create Rule
document.getElementById('ruleForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const pairCode = document.getElementById('rulePair').value;
    const ruleType = document.getElementById('ruleType').value;
    const amount = parseFloat(document.getElementById('ruleAmount').value);
    
    const data = {
        pair_code: pairCode,
        rule_type: ruleType,
        amount: amount
    };
    
    if (ruleType === 'target_rate') {
        data.target_rate = parseFloat(document.getElementById('targetRate').value);
    }
    
    if (ruleType === 'schedule') {
        data.schedule_day = parseInt(document.getElementById('scheduleDay').value);
        data.schedule_time = document.getElementById('scheduleTime').value;
    }
    
    if (ruleType === 'predictive') {
        data.min_confidence = parseFloat(document.getElementById('minConfidence').value) / 100;
        data.prediction_horizon = '24h';
    }
    
    try {
        const response = await fetch('/rules', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) throw new Error('Failed to create rule');
        
        const result = await response.json();
        showNotification('✅ Rule created successfully!', 'success');
        closeModal('ruleModal');
        await loadRules();
        
    } catch (error) {
        showNotification('❌ Failed to create rule: ' + error.message, 'error');
    }
});

// ──────────────────────────────────────────────────────────────
// 4. PREDICTIONS
// ──────────────────────────────────────────────────────────────

async function loadPredictions() {
    try {
        const response = await fetch('/predictions/all', {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (!response.ok) throw new Error('Failed to load predictions');
        
        const data = await response.json();
        renderPredictions(data.predictions);
    } catch (error) {
        console.error('Failed to load predictions:', error);
    }
}

function renderPredictions(predictions) {
    const container = document.getElementById('prediction-grid');
    
    if (!predictions || predictions.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-8 text-gray-500">
                <p>No predictions available. Please wait for model training...</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = predictions.map(p => {
        const confidencePercent = (p.confidence * 100).toFixed(0);
        const confidenceColor = p.confidence >= 0.8 ? 'green' : 
                               p.confidence >= 0.6 ? 'yellow' : 'red';
        
        return `
            <div class="prediction-card bg-white p-4 rounded-lg shadow hover:shadow-md transition">
                <div class="flex justify-between items-start">
                    <div>
                        <span class="font-bold text-lg">${p.pair}</span>
                    </div>
                    <span class="text-sm px-2 py-1 rounded bg-blue-100 text-blue-700">
                        ${confidencePercent}% confidence
                    </span>
                </div>
                <div class="mt-3">
                    <div class="text-2xl font-bold text-blue-600">
                        ${p.predicted_rate.toFixed(4)}
                    </div>
                    <div class="text-sm text-gray-500">
                        Predicted Rate
                    </div>
                </div>
                <div class="mt-2">
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-${confidenceColor}-500 h-2 rounded-full" 
                             style="width: ${confidencePercent}%"></div>
                    </div>
                    <div class="flex justify-between text-xs text-gray-500 mt-1">
                        <span>Low</span>
                        <span>Confidence</span>
                        <span>High</span>
                    </div>
                </div>
                <div class="text-xs text-gray-400 mt-2">
                    Model: ${p.model || 'prophet'} | Updated: ${new Date().toLocaleTimeString()}
                </div>
            </div>
        `;
    }).join('');
}

// ──────────────────────────────────────────────────────────────
// 5. UI HELPERS
// ──────────────────────────────────────────────────────────────

function toggleRuleFields() {
    const ruleType = document.getElementById('ruleType').value;
    
    document.getElementById('targetRateField').style.display = 
        ruleType === 'target_rate' ? 'block' : 'none';
    
    document.getElementById('scheduleFields').style.display = 
        ruleType === 'schedule' ? 'block' : 'none';
    
    document.getElementById('predictiveFields').style.display = 
        ruleType === 'predictive' ? 'block' : 'none';
}

function showModal(id) {
    document.getElementById(id).classList.remove('hidden');
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    const colors = {
        'success': 'bg-green-500',
        'error': 'bg-red-500',
        'info': 'bg-blue-500'
    };
    
    const notification = document.createElement('div');
    notification.className = `${colors[type]} text-white px-4 py-2 rounded-lg shadow-lg mb-2`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// ──────────────────────────────────────────────────────────────
// 6. ONBOARDING TOUR
// ──────────────────────────────────────────────────────────────

function startOnboarding() {
    const steps = [
        {
            element: '#currency-dashboard',
            title: '🌍 Real-Time FX Rates',
            description: 'Monitor exchange rates for all configured currencies. Add new currencies anytime!'
        },
        {
            element: '#predictions',
            title: '📈 AI Predictions',
            description: 'Our AI models predict future rates with confidence scores to help you make informed decisions.'
        },
        {
            element: '#rule-management',
            title: '🤖 Auto-Trading Agents',
            description: 'Create rules that automatically execute trades when conditions are met. No manual intervention needed!'
        },
        {
            element: '.rule-card',
            title: '📊 Rule Management',
            description: 'View all your rules, pause/activate them, or delete them. Each rule shows its execution history.'
        }
    ];
    
    // Show first step
    let currentStep = 0;
    
    function showStep() {
        const step = steps[currentStep];
        // Implementation would use a proper onboarding library
        // For POC, we'll use a simple approach
        alert(`${step.title}\n\n${step.description}`);
        
        if (currentStep < steps.length - 1) {
            currentStep++;
            setTimeout(showStep, 3000);
        } else {
            localStorage.setItem('onboarding_completed', 'true');
        }
    }
    
    setTimeout(showStep, 1000);
}

// ──────────────────────────────────────────────────────────────
// 7. INITIALIZATION
// ──────────────────────────────────────────────────────────────

// Populate currency pairs in rule form
async function populateCurrencyPairs() {
    try {
        const response = await fetch('/currency-pairs', {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            const select = document.getElementById('rulePair');
            select.innerHTML = data.pairs
                .filter(p => p.is_active)
                .map(p => `
                    <option value="${p.pair}">${p.pair}</option>
                `).join('');
        }
    } catch (error) {
        console.error('Failed to populate currency pairs:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await initDashboard();
    await populateCurrencyPairs();
    
    // Add event listeners for modal close buttons
    document.querySelectorAll('.modal .close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.add('hidden');
        });
    });
    
    // Close modal on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    });
});