// D:/projek-yolo8/app/static/js/script.js
document.addEventListener('DOMContentLoaded', function () {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const htmlElement = document.documentElement;
    const themeIconLight = document.getElementById('themeIconLight');
    const themeIconDark = document.getElementById('themeIconDark');
    const themeToggleText = document.getElementById('themeToggleText'); // Opsional, jika masih mau ada teks

    // Fungsi untuk mengupdate tampilan tombol tema
    function updateThemeButton(theme) {
        if (theme === 'dark') {
            if (themeIconLight) themeIconLight.style.display = 'none';
            if (themeIconDark) themeIconDark.style.display = 'inline-block';
            if (themeToggleText) themeToggleText.textContent = ' Terang'; // Teks jika diinginkan
            if (themeToggleBtn) themeToggleBtn.classList.replace('btn-outline-light', 'btn-outline-warning');

        } else {
            if (themeIconLight) themeIconLight.style.display = 'inline-block';
            if (themeIconDark) themeIconDark.style.display = 'none';
            if (themeToggleText) themeToggleText.textContent = ' Gelap'; // Teks jika diinginkan
            if (themeToggleBtn) themeToggleBtn.classList.replace('btn-outline-warning', 'btn-outline-light');
        }
    }

    const storedTheme = localStorage.getItem('theme');
    const preferredTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const currentTheme = storedTheme ? storedTheme : preferredTheme;

    htmlElement.setAttribute('data-bs-theme', currentTheme);
    updateThemeButton(currentTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            let newTheme = htmlElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
            htmlElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeButton(newTheme);
        });
    }

    // Tambahkan event listener untuk perubahan preferensi sistem (jika pengguna mengubahnya saat tab terbuka)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
      if (!localStorage.getItem('theme')) { // Hanya update jika tema tidak di-override oleh user
          const newColorScheme = event.matches ? "dark" : "light";
          htmlElement.setAttribute('data-bs-theme', newColorScheme);
          updateThemeButton(newColorScheme);
      }
    });
});