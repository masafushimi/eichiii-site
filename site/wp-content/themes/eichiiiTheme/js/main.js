// Service Worker Registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    // WordPressテーマディレクトリの相対パスを取得
    const themePath = document.querySelector('script[src*="main.js"]').src.replace('/js/main.js', '');
    navigator.serviceWorker.register(themePath + '/sw.js').then(function(registration) {
      console.log('ServiceWorker registration successful with scope: ', registration.scope);
    }, function(err) {
      console.log('ServiceWorker registration failed: ', err);
    });
  });
}

document.addEventListener('DOMContentLoaded', function() {
  const hamburgerMenu = document.querySelector('.u-hamburger-menu');
  const spNav = document.querySelector('.c-sp-gnav');

  if (hamburgerMenu) {
    hamburgerMenu.addEventListener('click', function() {
      this.classList.toggle('active');

      if (spNav) {
        if (this.classList.contains('active')) {
          spNav.style.display = 'block';
        } else {
          spNav.style.display = 'none';
        }
      }
    });
  }

  const spNavLinks = document.querySelectorAll('.c-sp-gnav ul a');

  spNavLinks.forEach(link => {
    link.addEventListener('click', function() {
      if (spNav) {
        spNav.style.display = 'none';
        hamburgerMenu.classList.remove('active');
      }
    });
  });

  // 画像の遅延読み込み実装
  if ('loading' in HTMLImageElement.prototype) {
    const images = document.querySelectorAll('img[loading="lazy"]');
    images.forEach(img => {
      img.src = img.getAttribute('src');
    });
  } else {
    // Fallback for browsers that don't support lazy loading
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js';
    document.body.appendChild(script);
  }

  // Intersection Observer for viewport detection
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const lazyElement = entry.target;
          if (lazyElement.dataset.src) {
            lazyElement.src = lazyElement.dataset.src;
            lazyElement.removeAttribute('data-src');
          }
          observer.unobserve(lazyElement);
        }
      });
    });

    document.querySelectorAll('[data-src]').forEach(element => {
      observer.observe(element);
    });
  }

  // フォームバリデーション強化
  const form = document.querySelector('form');
  if (form) {
    form.addEventListener('submit', function(e) {
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;

      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          field.style.borderColor = '#ff0000';
        } else {
          field.style.borderColor = '';
        }
      });

      if (!isValid) {
        e.preventDefault();
        // alert('必須項目をすべて入力してください。');
      }
    });
  }
});
