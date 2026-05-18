/* ── RENDER FULLSCREEN ── */
const renderPlayer = document.getElementById('render-player');
const renderFsBtn = document.getElementById('render-fs-btn');
renderFsBtn.addEventListener('click', () => {
  if (renderPlayer.requestFullscreen) renderPlayer.requestFullscreen();
  else if (renderPlayer.webkitRequestFullscreen) renderPlayer.webkitRequestFullscreen();
  else if (renderPlayer.mozRequestFullScreen) renderPlayer.mozRequestFullScreen();
});

const youtubeIds = {
  sun: 'bqnrUin0qUU',
  mercury: 'ibj9WRVkW1k',
  venus: '6M6wO3OSmJY',
  earth: 'FFYPBa2T0f8',
  mars: 'OH76VCvgAEA',
  jupiter: '_kHSee2pTvw',
  saturn: 'SmDZkMTPTM8',
  uranus: '6286ZWRbLfs',
  neptune: 'Mx5pO1axJFs',
  pluto: 'AhLoCXlzAFs',
  whole_solar: 'iW0AsLnhGoE'
};

function getYoutubeEmbedUrl(videoId) {
  return `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&mute=1&loop=1&playlist=${videoId}&controls=0&rel=0&modestbranding=1&playsinline=1&iv_load_policy=3&fs=0&disablekb=1`;
}

function shouldPreferLocalVideo() {
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (connection && connection.saveData) return false;
  if (connection && /slow-2g|2g/.test(connection.effectiveType || '')) return false;
  return true;
}

function getLocalBlenderVideoSrc(fileName) {
  return `media/${fileName}`;
}

const wholeSolarYoutubeUrl = getYoutubeEmbedUrl(youtubeIds.whole_solar);

