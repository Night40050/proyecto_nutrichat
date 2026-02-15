// app/static/js/app.js
// Funciones globales de NutriChat

class NutriChatApp {
    constructor() {
        this.init();
    }
    
    init() {
        console.log('🚀 NutriChat App iniciada');
        this.setupEventListeners();
        this.checkSystemStatus();
        this.setupAjaxCalls();
    }
    
    setupEventListeners() {
        // Tooltips
        this.setupTooltips();
        
        // Formularios
        this.setupForms();
        
        // Modales
        this.setupModals();
        
        // Dropdowns
        this.setupDropdowns();
    }
    
    setupTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
    
    setupForms() {
        // Validación de formularios
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const submitBtn = form.querySelector('button[type="submit"]');
                const originalText = submitBtn ? submitBtn.innerHTML : '';
                
                // Deshabilitar botón
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Procesando...';
                }
                
                // Verificar si es formulario de API
                const isApiForm = form.hasAttribute('data-api');
                
                if (isApiForm) {
                    await this.handleApiFormSubmit(form);
                } else {
                    // Formulario normal, enviar
                    form.submit();
                }
                
                // Restaurar botón después de 2 segundos
                setTimeout(() => {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }
                }, 2000);
            });
        });
    }
    
    async handleApiFormSubmit(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        const apiUrl = form.getAttribute('data-api-url') || form.action;
        const method = form.getAttribute('data-method') || 'POST';
        
        try {
            const response = await fetch(apiUrl, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message || 'Operación exitosa', 'success');
                
                // Redirigir si hay URL de redirección
                const redirectUrl = form.getAttribute('data-redirect');
                if (redirectUrl) {
                    setTimeout(() => {
                        window.location.href = redirectUrl;
                    }, 1500);
                }
                
                // Recargar la página si se especifica
                if (form.hasAttribute('data-reload')) {
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            } else {
                this.showNotification(result.message || 'Error en la operación', 'danger');
            }
        } catch (error) {
            console.error('Error en formulario:', error);
            this.showNotification('Error de conexión', 'danger');
        }
    }
    
    setupModals() {
        // Cerrar modales al hacer clic fuera
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    const modalInstance = bootstrap.Modal.getInstance(modal);
                    modalInstance.hide();
                }
            });
        });
    }
    
    setupDropdowns() {
        // Cerrar otros dropdowns al abrir uno
        document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                const dropdown = toggle.closest('.dropdown');
                document.querySelectorAll('.dropdown').forEach(d => {
                    if (d !== dropdown) {
                        d.classList.remove('show');
                    }
                });
            });
        });
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch('/api/v1/health');
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.updateStatusIndicator('success', 'Sistema operativo');
            } else {
                this.updateStatusIndicator('warning', 'Sistema con problemas');
            }
        } catch (error) {
            this.updateStatusIndicator('danger', 'Error de conexión');
        }
    }
    
    updateStatusIndicator(status, message) {
        const indicator = document.getElementById('system-status-indicator');
        if (indicator) {
            indicator.className = `status-indicator status-${status}`;
            indicator.textContent = message;
        }
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        // Verificar si ya existe una notificación del sistema
        if (window.showNotification) {
            window.showNotification(message, type, duration);
            return;
        }
        
        // Crear notificación manual
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
    
    setupAjaxCalls() {
        // Interceptar todos los enlaces con data-ajax
        document.addEventListener('click', async (e) => {
            const link = e.target.closest('a[data-ajax]');
            if (link) {
                e.preventDefault();
                
                const url = link.getAttribute('href');
                const method = link.getAttribute('data-method') || 'GET';
                const confirmMessage = link.getAttribute('data-confirm');
                
                if (confirmMessage && !confirm(confirmMessage)) {
                    return;
                }
                
                try {
                    const response = await fetch(url, { method });
                    const data = await response.json();
                    
                    if (data.success) {
                        this.showNotification(data.message || 'Operación exitosa', 'success');
                        
                        // Recargar si se especifica
                        if (link.hasAttribute('data-reload')) {
                            setTimeout(() => window.location.reload(), 1000);
                        }
                        
                        // Redirigir si se especifica
                        const redirectUrl = link.getAttribute('data-redirect');
                        if (redirectUrl) {
                            setTimeout(() => {
                                window.location.href = redirectUrl;
                            }, 1500);
                        }
                    } else {
                        this.showNotification(data.message || 'Error en la operación', 'danger');
                    }
                } catch (error) {
                    console.error('Error en petición AJAX:', error);
                    this.showNotification('Error de conexión', 'danger');
                }
            }
        });
    }
    
    // Función para cargar productos
    async loadProducts(filters = {}) {
        try {
            const queryString = new URLSearchParams(filters).toString();
            const response = await fetch(`/api/v1/products/items?${queryString}`);
            return await response.json();
        } catch (error) {
            console.error('Error cargando productos:', error);
            return { success: false, message: 'Error cargando productos' };
        }
    }
    
    // Función para crear producto
    async createProduct(productData) {
        try {
            const response = await fetch('/api/v1/products/items', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(productData)
            });
            return await response.json();
        } catch (error) {
            console.error('Error creando producto:', error);
            return { success: false, message: 'Error creando producto' };
        }
    }
    
    // Función para eliminar producto
    async deleteProduct(productId) {
        try {
            const response = await fetch(`/api/v1/products/items/${productId}`, {
                method: 'DELETE'
            });
            return await response.json();
        } catch (error) {
            console.error('Error eliminando producto:', error);
            return { success: false, message: 'Error eliminando producto' };
        }
    }
}

// Inicializar la aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.NutriChat = new NutriChatApp();
});

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NutriChatApp;
}