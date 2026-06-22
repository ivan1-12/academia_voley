// Gestión de Modo Oscuro / Claro
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement;
    
    // 1. Cargar tema guardado o usar el del sistema
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    
    // 2. Escuchar el click en el botón
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }
    
    // Función para aplicar el tema
    function setTheme(theme) {
        htmlElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Actualizar icono
        if (themeIcon) {
            if (theme === 'dark') {
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
                if (themeToggle) themeToggle.classList.replace('btn-outline-light', 'btn-outline-warning');
            } else {
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
                if (themeToggle) themeToggle.classList.replace('btn-outline-warning', 'btn-outline-light');
            }
        }
    }
});

// Ocultar filas no pendientes en las tablas principales de solicitudes
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Buscar tarjetas de solicitudes y procesar sus tablas
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            const header = card.querySelector('.card-header');
            if (!header) return;
            const title = header.textContent || '';
            if (title.includes('Solicitudes de registro') || title.includes('Solicitudes presentadas') || title.includes('Solicitudes sin tipo')) {
                const rows = card.querySelectorAll('table tbody tr');
                rows.forEach(row => {
                    const badge = row.querySelector('.badge');
                    if (!badge) return;
                    const text = (badge.textContent || '').trim().toLowerCase();
                    if (text !== 'pendiente') {
                        row.style.display = 'none';
                    }
                });
            }
        });
    } catch (e) {
        console.warn('hide non-pending rows error', e);
    }
});

// Envío AJAX para formularios marcados con data-ajax="true"
document.addEventListener('submit', function(e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.getAttribute('data-ajax') !== 'true') return;

    e.preventDefault();
    const url = form.action;
    const method = (form.method || 'POST').toUpperCase();
    const fd = new FormData(form);

    fetch(url, {
        method: method,
        body: fd,
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(async (resp) => {
        // intentar parsear JSON
        let data = null;
        try {
            data = await resp.json();
        } catch (err) {
            data = null;
        }

        const container = document.querySelector('.container.mt-3');
        if (data && typeof data.message === 'string') {
            const div = document.createElement('div');
            const cls = data.success ? 'success' : 'danger';
            div.className = `alert alert-${cls} alert-dismissible fade show`;
            div.innerHTML = `${data.message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>`;
            if (container) container.prepend(div);
            // cerrar modal si existe
            const modalEl = form.closest('.modal');
            if (modalEl) {
                try {
                    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                    modal.hide();
                } catch (err) {
                    // ignore
                }
            }
        } else if (resp.redirected) {
            window.location = resp.url;
        } else {
            // fallback: recargar para reflejar cambios
            window.location.reload();
        }
    })
    .catch((err) => {
        console.error('AJAX submit error', err);
        const container = document.querySelector('.container.mt-3');
        if (container) {
            const div = document.createElement('div');
            div.className = 'alert alert-danger alert-dismissible fade show';
            div.innerHTML = 'Error de red al asignar. Intenta de nuevo.' + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>';
            container.prepend(div);
        }
    });
});

// Toggle para mostrar/ocultar el buzón de solicitudes aceptadas/rechazadas
document.addEventListener('DOMContentLoaded', function() {
    const buzon = document.getElementById('buzonSection');
    const botones = document.querySelectorAll('.toggle-buzon-btn');
    if (!buzon || !botones.length) return;
    botones.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const isHidden = (buzon.style.display === 'none' || getComputedStyle(buzon).display === 'none');
            if (isHidden) {
                buzon.style.display = 'block';
                const icon = btn.querySelector('i');
                if (icon) { icon.classList.remove('fa-inbox'); icon.classList.add('fa-times'); }
                btn.setAttribute('aria-pressed', 'true');
            } else {
                buzon.style.display = 'none';
                const icon = btn.querySelector('i');
                if (icon) { icon.classList.remove('fa-times'); icon.classList.add('fa-inbox'); }
                btn.setAttribute('aria-pressed', 'false');
            }
        });
    });
});