/* ── PLANET DATA ── */
const planets = [
  {
    id: "sun", tag: "Star", name: "Sun", file: "sun.mp4", page: "sun.html",
    orbitalPeriod: null, // Star — no orbit
    desc: "The Sun is the star at the heart of our solar system — a massive, blazing sphere of plasma that provides the light, heat, and gravitational anchor that makes life on Earth possible.",
    facts: [
      { label: "Type", value: "G-type Star" },
      { label: "Diameter", value: "1,392,700 km" },
      { label: "Surface Temp", value: "5,500 °C" },
      { label: "Rotation", value: "25.4 days" },
    ]
  },
  {
    id: "mercury", tag: "Planet 01", name: "Mercury", file: "mercury.mp4", page: "mercury.html",
    orbitalPeriod: 0.2408,
    desc: "Mercury is the smallest planet in the solar system and the closest to the Sun. Its surface is heavily cratered, resembling the Moon, and it experiences extreme temperature swings between day and night.",
    facts: [
      { label: "Orbit Period", value: "88 Earth days" },
      { label: "Diameter", value: "4,879 km" },
      { label: "Moons", value: "0" },
      { label: "Rotation", value: "58.6 days" },
    ]
  },
  {
    id: "venus", tag: "Planet 02", name: "Venus", file: "venus.mp4", page: "venus.html",
    orbitalPeriod: 0.6152,
    desc: "Venus is the hottest planet, shrouded in thick clouds of sulfuric acid. Despite being farther from the Sun than Mercury, its runaway greenhouse effect makes its surface hotter than any other planet.",
    facts: [
      { label: "Orbit Period", value: "225 Earth days" },
      { label: "Diameter", value: "12,104 km" },
      { label: "Surface Temp", value: "465 °C" },
      { label: "Rotation", value: "243 days" },
    ]
  },
  {
    id: "earth", tag: "Planet 03", name: "Earth", file: "earth.mp4", page: "earth.html",
    orbitalPeriod: 1,
    desc: "Earth is the only known planet to harbor life. With vast oceans, a breathable atmosphere, and a protective magnetic field, it is a unique blue marble in the cosmic void.",
    facts: [
      { label: "Orbit Period", value: "365.25 days" },
      { label: "Diameter", value: "12,742 km" },
      { label: "Moons", value: "1" },
      { label: "Rotation", value: "23.9 hours" },
    ]
  },
  {
    id: "mars", tag: "Planet 04", name: "Mars", file: "mars.mp4", page: "mars.html",
    orbitalPeriod: 1.8808,
    desc: "Mars, the Red Planet, has the tallest volcano and the longest canyon in the solar system. Scientists are actively exploring it as a potential candidate for future human habitation.",
    facts: [
      { label: "Orbit Period", value: "687 Earth days" },
      { label: "Diameter", value: "6,779 km" },
      { label: "Moons", value: "2" },
      { label: "Rotation", value: "24.6 hours" },
    ]
  },
  {
    id: "jupiter", tag: "Planet 05", name: "Jupiter", file: "jupiter.mp4", page: "jupiter.html",
    orbitalPeriod: 11.862,
    desc: "Jupiter is the largest planet in the solar system — so massive that all other planets could fit inside it. Its iconic Great Red Spot is a storm that has raged for centuries.",
    facts: [
      { label: "Orbit Period", value: "11.9 Earth years" },
      { label: "Diameter", value: "139,820 km" },
      { label: "Moons", value: "95" },
      { label: "Rotation", value: "9.9 hours" },
    ]
  },
  {
    id: "saturn", tag: "Planet 06", name: "Saturn", file: "saturn.mp4", page: "saturn.html",
    orbitalPeriod: 29.457,
    desc: "Saturn is the jewel of the solar system, famous for its breathtaking ring system made of ice and rock. It is a gas giant so light that it would float in water.",
    facts: [
      { label: "Orbit Period", value: "29.5 Earth years" },
      { label: "Diameter", value: "116,460 km" },
      { label: "Ring Span", value: "~282,000 km" },
      { label: "Rotation", value: "10.7 hours" },
    ]
  },
  {
    id: "uranus", tag: "Planet 07", name: "Uranus", file: "uranus.mp4", page: "uranus.html",
    orbitalPeriod: 84.011,
    desc: "Uranus is an ice giant that rotates on its side with an axial tilt of 98°. Its pale blue-green color comes from methane in its atmosphere, which absorbs red light.",
    facts: [
      { label: "Orbit Period", value: "84 Earth years" },
      { label: "Diameter", value: "50,724 km" },
      { label: "Axial Tilt", value: "97.77°" },
      { label: "Rotation", value: "17.2 hours" },
    ]
  },
  {
    id: "neptune", tag: "Planet 08", name: "Neptune", file: "neptune.mp4", page: "neptune.html",
    orbitalPeriod: 164.8,
    desc: "Neptune is the farthest planet from the Sun and the windiest in the solar system. Its winds can reach over 2,000 km/h, and its deep blue color is one of the most striking in the solar system.",
    facts: [
      { label: "Orbit Period", value: "165 Earth years" },
      { label: "Diameter", value: "49,244 km" },
      { label: "Wind Speed", value: "2,100 km/h" },
      { label: "Rotation", value: "16.1 hours" },
    ]
  },
  {
    id: "pluto", tag: "Dwarf Planet", name: "Pluto", file: "pluto.mp4", page: "pluto.html",
    orbitalPeriod: 247.94,
    desc: "Pluto is a dwarf planet in the Kuiper Belt, reclassified from its planetary status in 2006. Despite its small size, it has a complex surface featuring nitrogen ice plains, mountain ranges of water ice, and a thin atmosphere.",
    facts: [
      { label: "Orbit Period", value: "248 Earth years" },
      { label: "Diameter", value: "2,377 km" },
      { label: "Moons", value: "5" },
      { label: "Rotation", value: "153.3 hours" },
    ]
  },
];

