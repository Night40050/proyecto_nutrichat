
// JavaScript principal para NutriChat

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // API Status Check
    function checkApiStatus() {
        const apiStatusElement = document.getElementById('api-status');
        if (apiStatusElement) {
            fetch('/api/v1/health')
                .then(response => response.json())
                .then(data => {
                    apiStatusElement.textContent = 'Conectado';
                    apiStatusElement.className = 'badge status-connected';
                })
                .catch(error => {
                    apiStatusElement.textContent = 'Desconectado';
                    apiStatusElement.className = 'badge status-disconnected';
                });
        }
    }
    
    // Verificar estado cada 30 segundos
    checkApiStatus();
    setInterval(checkApiStatus, 30000);
    
    // Formularios con validación
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Toast notifications
    function showToast(type, title, message) {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        const toastId = 'toast-' + Date.now();
        
        const toastHTML = `
            <div id="${toastId}" class="toast" role="alert">
                <div class="toast-header">
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        toastContainer.innerHTML += toastHTML;
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Remover después de mostrar
        toastElement.addEventListener('hidden.bs.toast', function () {
            this.remove();
        });
    }
    
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }
    
    // Exponer funciones globales
    window.NutriChat = {
        showToast: showToast,
        checkApiStatus: checkApiStatus
    };
    
    // Ejemplo de uso:
    // NutriChat.showToast('success', 'Éxito', 'Operación completada correctamente');
});

// Funciones de API
const API = {
    baseUrl: 'http://127.0.0.1:5000/api/v1',
    
    // Usuarios
    async register(userData) {
        const response = await fetch(`${this.baseUrl}/users/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(userData)
        });
        return response.json();
    },
    
    async login(telegramId) {
        const response = await fetch(`${this.baseUrl}/users/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({telegram_id: telegramId})
        });
        return response.json();
    },
    
    async getProfile(token) {
        const response = await fetch(`${this.baseUrl}/users/profile`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        return response.json();
    },
    
    // Productos
    async getProducts(token) {
        const response = await fetch(`${this.baseUrl}/products/items`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        return response.json();
    },
    
    async createProduct(token, productData) {
        const response = await fetch(`${this.baseUrl}/products/items`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(productData)
        });
        return response.json();
    },
    
    // Utilidades
    setToken(token) {
        localStorage.setItem('nutrichat_token', token);
    },
    
    getToken() {
        return localStorage.getItem('nutrichat_token');
    },
    
    removeToken() {
        localStorage.removeItem('nutrichat_token');
    },
    
    isAuthenticated() {
        return !!this.getToken();
    }
};
export default API;