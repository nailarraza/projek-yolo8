// D:/projek-yolo8/app/static/js/script.js
document.addEventListener('DOMContentLoaded', function () {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const htmlElement = document.documentElement;

    if (!themeToggleBtn || !htmlElement) {
        console.warn("Tombol tema atau elemen HTML tidak ditemukan.");
        return;
    }

    // Ikon untuk masing-masing tema
    const sunIcon = '<i class="fas fa-sun"></i><span class="visually-hidden">Switch to Light Mode</span>';
    const moonIcon = '<i class="fas fa-moon"></i><span class="visually-hidden">Switch to Dark Mode</span>';

    // Fungsi untuk mengatur ikon tombol berdasarkan tema saat ini
    const setButtonIcon = () => {
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        if (currentTheme === 'dark') {
            themeToggleBtn.innerHTML = sunIcon;
            themeToggleBtn.title = 'Switch to Light Mode';
            themeToggleBtn.classList.remove('btn-outline-light');
            themeToggleBtn.classList.add('btn-outline-warning'); // Contoh kelas untuk mode terang
        } else {
            themeToggleBtn.innerHTML = moonIcon;
            themeToggleBtn.title = 'Switch to Dark Mode';
            themeToggleBtn.classList.remove('btn-outline-warning');
            themeToggleBtn.classList.add('btn-outline-light'); // Contoh kelas untuk mode gelap
        }
    };

    // Terapkan tema dari localStorage atau preferensi sistem
    const storedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    let currentTheme;

    if (storedTheme) {
        currentTheme = storedTheme;
    } else {
        currentTheme = systemPrefersDark ? 'dark' : 'light';
    }
    htmlElement.setAttribute('data-bs-theme', currentTheme);
    setButtonIcon(); // Atur ikon tombol saat halaman dimuat

    // Event listener untuk tombol
    themeToggleBtn.addEventListener('click', () => {
        // Logika untuk mengubah tema (Anda mungkin sudah memiliki ini)
        if (htmlElement.getAttribute('data-bs-theme') === 'dark') {
            htmlElement.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('theme', 'light');
        } else {
            htmlElement.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
        // Perbarui ikon setelah tema diubah
        setButtonIcon();
    });

    // Tambahkan event listener untuk perubahan preferensi sistem
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        // Hanya update jika tema tidak di-override secara manual oleh pengguna (tidak ada di localStorage)
        if (!localStorage.getItem('theme')) {
            const newColorScheme = event.matches ? "dark" : "light";
            htmlElement.setAttribute('data-bs-theme', newColorScheme);
            setButtonIcon();
        }
    });
});