/* ── TEXTURE & BLEND MAPS ── */
const textureMap = {
  sun: ['textures/sunmap.jpg','textures/sun_surface.jpg','textures/stars.jpg'],
  mercury: ['textures/mercury_color.jpg','textures/mercury_bump.jpg','textures/mercury_surface.jpg'],
  venus: ['textures/venus_surface.jpg','textures/venus_clouds.jpg'],
  earth: ['textures/earth_daymap.jpg','textures/earth_nightmap.jpg','textures/earth_clouds.jpg','textures/earth_bump.jpg','textures/earth_specular.jpg'],
  mars: ['textures/mars_surface.jpg','textures/mars_bump.jpg','textures/mars_normal.jpg'],
  jupiter: ['textures/jupiter_map.jpg'],
  saturn: ['textures/saturn_map.jpg','textures/saturn_rings.png','textures/saturn_ring.png','textures/saturn_color.jpg'],
  uranus: ['textures/uranus_map.jpg','textures/uranus.jpg','textures/uranus_rings.png'],
  neptune: ['textures/neptune_map.jpg','textures/neptune_surface.jpg'],
  pluto: ['textures/pluto_map.jpg','textures/pluto_bump.jpg','textures/charon_map.jpg']
};

const blendMap = {
  sun: 'codes/sun.blend', mercury: 'codes/mercury.blend', venus: 'codes/venus.blend',
  earth: 'codes/earth.blend', mars: 'codes/mars.blend', jupiter: 'codes/jupiter.blend',
  saturn: 'codes/saturn.blend', uranus: 'codes/uranus.blend', neptune: 'codes/neptune.blend',
  pluto: 'codes/pluto.blend'
};

// Whole-solar project entry (UI access for downloadable .blend and notes)
const wholePlanet = {
  id: 'whole_solar', tag: 'Project', name: 'Whole Solar System', file: '', page: 'index.html',
  orbitalPeriod: 1, desc: 'Full solar system render and project files.', facts: [
    { label: 'Content', value: 'Full render + assets' },
    { label: 'Format', value: 'Blender .blend + textures + notes' },
  ]
};

// Add to blendMap so modal download logic works for the project
blendMap[wholePlanet.id] = 'codes/whole_solar.blend';

/* ── BUILD VIDEO GRID ── */
const grid = document.getElementById('planet-video-grid');
planets.forEach((planet) => {
  const block = document.createElement('div');
  block.className = 'planet-video-block';
  block.setAttribute('role', 'button');
  block.setAttribute('tabindex', '0');
  block.setAttribute('aria-label', `Open ${planet.name} details`);

  block.innerHTML = `
        <video autoplay muted loop playsinline preload="metadata">
          <source src="${getLocalBlenderVideoSrc(planet.file)}" type="video/mp4" />
        </video>
        <div class="planet-video-overlay">
          <div class="planet-video-tag">${planet.tag}</div>
          <div class="planet-video-name">${planet.name}</div>
          <div class="planet-video-hint">
            <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;">
              <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.4"/>
              <path d="M6 8h4M8 6l2 2-2 2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Click to explore
          </div>
        </div>
      `;

  block.addEventListener('click', () => openModal(planet));
  block.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openModal(planet); }
  });
  grid.appendChild(block);
});

  // Hook up hero 'Whole Solar System' project card
  const openWholeBtn = document.getElementById('open-whole-project');
  const downloadWholeBlend = document.getElementById('download-whole-blend');
  if (openWholeBtn) openWholeBtn.addEventListener('click', () => openModal(wholePlanet));
  if (downloadWholeBlend) {
    downloadWholeBlend.href = blendMap[wholePlanet.id] || '#';
    if (!blendMap[wholePlanet.id]) downloadWholeBlend.style.display = 'none';
  }

/* ── MODAL REFS ── */
const backdrop             = document.getElementById('modal-backdrop');
const modal                = document.getElementById('modal');
const modalVideo           = document.getElementById('modal-video');
const modalSrc             = document.getElementById('modal-video-src');
const modalBadge           = document.getElementById('modal-badge');
const modalTitle           = document.getElementById('modal-planet-title');
const modalDesc            = document.getElementById('modal-desc');
const modalFacts           = document.getElementById('modal-facts');
const modalDownloadBlend   = document.getElementById('modal-download-blend');
const modalDownloadTextures= document.getElementById('modal-download-textures');
const modalCodeBlock       = document.getElementById('planet-code-block');
const modalCodeContent     = document.getElementById('planet-code-content');
const codeCopyBtn          = document.getElementById('code-copy-btn');
const codeDownloadTxtBtn   = document.getElementById('code-download-txt-btn');
const codeDownloadPyBtn    = document.getElementById('code-download-py-btn');
const closeBtns            = [document.getElementById('modal-close'), document.getElementById('modal-close-btn')];
const fsBtn                = document.getElementById('modal-fullscreen-btn');

