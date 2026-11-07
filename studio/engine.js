// Browser runtime for one film page. The page calls boot() with a pure draw
// function of time. Headless Chrome asks captureFrame(i) for every frame.

const LOOKS = {
  cinematic: {
    grade: "contrast(1.08) saturate(0.9)",
    vignette: 0.46,
    grain: 0.055,
    hold: 24,
    scanlines: 0,
    halftone: 0,
  },
  claymation: {
    grade: "saturate(1.06) contrast(1.04) sepia(0.14)",
    vignette: 0.3,
    grain: 0.045,
    hold: 12,
    scanlines: 0,
    halftone: 0,
  },
  "anime-cel": {
    grade: "saturate(1.22) contrast(1.08)",
    vignette: 0.06,
    grain: 0,
    hold: 12,
    scanlines: 0,
    halftone: 0,
  },
  storybook: {
    grade: "saturate(0.8) contrast(0.92) brightness(1.05)",
    vignette: 0.2,
    grain: 0.05,
    hold: 24,
    scanlines: 0,
    halftone: 0,
  },
  papercut: {
    grade: "contrast(1.08) saturate(0.94)",
    vignette: 0.14,
    grain: 0.03,
    hold: 12,
    scanlines: 0,
    halftone: 0,
  },
  vhs: {
    grade: "saturate(1.28) contrast(1.12) hue-rotate(-8deg)",
    vignette: 0.42,
    grain: 0.08,
    hold: 24,
    scanlines: 0.22,
    halftone: 0,
  },
  "glossy-ad": {
    grade: "contrast(1.04) saturate(1.06) brightness(1.03)",
    vignette: 0,
    grain: 0,
    hold: 24,
    scanlines: 0,
    halftone: 0,
  },
  ink: {
    grade: "grayscale(0.62) sepia(0.22) contrast(1.16)",
    vignette: 0.24,
    grain: 0.035,
    hold: 12,
    scanlines: 0,
    halftone: 0.22,
  },
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function ease(t) {
  const x = clamp(t, 0, 1);
  return x * x * (3 - 2 * x);
}

function mulberry32(seed) {
  let state = seed >>> 0;
  return function rand() {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function even(value, fallback) {
  const n = Number.isFinite(value) && value >= 2 ? Math.round(value) : fallback;
  const positive = Math.max(2, Math.round(n));
  return positive % 2 === 0 ? positive : positive - 1;
}

function hexChannels(color) {
  const n = Number.parseInt(color.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function normalize(v) {
  const length = Math.hypot(v.x, v.y, v.z) || 1;
  return { x: v.x / length, y: v.y / length, z: v.z / length };
}

function ensureFont() {
  if (document.getElementById("studio-font")) return;
  const style = document.createElement("style");
  style.id = "studio-font";
  style.textContent = `
    @font-face {
      font-family: "Studio Sans";
      src: url("/system-font/DejaVuSans.ttf");
      font-weight: 400;
    }
    @font-face {
      font-family: "Studio Sans";
      src: url("/system-font/DejaVuSans-Bold.ttf");
      font-weight: 700;
    }
  `;
  document.head.appendChild(style);
}

function makeTile(kind) {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  const image = ctx.createImageData(128, 128);
  const rand = mulberry32(kind === "dot" ? 99 : 41);
  for (let y = 0; y < 128; y += 1) {
    for (let x = 0; x < 128; x += 1) {
      const i = (y * 128 + x) * 4;
      if (kind === "dot") {
        const cx = x % 8;
        const cy = y % 8;
        const on = (cx - 3) ** 2 + (cy - 3) ** 2 < 3;
        const v = on ? 20 : 230;
        image.data[i] = image.data[i + 1] = image.data[i + 2] = v;
      } else {
        const v = Math.floor(rand() * 255);
        image.data[i] = image.data[i + 1] = image.data[i + 2] = v;
      }
      image.data[i + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
  return canvas;
}

function paintOverlay(ctx, width, height, look, frame, tiles) {
  if (look.grain > 0) {
    ctx.save();
    ctx.globalAlpha = look.grain;
    ctx.globalCompositeOperation = "overlay";
    const shift = (frame * 13) % 128;
    ctx.translate(shift, (frame * 7) % 128);
    ctx.fillStyle = ctx.createPattern(tiles.grain, "repeat");
    ctx.fillRect(-128, -128, width + 256, height + 256);
    ctx.restore();
  }
  if (look.halftone > 0) {
    ctx.save();
    ctx.globalAlpha = look.halftone;
    ctx.globalCompositeOperation = "multiply";
    ctx.fillStyle = ctx.createPattern(tiles.dot, "repeat");
    ctx.fillRect(0, 0, width, height);
    ctx.restore();
  }
  if (look.scanlines > 0) {
    ctx.fillStyle = `rgba(0, 0, 0, ${look.scanlines})`;
    for (let y = 0; y < height; y += 3) ctx.fillRect(0, y, width, 1);
  }
  if (look.vignette > 0) {
    const g = ctx.createRadialGradient(
      width / 2,
      height / 2,
      Math.min(width, height) * 0.3,
      width / 2,
      height / 2,
      Math.max(width, height) * 0.72,
    );
    g.addColorStop(0, "rgba(0, 0, 0, 0)");
    g.addColorStop(1, `rgba(0, 0, 0, ${look.vignette})`);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);
  }
}

function project(point, camera, width, height) {
  const depth = Math.max(0.2, point.z - camera.z);
  const scale = camera.fov / depth;
  return {
    x: width / 2 + (point.x - camera.x) * scale,
    y: height * 0.62 - (point.y - camera.y) * scale,
    z: depth,
  };
}

function mesh(ctx, faces, camera, light, width, height) {
  const lit = normalize(light);
  const drawn = faces.map((face) => {
    const [a, b, c] = face.points;
    const ux = b.x - a.x;
    const uy = b.y - a.y;
    const uz = b.z - a.z;
    const vx = c.x - a.x;
    const vy = c.y - a.y;
    const vz = c.z - a.z;
    const n = normalize({
      x: uy * vz - uz * vy,
      y: uz * vx - ux * vz,
      z: ux * vy - uy * vx,
    });
    const lamp = Math.abs(n.x * lit.x + n.y * lit.y + n.z * lit.z);
    const shade = 0.62 + 0.38 * clamp(lamp, 0, 1);
    const screen = face.points.map((point) => project(point, camera, width, height));
    const depth = (screen[0].z + screen[1].z + screen[2].z) / 3;
    return { screen, depth, shade, color: face.color };
  });
  drawn.sort((a, b) => b.depth - a.depth);
  for (const face of drawn) {
    const [r, g, b] = hexChannels(face.color);
    ctx.beginPath();
    ctx.moveTo(face.screen[0].x, face.screen[0].y);
    ctx.lineTo(face.screen[1].x, face.screen[1].y);
    ctx.lineTo(face.screen[2].x, face.screen[2].y);
    ctx.closePath();
    ctx.fillStyle = `rgb(${Math.round(r * face.shade)}, ${Math.round(g * face.shade)}, ${Math.round(b * face.shade)})`;
    ctx.fill();
  }
}

export function boot(film) {
  const canvas = document.querySelector("canvas");
  if (!canvas) throw new Error("film page needs a canvas");
  if (typeof film.draw !== "function") throw new Error("film.draw must be a function");
  const params = new URLSearchParams(location.search);
  const width = even(Number(params.get("w")), film.width);
  const height = even(Number(params.get("h")), film.height);
  const lookName = params.get("look") || film.look || "cinematic";
  const look = LOOKS[lookName] || LOOKS.cinematic;
  const fps = film.fps;
  const frames = Math.round(film.duration * fps);
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d", { alpha: false });
  const tiles = { grain: makeTile("grain"), dot: makeTile("dot") };
  const api = {
    w: width,
    h: height,
    clamp,
    lerp,
    ease,
    rng: mulberry32,
    font(size, weight = 700) {
      return `${weight} ${Math.round(size)}px "Studio Sans", "DejaVu Sans", sans-serif`;
    },
    safe() {
      return {
        x: width * 0.08,
        y: height * 0.08,
        w: width * 0.84,
        h: height * 0.84,
      };
    },
    mesh(context, faces, camera, light) {
      mesh(context, faces, camera, light, width, height);
    },
  };

  function timeAt(frame) {
    let t = frame / fps;
    if (look.hold && look.hold < fps) t = Math.floor(t * look.hold) / look.hold;
    return Math.min(t, Math.max(0, film.duration - 1 / fps));
  }

  function drawFrame(frame) {
    const t = timeAt(frame);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.filter = "none";
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, width, height);
    ctx.save();
    ctx.filter = look.grade || "none";
    film.draw(ctx, t, api);
    ctx.restore();
    ctx.filter = "none";
    paintOverlay(ctx, width, height, look, frame, tiles);
  }

  window.captureFrame = (frame) => {
    drawFrame(frame);
    return canvas.toDataURL("image/jpeg", 0.92);
  };
  window.studioExport = () => ({
    title: film.title,
    fps,
    width,
    height,
    frames,
    duration: film.duration,
    look: lookName,
    purpose: film.purpose || "cinematic",
    sound: film.sound || [],
    voice: film.voice || [],
    music: film.music || null,
    renderer: "canvas2d",
  });

  ensureFont();
  window.STUDIO_READY = (async () => {
    await document.fonts.load('700 64px "Studio Sans"');
    await document.fonts.ready;
    drawFrame(0);
    return window.studioExport();
  })();

  if (!params.has("capture")) {
    const hud = document.createElement("div");
    hud.textContent = "preview · sound is in the rendered mp4";
    hud.style.cssText = "position:fixed;left:10px;bottom:8px;color:rgba(255,255,255,.8);font:12px/1.4 sans-serif;text-shadow:0 1px 2px #000";
    document.body.appendChild(hud);
    const started = performance.now();
    const loop = (now) => {
      const t = ((now - started) / 1000) % film.duration;
      drawFrame(Math.min(frames - 1, Math.floor(t * fps)));
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
}

export { LOOKS };
