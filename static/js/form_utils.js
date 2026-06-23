/* Utilities for forms: password toggle and basic strength meter */

function attachPasswordToggle(buttonId, inputId, iconId) {
    try {
        const btn = document.getElementById(buttonId);
        const input = document.getElementById(inputId);
        const icon = document.getElementById(iconId);
        if (!btn || !input || !icon) return;
        btn.addEventListener('click', function () {
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
                btn.setAttribute('aria-label', 'Ocultar contraseña');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
                btn.setAttribute('aria-label', 'Mostrar contraseña');
            }
        });
    } catch (e) {
        console.warn('attachPasswordToggle error', e);
    }
}

function scorePasswordSimple(pw) {
    let score = 0;
    if (!pw) return 0;
    if (pw.length >= 8) score += 1;
    if (pw.length >= 12) score += 1;
    if (/[0-9]/.test(pw)) score += 1;
    if (/[A-Z]/.test(pw)) score += 1;
    if (/[^A-Za-z0-9]/.test(pw)) score += 1;
    return score; // 0-5
}

function attachPasswordStrength(inputId, barId) {
    try {
        const input = document.getElementById(inputId);
        const bar = document.getElementById(barId);
        if (!input || !bar) return;
        input.addEventListener('input', function () {
            const s = scorePasswordSimple(input.value);
            const percent = Math.min(100, Math.round((s / 5) * 100));
            bar.style.width = percent + '%';
            bar.className = 'progress-bar';
            if (percent < 40) bar.classList.add('bg-danger');
            else if (percent < 70) bar.classList.add('bg-warning');
            else bar.classList.add('bg-success');
        });
    } catch (e) {
        console.warn('attachPasswordStrength error', e);
    }
}

function initFormUtils() {
    attachPasswordToggle('togglePasswordReg', 'password', 'togglePasswordRegIcon');
    attachPasswordStrength('password', 'passwordStrengthReg');
    attachPasswordToggle('togglePasswordStaff', 'password', 'togglePasswordStaffIcon');
    attachPasswordStrength('password', 'passwordStrengthStaff');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFormUtils);
} else {
    initFormUtils();
}
