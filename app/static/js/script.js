// Lokasi file: D:/projek-yolo8/app/static/js/script.js
document.addEventListener('DOMContentLoaded', function () {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;
    const htmlElement = document.documentElement;
    const moonIcon = '<i class="bi bi-moon-stars-fill"></i>';
    const sunIcon = '<i class="bi bi-sun-fill"></i>';

    if (currentTheme) {
        htmlElement.setAttribute('data-bs-theme', currentTheme);
        if (themeToggleBtn) {
            themeToggleBtn.innerHTML = currentTheme === 'dark' ? sunIcon : moonIcon;
        }
    } else { // Default to light if no preference saved
        htmlElement.setAttribute('data-bs-theme', 'light');
         if (themeToggleBtn) {
            themeToggleBtn.innerHTML = moonIcon;
        }
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            let theme = htmlElement.getAttribute('data-bs-theme');
            if (theme === 'dark') {
                htmlElement.setAttribute('data-bs-theme', 'light');
                localStorage.setItem('theme', 'light');
                themeToggleBtn.innerHTML = moonIcon;
            } else {
                htmlElement.setAttribute('data-bs-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeToggleBtn.innerHTML = sunIcon;
            }
        });
    }
});

// Fungsi untuk menampilkan pesan error pada form tertentu
function displayError(formId, message) {
    const errorDiv = document.getElementById(formId + '-error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}

// Fungsi untuk menyembunyikan pesan error
function clearError(formId) {
     const errorDiv = document.getElementById(formId + '-error-message');
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }
}
