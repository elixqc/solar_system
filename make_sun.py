import os

source_path = 'c:/laragon/www/ma-portfolio/blender/earth.html'
dest_path = 'c:/laragon/www/ma-portfolio/blender/sun.html'

with open(source_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sun specific replacements
content = content.replace('Earth — Blender Solar System', 'Sun — Blender Solar System')
content = content.replace('<div class="nav-badge">Earth</div>', '<div class="nav-badge">Sun</div>')
content = content.replace('<div class="hero-eyebrow">Earth</div>', '<div class="hero-eyebrow">Sun</div>')
content = content.replace('The living world we call <span class="accent">home</span>.', 'The heart of our <span class="accent">solar system</span>.')
content = content.replace('Earth is the third planet from the Sun and the only known world with surface oceans, active plate tectonics, and life. Its atmosphere is rich in nitrogen and oxygen, which supports stable temperatures and complex ecosystems.', 'The Sun is a yellow dwarf star, a hot ball of glowing gases at the heart of our solar system. Its gravity holds the solar system together, keeping everything from the biggest planets to the smallest debris in its orbit.')
content = content.replace('Use the render to show oceans, cloud cover, and day-night motion.', 'Use the render to show the glowing corona and active surface flares.')
content = content.replace('This page can also anchor the whole solar-system series intro.', 'This page introduces the central star of the solar system.')
content = content.replace('Earth render and explanation.', 'Sun render and explanation.')
content = content.replace('media/earth.mp4', 'media/sun.mp4')
content = content.replace('Earth in a 10-second loop.', 'The Sun in a 10-second loop.')
content = content.replace('Earth summary', 'Sun summary')
content = content.replace('Earth has liquid water on its surface, a protective magnetic field, and an atmosphere that helps regulate climate. It is the only planet known to support life as we know it.', 'The Sun is composed of hydrogen and helium. It is about 4.6 billion years old and produces energy through nuclear fusion in its core.')

# Age calculator replacements
content = content.replace('<div class="age-calculator-label">Age converter</div>', '<div class="age-calculator-label">Rotation calculator</div>')
content = content.replace('Enter your age in Earth years and see the Earth equivalent. Since this is Earth itself, the number stays the same.', 'Enter your age in Earth years to calculate how many times the Sun has rotated on its axis since you were born (approx 27 Earth days per rotation).')
content = content.replace('earth-age-', 'sun-age-')
content = content.replace('Earth age', 'age')
content = content.replace('Earth time', 'Sun rotations')

# Replace the formatting function for the sun
script_old = """    function formatPlanetAge(earthAge, planetYearInEarthDays) {
      const safeEarthAge = Number.isFinite(earthAge) && earthAge >= 0 ? earthAge : 0;
      const totalPlanetYears = (safeEarthAge * 365.25) / planetYearInEarthDays;
      let years = Math.floor(totalPlanetYears);
      let months = Math.floor((totalPlanetYears - years) * 12);
      let days = Math.round((((totalPlanetYears - years) * 12) - months) * 30);

      if (days >= 30) {
        days -= 30;
        months += 1;
      }

      if (months >= 12) {
        months -= 12;
        years += 1;
      }

      return `${years} year${years === 1 ? '' : 's'}, ${months} month${months === 1 ? '' : 's'}, ${days} day${days === 1 ? '' : 's'}`;
    }

    function updateEarthAge() {
      const earthAge = Number(earthAgeInput.value);
      const earthAgeValue = formatPlanetAge(earthAge, 365.25);
      earthAgeOutput.innerHTML = `You would be about <strong>${earthAgeValue}</strong> Earth time.`;
    }"""

script_new = """    function formatSunRotations(earthAge) {
      const safeEarthAge = Number.isFinite(earthAge) && earthAge >= 0 ? earthAge : 0;
      const totalRotations = Math.floor((safeEarthAge * 365.25) / 27);
      return `${totalRotations} rotations`;
    }

    function updateEarthAge() {
      const earthAge = Number(earthAgeInput.value);
      const rotations = formatSunRotations(earthAge);
      earthAgeOutput.innerHTML = `The Sun has completed about <strong>${rotations}</strong> since you were born.`;
    }"""
content = content.replace(script_old, script_new)

# Details grid
content = content.replace('Life support', 'Energy')
content = content.replace('Water, atmosphere, and chemistry.', 'Nuclear fusion and energy.')
content = content.replace("Earth's liquid water, moderate temperatures, and chemical cycles make it the only known world with a biosphere that can sustain complex life.", 'The Sun produces energy through nuclear fusion in its core, converting hydrogen into helium and releasing immense amounts of light and heat.')
content = content.replace('A balanced day and year.', 'Differential rotation.')
content = content.replace('Earth completes one rotation in about 24 hours and one orbit in about 365.25 days. That stable rhythm shapes weather, seasons, and daily life.', 'Because the Sun is a ball of gas, it does not rotate rigidly. Its equator rotates once every 24 days, while its poles take over 30 days.')

# Footer
content = content.replace('Earth · Blender Planet Page', 'Sun · Blender Planet Page')
content = content.replace('blender/media/earth.mp4', 'blender/media/sun.mp4')

# Navigator
# Current Earth marker should be removed
content = content.replace('<a href="earth.html" class="planet-card current">', '<a href="earth.html" class="planet-card ">')
content = content.replace('<div class="planet-tag">Current</div>\\n            <h3>Earth</h3>', '<div class="planet-tag">Planet 03</div>\\n            <h3>Earth</h3>')
content = content.replace('<div class="planet-tag">Current</div>\\n            <h3>Earth</h3>', '<div class="planet-tag">Planet 03</div>\\n            <h3>Earth</h3>')

# The current planet-tag in HTML has real newlines and spaces, so let's do a more robust replace for the Earth block
earth_block_old = """          <a href="earth.html" class="planet-card current">
            <div class="planet-tag">Current</div>
            <h3>Earth</h3>"""
earth_block_new = """          <a href="earth.html" class="planet-card ">
            <div class="planet-tag">Planet 03</div>
            <h3>Earth</h3>"""
content = content.replace(earth_block_old, earth_block_new)

new_planet_card = """          <a href="sun.html" class="planet-card current">
            <div class="planet-tag">Current</div>
            <h3>Sun</h3>
            <p>The central star of our solar system.</p>
            <div class="planet-arrow">↗</div>
          </a>
"""
content = content.replace('<a href="mercury.html" class="planet-card ">', new_planet_card + '          <a href="mercury.html" class="planet-card ">')

with open(dest_path, 'w', encoding='utf-8') as f:
    f.write(content)
