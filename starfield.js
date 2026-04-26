const Starfield = (function() {
  let canvas, ctx;
  let stars = [];
  let width, height;
  let mouseX, mouseY;
  let targetMouseX, targetMouseY;
  
  let config = {
    starColor: "255, 255, 255",
    hueJitter: 0,
    trailLength: 0.8,
    baseSpeed: 3,
    maxAcceleration: 2,
    accelerationRate: 0.05,
    decelerationRate: 0.05,
    minSpawnRadius: 80,
    maxSpawnRadius: 500,
    starCount: 500
  };

  class Star {
    constructor() {
      this.reset(true);
    }
    reset(randomZ = false) {
      this.x = (Math.random() - 0.5) * width * 2;
      this.y = (Math.random() - 0.5) * height * 2;
      this.z = randomZ ? Math.random() * width : width;
      this.pz = this.z;
    }
    update(speed) {
      this.pz = this.z + (speed * config.trailLength * 10);
      this.z -= speed;
      if (this.z < 1) {
        this.reset();
      }
    }
    draw() {
      let cx = width / 2;
      let cy = height / 2;
      
      let sx = (this.x / this.z) * cx + cx;
      let sy = (this.y / this.z) * cy + cy;
      
      let px = (this.x / this.pz) * cx + cx;
      let py = (this.y / this.pz) * cy + cy;

      // Interactive cursor parallax
      let pdx = (targetMouseX - cx) * (1 - this.z / width) * 0.15;
      let pdy = (targetMouseY - cy) * (1 - this.z / width) * 0.15;

      sx += pdx; sy += pdy;
      px += pdx; py += pdy;

      if (sx < 0 || sx > width || sy < 0 || sy > height) {
        return;
      }

      let opacity = Math.max(0.1, 1 - (this.z / width));
      
      // Parse rgb() if user provides it
      let colorStr = config.starColor;
      if (colorStr.startsWith("rgb(")) {
        colorStr = colorStr.replace("rgb(", "").replace(")", "");
      }

      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(sx, sy);
      ctx.strokeStyle = `rgba(${colorStr}, ${opacity})`;
      ctx.lineWidth = Math.max(0.5, (1 - this.z / width) * 2.5);
      ctx.stroke();
    }
  }

  function init(options) {
    if(options) Object.assign(config, options);
    
    // Bind to the hero section
    const container = document.getElementById('hero');
    if (!container) return;

    canvas = document.createElement('canvas');
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.zIndex = '0';
    canvas.style.pointerEvents = 'none'; // Ensure clicks pass through to buttons
    container.insertBefore(canvas, container.firstChild);
    
    ctx = canvas.getContext('2d');

    resize();
    window.addEventListener('resize', resize);
    
    mouseX = width / 2;
    mouseY = height / 2;
    targetMouseX = mouseX;
    targetMouseY = mouseY;

    // Track mouse over the hero section (hover, no dragging required)
    container.addEventListener('mousemove', (e) => {
      const rect = container.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    });

    // Reset mouse to center when leaving hero
    container.addEventListener('mouseleave', () => {
      mouseX = width / 2;
      mouseY = height / 2;
    });

    for (let i = 0; i < config.starCount; i++) {
      stars.push(new Star());
    }

    requestAnimationFrame(animate);
  }

  function resize() {
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    canvas.width = width;
    canvas.height = height;
    targetMouseX = width / 2;
    targetMouseY = height / 2;
  }

  function animate() {
    targetMouseX += (mouseX - targetMouseX) * 0.05;
    targetMouseY += (mouseY - targetMouseY) * 0.05;

    // Speed increases as mouse moves further from the center
    let dx = mouseX - width / 2;
    let dy = mouseY - height / 2;
    let dist = Math.sqrt(dx * dx + dy * dy);
    let maxDist = Math.sqrt((width/2)**2 + (height/2)**2);
    let speedFactor = Math.min(1, dist / (maxDist * 0.5)); 

    let currentSpeed = config.baseSpeed + (speedFactor * config.maxAcceleration);

    // Use clearRect to keep the CSS gradient background visible
    ctx.clearRect(0, 0, width, height);

    stars.forEach(star => {
      star.update(currentSpeed);
      star.draw();
    });

    requestAnimationFrame(animate);
  }

  return {
    setup: function(options) {
      if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', () => init(options));
      } else {
        init(options);
      }
    }
  };
})();
