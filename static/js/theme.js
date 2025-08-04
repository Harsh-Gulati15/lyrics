// static/js/theme.js

const themeToggleBtn = document.getElementById('theme-toggle');
const moonIcon = document.getElementById('moon-icon');
const sunIcon = document.getElementById('sun-icon');
const htmlEl = document.documentElement;

function updateIcons() {
    if (!moonIcon || !sunIcon) return; // Don't run if icons aren't on the page
    if (htmlEl.classList.contains('dark')) {
        moonIcon.classList.add('hidden');
        sunIcon.classList.remove('hidden');
    } else {
        moonIcon.classList.remove('hidden');
        sunIcon.classList.add('hidden');
    }
}

if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function() {
        htmlEl.classList.toggle('dark');
        if (htmlEl.classList.contains('dark')) {
            localStorage.setItem('theme', 'dark');
        } else {
            localStorage.setItem('theme', 'light');
        }
        updateIcons();
    });
}

// Set initial icon state on page load.
// Wrap in DOMContentLoaded to ensure elements exist.
document.addEventListener('DOMContentLoaded', updateIcons);