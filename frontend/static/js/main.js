
document.addEventListener('DOMContentLoaded', () => {
    initMobileNav();
    
    highlightActiveLink();
    
    initDropdowns();
});

function initMobileNav() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('show');
            navToggle.classList.toggle('active');
            
            const openIcon = navToggle.querySelector('.toggle-open');
            const closeIcon = navToggle.querySelector('.toggle-close');
            
            if (navMenu.classList.contains('show')) {
                openIcon.style.display = 'none';
                closeIcon.style.display = 'block';
            } else {
                openIcon.style.display = 'block';
                closeIcon.style.display = 'none';
            }
        });
        
        document.addEventListener('click', (e) => {
            if (!navMenu.contains(e.target) && !navToggle.contains(e.target)) {
                navMenu.classList.remove('show');
                navToggle.classList.remove('active');
                navToggle.querySelector('.toggle-open').style.display = 'block';
                navToggle.querySelector('.toggle-close').style.display = 'none';
            }
        });
    }
}

function highlightActiveLink() {
    const currentPath = window.location.pathname;
    
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => link.classList.remove('active'));
    
    if (currentPath === '/' || currentPath === '/index.html') {
        const homeLink = document.getElementById('nav-link-home');
        if (homeLink) homeLink.classList.add('active');
    } else if (currentPath.startsWith('/predict')) {
        const predictLink = document.getElementById('nav-link-predict');
        if (predictLink) predictLink.classList.add('active');
    } else if (currentPath.startsWith('/history')) {
        const historyLink = document.getElementById('nav-link-history');
        if (historyLink) historyLink.classList.add('active');
    } else if (currentPath.startsWith('/dashboard')) {
        const dashboardLink = document.getElementById('nav-link-dashboard');
        if (dashboardLink) dashboardLink.classList.add('active');
    } else if (currentPath.startsWith('/about')) {
        const aboutLink = document.getElementById('nav-link-about');
        if (aboutLink) aboutLink.classList.add('active');
    } else if (currentPath.startsWith('/contact')) {
        const contactLink = document.getElementById('nav-link-contact');
        if (contactLink) contactLink.classList.add('active');
    }
}

const LoadingOverlay = {
    element: document.getElementById('loading-overlay'),
    
    show(message = 'Processing request...') {
        if (!this.element) {
            this.element = document.getElementById('loading-overlay');
        }
        if (this.element) {
            const messageEl = this.element.querySelector('.spinner-message');
            if (messageEl) messageEl.textContent = message;
            this.element.classList.add('show');
            this.element.setAttribute('aria-hidden', 'false');
        }
    },
    
    hide() {
        if (this.element) {
            this.element.classList.remove('show');
            this.element.setAttribute('aria-hidden', 'true');
        }
    }
};

function showNotification(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-circle-exclamation';
    
    toast.innerHTML = `
        <i class="fa-solid ${iconClass}"></i>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse forwards';
        toast.addEventListener('animationend', () => {
            toast.remove();
        });
    }, duration);
}

function initDropdowns() {
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            const dropdown = toggle.closest('.dropdown');
            if (!dropdown) return;
            
            const isActive = dropdown.classList.contains('active');
            
            closeAllDropdowns();
            
            if (!isActive) {
                dropdown.classList.add('active');
                toggle.setAttribute('aria-expanded', 'true');
            }
        });
        
        toggle.addEventListener('keydown', (e) => {
            if (e.key === ' ' || e.key === 'Spacebar') {
                e.preventDefault();
                toggle.click();
            }
        });
    });
    
    document.addEventListener('click', (e) => {
        const activeDropdowns = document.querySelectorAll('.dropdown.active');
        activeDropdowns.forEach(dropdown => {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
                const toggle = dropdown.querySelector('.dropdown-toggle');
                if (toggle) {
                    toggle.setAttribute('aria-expanded', 'false');
                }
            }
        });
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllDropdowns();
        }
    });
}

function closeAllDropdowns() {
    const activeDropdowns = document.querySelectorAll('.dropdown.active');
    activeDropdowns.forEach(dropdown => {
        dropdown.classList.remove('active');
        const toggle = dropdown.querySelector('.dropdown-toggle');
        if (toggle) {
            toggle.setAttribute('aria-expanded', 'false');
        }
    });
}