/* ── AGE CALCULATOR REFS ── */
const calcPlanetName    = document.getElementById('calc-planet-name');
const ageInput          = document.getElementById('age-input');
const ageCalcBtn        = document.getElementById('age-calc-btn');
const ageError          = document.getElementById('age-error');
const ageErrorMsg       = document.getElementById('age-error-msg');
const ageResult         = document.getElementById('age-result');
const ageNoCalc         = document.getElementById('age-no-calc');
const ageCalcEl         = document.getElementById('age-calc');
const resultPlanetLabel = document.getElementById('result-planet-label');
const resultPlanetBadge = document.getElementById('result-planet-badge');
const resultValue       = document.getElementById('result-value');
const resultBreakdown   = document.getElementById('result-breakdown');

let currentPlanet = null;
let currentCodeToken = 0;
const planetCodeCache = new Map();

function getPlanetCodeUrl(planetId) {
  return `text%20file/${planetId}.txt`;
}

async function loadPlanetCode(planet) {
  const loadToken = ++currentCodeToken;
  const codeUrl = getPlanetCodeUrl(planet.id);

  modalCodeContent.textContent = 'Loading code...';
  codeCopyBtn.disabled = true;
  codeDownloadTxtBtn.disabled = true;
  codeDownloadPyBtn.disabled = true;
  codeCopyBtn.textContent = 'Copy code';
  codeDownloadTxtBtn.textContent = 'Download .txt';
  codeDownloadPyBtn.textContent = 'Download .py';
  codeCopyBtn.classList.remove('copied');
  codeDownloadTxtBtn.classList.remove('done');
  codeDownloadPyBtn.classList.remove('done');

  try {
    let codeText = planetCodeCache.get(codeUrl);

    if (!codeText) {
      const response = await fetch(codeUrl, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Failed to load ${codeUrl}`);
      }
      codeText = await response.text();
      planetCodeCache.set(codeUrl, codeText);
    }

    if (loadToken !== currentCodeToken || !currentPlanet || currentPlanet.id !== planet.id) return;

    modalCodeContent.textContent = codeText.trimEnd() || 'No code available for this planet.';
    codeCopyBtn.disabled = false;
    codeDownloadTxtBtn.disabled = false;
    codeDownloadPyBtn.disabled = false;
  } catch {
    if (loadToken !== currentCodeToken || !currentPlanet || currentPlanet.id !== planet.id) return;

    modalCodeContent.textContent = 'Unable to load this planet code file.';
    codeCopyBtn.disabled = true;
    codeDownloadTxtBtn.disabled = true;
    codeDownloadPyBtn.disabled = true;
  }
}

async function copyPlanetCode() {
  const codeText = modalCodeContent.textContent || '';
  if (!codeText || codeCopyBtn.disabled) return;

  try {
    await navigator.clipboard.writeText(codeText);
    codeCopyBtn.textContent = 'Copied';
    codeCopyBtn.classList.add('copied');
    setTimeout(() => {
      codeCopyBtn.textContent = 'Copy code';
      codeCopyBtn.classList.remove('copied');
    }, 1400);
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(modalCodeContent);
    selection.removeAllRanges();
    selection.addRange(range);
    document.execCommand('copy');
    selection.removeAllRanges();
  }
}

function downloadPlanetCode(extension) {
  const codeText = modalCodeContent.textContent || '';
  const targetBtn = extension === 'py' ? codeDownloadPyBtn : codeDownloadTxtBtn;
  if (!codeText || targetBtn.disabled) return;

  const baseName = currentPlanet?.id ? `${currentPlanet.id}-code` : 'planet-code';
  const blob = new Blob([codeText], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${baseName}.${extension}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);

  targetBtn.textContent = 'Downloaded';
  targetBtn.classList.add('done');
  setTimeout(() => {
    targetBtn.textContent = extension === 'py' ? 'Download .py' : 'Download .txt';
    targetBtn.classList.remove('done');
  }, 1400);
}

/* ── AGE VALIDATION & CALCULATION ── */
function resetCalcUI() {
  ageInput.value = '';
  ageInput.classList.remove('error');
  ageError.classList.remove('visible');
  ageResult.classList.remove('visible');
  ageNoCalc.classList.remove('visible');
}

function showError(msg) {
  ageErrorMsg.textContent = msg;
  ageError.classList.add('visible');
  ageInput.classList.add('error');
  ageResult.classList.remove('visible');
}

function clearError() {
  ageError.classList.remove('visible');
  ageInput.classList.remove('error');
}

function calculateAge() {
  clearError();

  const raw = ageInput.value.trim();

  // Empty check
  if (raw === '') {
    showError('Please enter your age to calculate.');
    return;
  }

  // Must be a number
  if (isNaN(raw) || raw === '') {
    showError('That doesn\'t look like a number. Please enter a valid age.');
    return;
  }

  const age = Number(raw);

  // Must be an integer
  if (!Number.isFinite(age)) {
    showError('Please enter a finite number.');
    return;
  }

  // Must be positive
  if (age <= 0) {
    showError('Age must be greater than 0.');
    return;
  }

  // Must be a reasonable age
  if (age > 150) {
    showError('Please enter a realistic age (1 – 150 Earth years).');
    return;
  }

  // Must be a whole number (or close to it)
  if (age !== Math.floor(age) && !String(raw).includes('.')) {
    showError('Please enter a whole number for your age.');
    return;
  }

  // No orbital period (Sun)
  if (!currentPlanet.orbitalPeriod) {
    ageNoCalc.classList.add('visible');
    ageResult.classList.remove('visible');
    return;
  }

  // ── Calculate Planet Age ──
  const planetAgeInYears = age / currentPlanet.orbitalPeriod;
  
  // Break down into years, months, days
  const wholeYears = Math.floor(planetAgeInYears);
  const remaining = (planetAgeInYears - wholeYears) * 12; // Convert fractional year to months
  const months = Math.floor(remaining);
  const remainingFraction = (remaining - months);
  const days = Math.round(remainingFraction * 30.44); // Average days per month
  
  // Format main display
  const displayYears = wholeYears > 0 ? wholeYears : planetAgeInYears.toFixed(2);
  resultValue.textContent = displayYears;
  resultPlanetLabel.textContent = currentPlanet.name;
  resultPlanetBadge.textContent = currentPlanet.name;

  // Build breakdown grid
  const breakdownHTML = `
        <div class="age-breakdown-item">
          <div class="age-breakdown-value">${wholeYears}</div>
          <div class="age-breakdown-unit">Year${wholeYears !== 1 ? 's' : ''}</div>
        </div>
        <div class="age-breakdown-item">
          <div class="age-breakdown-value">${months}</div>
          <div class="age-breakdown-unit">Month${months !== 1 ? 's' : ''}</div>
        </div>
        <div class="age-breakdown-item">
          <div class="age-breakdown-value">${days}</div>
          <div class="age-breakdown-unit">Day${days !== 1 ? 's' : ''}</div>
        </div>
      `;
  resultBreakdown.innerHTML = breakdownHTML;
  
  // Calculation explanation
  const resultCalc = document.getElementById('result-calculation');
  const orbitalText = currentPlanet.orbitalPeriod === 1 
    ? 'Earth year (orbital period = Earth orbit)'
    : `${currentPlanet.orbitalPeriod} Earth years (${currentPlanet.name}'s orbital period)`;
  resultCalc.innerHTML = `<strong>${age}</strong> Earth years ÷ <strong>${currentPlanet.orbitalPeriod}</strong> ${orbitalText} = <strong>${wholeYears} yrs, ${months} mo, ${days} days</strong>`;

  ageResult.classList.add('visible');
  ageNoCalc.classList.remove('visible');
}

// Trigger on button click
ageCalcBtn.addEventListener('click', calculateAge);

// Trigger on Enter key in input
ageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') calculateAge();
});

// Clear error as user types
ageInput.addEventListener('input', () => {
  if (ageInput.classList.contains('error')) clearError();
  ageResult.classList.remove('visible');
  ageNoCalc.classList.remove('visible');
});

codeCopyBtn.addEventListener('click', copyPlanetCode);
codeDownloadTxtBtn.addEventListener('click', () => downloadPlanetCode('txt'));
codeDownloadPyBtn.addEventListener('click', () => downloadPlanetCode('py'));

/* ── OPEN MODAL ── */
function openModal(planet) {
  currentPlanet = planet;

  // Content
  modalBadge.textContent = planet.tag;
  modalTitle.textContent = planet.name;
  modalDesc.textContent  = planet.desc;

  // Facts
  modalFacts.innerHTML = planet.facts.map(f => `
        <div class="modal-fact">
          <div class="modal-fact-label">${f.label}</div>
          <div class="modal-fact-value">${f.value}</div>
        </div>
      `).join('');

  // Age calculator labels
  calcPlanetName.textContent = planet.name;
  resetCalcUI();

  // Hide age calculator for the whole-solar project (it does not apply there)
  if (planet.id === 'whole_solar') {
    if (ageCalcEl) ageCalcEl.style.display = 'none';
  } else {
    if (ageCalcEl) ageCalcEl.style.display = '';
  }

  // Code block
  modalCodeBlock.style.display = '';
  loadPlanetCode(planet);

  // Hide Sun note by default; it'll show on calculate if needed
  ageNoCalc.classList.remove('visible');

  // Video source
  modalVideo.hidden = false;
  modalSrc.src = getLocalBlenderVideoSrc(planet.file);
  modalVideo.load();
  modalVideo.play().catch(() => {});

  // Blend download
  if (blendMap[planet.id]) {
    modalDownloadBlend.href = blendMap[planet.id];
    modalDownloadBlend.style.display = '';
    modalDownloadBlend.setAttribute('download', '');
  } else {
    modalDownloadBlend.style.display = 'none';
  }

  // Textures download
  if (textureMap[planet.id] && textureMap[planet.id].length) {
    modalDownloadTextures.style.display = '';
    modalDownloadTextures.disabled = false;
    modalDownloadTextures.onclick = (e) => {
      e.preventDefault();
      textureMap[planet.id].forEach((f, idx) => {
        setTimeout(() => {
          const a = document.createElement('a');
          a.href = f; a.download = f.split('/').pop();
          document.body.appendChild(a); a.click(); a.remove();
        }, idx * 250);
      });
    };
  } else {
    modalDownloadTextures.style.display = 'none';
  }


  // Open
  backdrop.classList.add('open');
  document.body.style.overflow = 'hidden';
  modal.scrollTop = 0;
  // Focus the age input but avoid scrolling the modal into view.
  // Use the preventScroll option when available, with safe fallbacks.
  setTimeout(() => {
    try {
      ageInput.focus({ preventScroll: true });
    } catch (err) {
      try { ageInput.focus(); } catch (err2) { /* ignore */ }
    }
  }, 400);
}

/* ── CLOSE MODAL ── */
function closeModal() {
  backdrop.classList.remove('open');
  document.body.style.overflow = '';
  modalVideo.pause();
  modalSrc.src = '';
  modalVideo.load();
  modalVideo.hidden = true;
  currentPlanet = null;
  currentCodeToken += 1;
}

closeBtns.forEach(b => b.addEventListener('click', closeModal));
backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeModal(); });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && backdrop.classList.contains('open')) closeModal();
});

/* Fullscreen */
fsBtn.addEventListener('click', () => {
  if (modalVideo.requestFullscreen) modalVideo.requestFullscreen();
  else if (modalVideo.webkitRequestFullscreen) modalVideo.webkitRequestFullscreen();
  else if (modalVideo.mozRequestFullScreen) modalVideo.mozRequestFullScreen();
});

/* Planet selector removed from hero; no JS needed. */

/* ── STARFIELD SETUP (depends on ../starfield.js being loaded first) ── */
if (typeof Starfield !== 'undefined') {
  Starfield.setup({
    starColor: "rgb(58, 85, 217)", hueJitter: 0, trailLength: 0.8,
    baseSpeed: 3, maxAcceleration: 2, accelerationRate: 0.05, decelerationRate: 0.05,
    minSpawnRadius: 80, maxSpawnRadius: 500
  });
}
