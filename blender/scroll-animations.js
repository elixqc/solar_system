/* ═══════════════════════════════════════════
   SCROLL ANIMATIONS — Solar System
   Add <script src="scroll-animations.js"></script>
   at the bottom of <body>, before </body>.
   ═══════════════════════════════════════════ */

(function () {
  'use strict';

  /* ── IntersectionObserver — fade/slide elements in ── */
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('anim-in');
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -48px 0px' }
  );

  /* Observe section headings */
  document.querySelectorAll('.section-eyebrow, .section-title, .section-lead').forEach((el, i) => {
    el.style.transitionDelay = `${i * 0.1}s`;
    io.observe(el);
  });

  /* Observe render stats */
  document.querySelectorAll('.render-stat, .render-stats-cta').forEach((el, i) => {
    el.style.transitionDelay = `${i * 0.07}s`;
    io.observe(el);
  });

  /* Observe planet grid cards (staggered) */
  function observePlanetCards() {
    const cards = document.querySelectorAll('.planet-video-block');
    cards.forEach((card, i) => {
      /* Column-aware stagger: 3-col grid → delay by column position */
      const col = i % 3;
      card.style.transitionDelay = `${col * 0.1 + Math.floor(i / 3) * 0.05}s`;
      io.observe(card);
    });
  }

  /* Planet cards are added dynamically by main.js — wait for them */
  const gridEl = document.getElementById('planet-video-grid');
  if (gridEl) {
    if (gridEl.children.length > 0) {
      observePlanetCards();
    } else {
      const mo = new MutationObserver(() => {
        if (gridEl.children.length > 0) {
          mo.disconnect();
          observePlanetCards();
        }
      });
      mo.observe(gridEl, { childList: true });
    }
  }

  /* ── Parallax on render section ── */
  const renderSection = document.querySelector('.render-section');
  if (renderSection && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let ticking = false;
    const handleParallax = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const rect = renderSection.getBoundingClientRect();
          const progress = Math.max(0, Math.min(1, -rect.top / (rect.height * 0.8)));
          /* Subtle upward drift on the pseudo glow as you scroll */
          renderSection.style.setProperty('--parallax-y', `${progress * -40}px`);

          /* Also gently shift the render frame */
          const frame = renderSection.querySelector('.render-frame');
          if (frame) {
            frame.style.transform = `translateY(${progress * -12}px)`;
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleParallax, { passive: true });
    handleParallax(); // initial
  }

  /* ── Smooth number count-up for render stats ── */
  function animateStatValues() {
    const stats = document.querySelectorAll('.render-stat-value');
    stats.forEach((el) => {
      /* Extract numeric part */
      const raw = el.childNodes[0]?.nodeValue?.trim() || '';
      const num = parseFloat(raw.replace(/,/g, ''));
      if (isNaN(num) || num === 0) return;

      const unit = el.querySelector('.unit');
      const unitText = unit ? unit.outerHTML : '';
      const isFloat = !Number.isInteger(num);
      const duration = 900;
      const start = performance.now();

      const tick = (now) => {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        /* Ease-out expo */
        const eased = 1 - Math.pow(1 - progress, 4);
        const value = eased * num;
        const display = isFloat ? value.toFixed(1) : Math.round(value).toLocaleString();
        el.innerHTML = display + ' ' + unitText;
        if (progress < 1) requestAnimationFrame(tick);
      };

      requestAnimationFrame(tick);
    });
  }

  /* Trigger count-up once the stats row enters the viewport */
  const statsRow = document.querySelector('.render-stats');
  if (statsRow) {
    let counted = false;
    const countObs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !counted) {
          counted = true;
          animateStatValues();
          countObs.disconnect();
        }
      },
      { threshold: 0.5 }
    );
    countObs.observe(statsRow);
  }

  /* ── Tilt effect on planet cards ── */
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.addEventListener('mousemove', (e) => {
      const card = e.target.closest('.planet-video-block');
      if (!card) return;
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / (rect.width / 2);
      const dy = (e.clientY - cy) / (rect.height / 2);
      /* Gentle tilt — max ±5deg */
      card.style.transform = `
        translateY(-6px) scale(1.01)
        rotateX(${-dy * 4}deg)
        rotateY(${dx * 4}deg)
      `;
      card.style.transition = 'transform 0.12s ease';
    });

    document.addEventListener('mouseleave', (e) => {
      const card = e.target.closest?.('.planet-video-block');
      if (!card) return;
      card.style.transform = '';
      card.style.transition = 'transform 0.4s cubic-bezier(0.25,0.46,0.45,0.94)';
    }, true);

    /* Reset tilt on mouse leaving the card */
    document.addEventListener('mouseover', (e) => {
      if (!e.target.closest('.planet-video-block')) {
        document.querySelectorAll('.planet-video-block').forEach((c) => {
          if (!c.matches(':hover')) {
            c.style.transform = '';
            c.style.transition = 'transform 0.4s cubic-bezier(0.25,0.46,0.45,0.94)';
          }
        });
      }
    });
  }

  /* ── Progress glow on scroll position in hero ── */
  const hero = document.querySelector('.hero');
  if (hero) {
    const handleHeroScroll = () => {
      const scrolled = window.scrollY;
      const maxScroll = hero.offsetHeight;
      const progress = Math.min(scrolled / maxScroll, 1);
      hero.style.setProperty('--hero-scroll', progress);
      /* Fade hero content slightly as user scrolls away */
      const heroContent = hero.querySelector('div:first-child');
      if (heroContent) {
        heroContent.style.opacity = 1 - progress * 0.35;
        heroContent.style.transform = `translateY(${progress * 24}px)`;
      }
    };
    window.addEventListener('scroll', handleHeroScroll, { passive: true });
  }

  /* ── Reveal nav logo accent on scroll ── */
  const navLogo = document.querySelector('.nav-logo');
  if (navLogo) {
    window.addEventListener('scroll', () => {
      navLogo.style.opacity = window.scrollY > 60 ? '1' : '0.85';
    }, { passive: true });
  }

})();