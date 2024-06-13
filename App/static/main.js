const navbar = document.querySelector('.navbar');
const brandImg = document.getElementById('brandLogo');
const getStarted = document.getElementById('getStarted');

window.addEventListener('load', () => {
    if (window.innerWidth <= 767.9) {
        navbar.classList.replace('navbar-dark', 'navbar-light');
        navbar.classList.remove('bg-success');
        brandImg.src = '/static/img/KURS.svg';
        getStarted.classList.replace('btn-light', 'btn-success');
    }
});
