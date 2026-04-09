document.addEventListener('DOMContentLoaded', () => {
    console.log('Painel administrativo carregado!');
    // Adicione interações aqui (ex: filtros, atualizações via API)
});

// Utility function to get API base
function getApiBase() {
    return window.API_BASE || 'https://sd-br2.blazebr.com:26173'; // Fallback
}

// Utility to check if logged in
function isLoggedIn() {
    return !!localStorage.getItem('access_token');
}

// Logout function
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('admin_token');
    window.location.href = './home.html';
}

// Dashboard functions
function loadDashboard() {
    const API_BASE = getApiBase();
    const token = localStorage.getItem('access_token');

    if (!token) {
        window.location.href = './home.html';
        return;
    }

    fetch(`${API_BASE}/dashboard`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to load dashboard');
        return response.json();
    })
    .then(data => {
        document.getElementById('welcome').textContent = `Bem-vindo, ${data.user.username}!`;
        if (data.user.admin) {
            document.getElementById('adminLink').style.display = 'inline';
        }
        const tbody = document.getElementById('apoiadoresBody');
        data.apoiadores.forEach(apoiador => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${apoiador.discord_id}</td>
                <td>${apoiador.tipo_apoio}</td>
                <td class="status-${apoiador.ativo ? 'ativo' : 'inativo'}">${apoiador.ativo ? 'Ativo' : 'Inativo'}</td>
                <td>${apoiador.data_expiracao ? new Date(apoiador.data_expiracao).toLocaleDateString('pt-BR') : '-'}</td>
            `;
            tbody.appendChild(row);
        });
    })
    .catch(error => {
        console.error(error);
        alert('Erro ao carregar dashboard');
    });
}

// Servers functions
function loadServers() {
    const API_BASE = getApiBase();
    const token = localStorage.getItem('access_token');

    if (!token) {
        window.location.href = './home.html';
        return;
    }

    fetch(`${API_BASE}/servers`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to load servers');
        return response.json();
    })
    .then(data => {
        const ul = document.getElementById('guildsList');
        data.guilds.forEach(guild => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${guild.name}</strong> (ID: ${guild.id})`;
            ul.appendChild(li);
        });
    })
    .catch(error => {
        console.error(error);
        alert('Erro ao carregar servidores');
    });
}

// Admin functions
function loadAdmin() {
    const API_BASE = getApiBase();
    const token = localStorage.getItem('access_token');
    const adminToken = localStorage.getItem('admin_token') || prompt('Enter admin token:');

    if (!token || !adminToken) {
        window.location.href = './home.html';
        return;
    }

    fetch(`${API_BASE}/admin`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to load admin');
        return response.json();
    })
    .then(data => {
        // Metrics
        const metricasDiv = document.getElementById('metricas');
        metricasDiv.innerHTML = `
            <div class="metrica">
                <h3>Total de Doações</h3>
                <p>${data.metricas.total_donations}</p>
            </div>
            <div class="metrica">
                <h3>Apoiadores Ativos</h3>
                <p>${data.metricas.active_supporters}</p>
            </div>
            <div class="metrica">
                <h3>Expirados</h3>
                <p>${data.metricas.expired_supporters}</p>
            </div>
            <div class="metrica">
                <h3>Taxa de Renovação</h3>
                <p>${data.metricas.renewal_rate}%</p>
            </div>
            <div class="metrica warning">
                <h3>Cargos Pendentes</h3>
                <p>${data.metricas.pending_role_assignments}</p>
            </div>
            <div class="metrica danger">
                <h3>Falhas Webhook</h3>
                <p>${data.metricas.webhook_failure_count}</p>
            </div>
        `;

        // Apoiadores table
        const tbody = document.getElementById('apoiadoresBody');
        data.apoiadores.forEach(apoiador => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${apoiador.discord_id}</td>
                <td>${apoiador.guild_id}</td>
                <td>${apoiador.tipo_apoio}</td>
                <td class="status-${apoiador.ativo ? 'ativo' : 'inativo'}">${apoiador.ativo ? 'Ativo' : 'Inativo'}</td>
                <td>${apoiador.ultimo_pagamento ? new Date(apoiador.ultimo_pagamento).toLocaleDateString('pt-BR') : '-'}</td>
                <td>${apoiador.data_expiracao ? new Date(apoiador.data_expiracao).toLocaleDateString('pt-BR') : '-'}</td>
                <td>${apoiador.cargo_atribuido ? '✅ Sim' : '❌ Não'}</td>
            `;
            tbody.appendChild(row);
        });
    })
    .catch(error => {
        console.error(error);
        alert('Erro ao carregar admin');
    });

    // Form submit
    document.getElementById('roleConfigForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const guildId = document.getElementById('guild_id').value;
        const supporter_roles = {};
        for (let i = 1; i <= 9; i++) {
            const val = document.getElementById(`role_${i}`).value.trim();
            if (val) supporter_roles[String(i)] = val;
        }
        const formData = { guild_id: guildId, supporter_roles };
        
        try {
            const response = await fetch(`${API_BASE}/admin/set-supporter-roles`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${adminToken}`
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            if (response.ok) {
                alert(`Configuração salva! Servidor: ${result.guild_id}`);
            } else {
                alert(`Erro: ${result.detail || 'Falha ao salvar configuração'}`);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Erro na comunicação com o servidor');
        }
    });
}

// Home function
function setupHome() {
    const API_BASE = getApiBase();
    document.getElementById('loginLink').href = API_BASE + '/login';
}