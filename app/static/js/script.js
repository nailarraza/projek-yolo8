// Custom JavaScript will go here

document.addEventListener('DOMContentLoaded', function () {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;
    const htmlElement = document.documentElement;

    if (currentTheme) {
        htmlElement.setAttribute('data-bs-theme', currentTheme);
        updateToggleButtonText(currentTheme);
    } else { // Default to light if no preference stored
        htmlElement.setAttribute('data-bs-theme', 'light');
        updateToggleButtonText('light');
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            let newTheme = htmlElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
            htmlElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateToggleButtonText(newTheme);
        });
    }

    function updateToggleButtonText(theme) {
        if (themeToggleBtn) {
             // Anda bisa menggunakan ikon di sini
            themeToggleBtn.textContent = theme === 'dark' ? 'Mode Terang' : 'Mode Gelap';
        }
    }
});
