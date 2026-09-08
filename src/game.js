/* ===========================================================================
   RIVENBROOK - a small pixel-art RPG
   Field exploration + an FF4/5/6-flavoured ATB battle system.
   All art comes from spritecook (tools/spritecook.py); all maps from mapcook.
   =========================================================================== */
'use strict';

const VW = 320, VH = 180, TILE = 16;

/* --------------------------------------------------------------- canvas -- */
const canvas = document.getElementById('screen');
const ctx = canvas.getContext('2d', { alpha: false });
canvas.width = VW; canvas.height = VH;
ctx.imageSmoothingEnabled = false;

function fitCanvas() {
  const pad = 8;
  const scale = Math.max(1, Math.floor(Math.min(
    (window.innerWidth - pad) / VW, (window.innerHeight - pad) / VH)));
  canvas.style.width = (VW * scale) + 'px';
  canvas.style.height = (VH * scale) + 'px';
}
window.addEventListener('resize', fitCanvas);

/* ---------------------------------------------------------------- atlas -- */
const atlas = new Image();
const FRAMES = ATLAS_META.frames;

function spr(name, dx, dy, opts) {
  const f = FRAMES[name];
  if (!f) return;
  const s = (opts && opts.scale) || 1;
  ctx.drawImage(atlas, f[0], f[1], f[2], f[3],
    Math.round(dx), Math.round(dy), f[2] * s, f[3] * s);
}
function sprSize(name) { const f = FRAMES[name]; return f ? [f[2], f[3]] : [0, 0]; }

/* ----------------------------------------------------------------- text -- */
const FontCache = {
  keys: Object.keys(FONT),
  index: {},
  base: null,
  tints: {},
  build() {
    const c = document.createElement('canvas');
    c.width = GLYPH_W * this.keys.length; c.height = GLYPH_H;
    const g = c.getContext('2d');
    g.fillStyle = '#ffffff';
    this.keys.forEach((ch, i) => {
      this.index[ch] = i;
      const rows = FONT[ch];
      for (let y = 0; y < FONT_ROWS; y++)
        for (let x = 0; x < FONT_W; x++)
          if (rows[y][x] === '1') g.fillRect(i * GLYPH_W + x, y, 1, 1);
    });
    this.base = c;
  },
  tint(color) {
    if (this.tints[color]) return this.tints[color];
    const c = document.createElement('canvas');
    c.width = this.base.width; c.height = this.base.height;
    const g = c.getContext('2d');
    g.drawImage(this.base, 0, 0);
    g.globalCompositeOperation = 'source-in';
    g.fillStyle = color;
    g.fillRect(0, 0, c.width, c.height);
    this.tints[color] = c;
    return c;
  }
};

function textWidth(str) { return str.length * GLYPH_W; }

function drawText(str, x, y, color, opts) {
  opts = opts || {};
  str = String(str);
  x = Math.round(x); y = Math.round(y);
  if (opts.align === 'center') x -= Math.round(textWidth(str) / 2);
  else if (opts.align === 'right') x -= textWidth(str);
  if (opts.shadow !== false) {
    const sheet = FontCache.tint(opts.shadowColor || '#12101c');
    blitText(sheet, str, x + 1, y + 1);
  }
  blitText(FontCache.tint(color || '#f4f4ec'), str, x, y);
  return textWidth(str);
}

function blitText(sheet, str, x, y) {
  for (let i = 0; i < str.length; i++) {
    const idx = FontCache.index[str[i]];
    if (idx === undefined) continue;
    ctx.drawImage(sheet, idx * GLYPH_W, 0, GLYPH_W, GLYPH_H, x + i * GLYPH_W, y, GLYPH_W, GLYPH_H);
  }
}

function wrapText(str, maxChars) {
  const words = String(str).split(' ');
  const lines = []; let line = '';
  for (const w of words) {
    if (line && (line + ' ' + w).length > maxChars) { lines.push(line); line = w; }
    else line = line ? line + ' ' + w : w;
  }
  if (line) lines.push(line);
  return lines;
}

/* -------------------------------------------------------------- windows -- */
/* The menu chrome: a beveled navy panel with a bright inner rule, the look
   the 16-bit Final Fantasy menus used. */
function drawWindow(x, y, w, h, opts) {
  opts = opts || {};
  const grad = ctx.createLinearGradient(0, y, 0, y + h);
  const tone = opts.tone || 'blue';
  if (tone === 'blue') { grad.addColorStop(0, '#2c47a8'); grad.addColorStop(1, '#111a4e'); }
  else if (tone === 'dark') { grad.addColorStop(0, '#241f38'); grad.addColorStop(1, '#12101f'); }
  else { grad.addColorStop(0, '#7a2b3c'); grad.addColorStop(1, '#3a1120'); }

  ctx.fillStyle = '#0b0a16';
  ctx.fillRect(x + 1, y, w - 2, h);
  ctx.fillRect(x, y + 1, w, h - 2);
  ctx.fillStyle = grad;
  ctx.fillRect(x + 2, y + 1, w - 4, h - 2);
  ctx.fillRect(x + 1, y + 2, w - 2, h - 4);

  ctx.fillStyle = opts.frame || '#9db4ea';
  ctx.fillRect(x + 2, y + 1, w - 4, 1);
  ctx.fillRect(x + 2, y + h - 2, w - 4, 1);
  ctx.fillRect(x + 1, y + 2, 1, h - 4);
  ctx.fillRect(x + w - 2, y + 2, 1, h - 4);
  ctx.fillStyle = '#e8eeff';
  ctx.fillRect(x + 2, y + 1, 2, 1); ctx.fillRect(x + w - 4, y + 1, 2, 1);
  ctx.fillRect(x + 1, y + 2, 1, 2); ctx.fillRect(x + w - 2, y + 2, 1, 2);
  ctx.fillStyle = '#4d63b4';
  ctx.fillRect(x + 3, y + 3, w - 6, 1);
}

function drawCursor(x, y, t) {
  const bob = Math.sin(t * 8) > 0 ? 1 : 0;
  x = Math.round(x + bob); y = Math.round(y);
  const tri = (ox, oy, h, color) => {
    ctx.fillStyle = color;
    const half = (h - 1) / 2;
    for (let i = 0; i < h; i++) {
      const w = Math.round(half + 1 - Math.abs(i - half));
      ctx.fillRect(x + ox, y + oy + i, w, 1);
    }
  };
  tri(-1, -1, 11, '#241b26');
  tri(0, 0, 9, '#e0a83c');
  ctx.fillStyle = '#ffeda8';
  ctx.fillRect(x, y + 1, 3, 1);
  ctx.fillRect(x, y + 2, 2, 1);
  ctx.fillRect(x, y + 3, 4, 1);
}

function drawBar(x, y, w, h, pct, colorA, colorB) {
  pct = Math.max(0, Math.min(1, pct));
  ctx.fillStyle = '#0b0a16'; ctx.fillRect(x - 1, y - 1, w + 2, h + 2);
  ctx.fillStyle = '#2a2a44'; ctx.fillRect(x, y, w, h);
  const fill = Math.round(w * pct);
  if (fill > 0) {
    ctx.fillStyle = colorB; ctx.fillRect(x, y, fill, h);
    ctx.fillStyle = colorA; ctx.fillRect(x, y, fill, 1);
  }
}

/* ---------------------------------------------------------------- input -- */
const Input = {
  down: {}, tapped: {},
  bind: {
    ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right',
    KeyW: 'up', KeyS: 'down', KeyA: 'left', KeyD: 'right',
    KeyZ: 'confirm', Enter: 'confirm', Space: 'confirm',
    KeyX: 'cancel', Backspace: 'cancel',
    Escape: 'menu', KeyC: 'menu', ShiftLeft: 'menu',
    KeyM: 'mute'
  },
  init() {
    window.addEventListener('keydown', e => {
      const a = this.bind[e.code];
      if (!a) return;
      e.preventDefault();
      if (!this.down[a]) this.tapped[a] = true;
      this.down[a] = true;
    });
    window.addEventListener('keyup', e => {
      const a = this.bind[e.code];
      if (!a) return;
      e.preventDefault();
      this.down[a] = false;
    });
    window.addEventListener('blur', () => { this.down = {}; });
    this.initTouch();
  },
  initTouch() {
    const pad = document.getElementById('touch');
    if (!pad) return;
    if (!('ontouchstart' in window)) return;
    pad.style.display = 'block';
    pad.querySelectorAll('[data-act]').forEach(el => {
      const act = el.dataset.act;
      const on = e => { e.preventDefault(); if (!this.down[act]) this.tapped[act] = true; this.down[act] = true; el.classList.add('on'); };
      const off = e => { e.preventDefault(); this.down[act] = false; el.classList.remove('on'); };
      el.addEventListener('touchstart', on, { passive: false });
      el.addEventListener('touchend', off, { passive: false });
      el.addEventListener('touchcancel', off, { passive: false });
    });
  },
  tap(a) { return !!this.tapped[a]; },
  held(a) { return !!this.down[a]; },
  // Menus want a repeat after a short hold; this keeps list scrolling usable.
  repeat: {},
  nav(a, dt) {
    if (this.tap(a)) { this.repeat[a] = -0.28; return true; }
    if (!this.down[a]) { this.repeat[a] = 0; return false; }
    this.repeat[a] = (this.repeat[a] || 0) + dt;
    if (this.repeat[a] >= 0.08) { this.repeat[a] = 0; return true; }
    return false;
  },
  endFrame() { this.tapped = {}; }
};

/* ---------------------------------------------------------------- audio -- */
/* A tiny square-wave chip synth: three looping themes and a handful of SFX. */
const Audio_ = {
  ctxA: null, gain: null, muted: false, timer: null, track: null, step: 0,
  ensure() {
    if (this.ctxA) return true;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    this.ctxA = new AC();
    this.gain = this.ctxA.createGain();
    this.gain.gain.value = 0.16;
    this.gain.connect(this.ctxA.destination);
    return true;
  },
  resume() { if (this.ctxA && this.ctxA.state === 'suspended') this.ctxA.resume(); },
  blip(freq, dur, type, vol) {
    if (this.muted || !this.ensure()) return;
    this.resume();
    const t = this.ctxA.currentTime;
    const o = this.ctxA.createOscillator();
    const g = this.ctxA.createGain();
    o.type = type || 'square';
    o.frequency.setValueAtTime(freq, t);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol || 0.5, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + (dur || 0.1));
    o.connect(g); g.connect(this.gain);
    o.start(t); o.stop(t + (dur || 0.1) + 0.02);
  },
  sweep(f0, f1, dur, type) {
    if (this.muted || !this.ensure()) return;
    this.resume();
    const t = this.ctxA.currentTime;
    const o = this.ctxA.createOscillator();
    const g = this.ctxA.createGain();
    o.type = type || 'sawtooth';
    o.frequency.setValueAtTime(f0, t);
    o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
    g.gain.setValueAtTime(0.4, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(this.gain);
    o.start(t); o.stop(t + dur + 0.02);
  },
  sfx(name) {
    switch (name) {
      case 'cursor': this.blip(660, 0.05, 'square', 0.25); break;
      case 'confirm': this.blip(880, 0.07, 'square', 0.35); setTimeout(() => this.blip(1320, 0.07, 'square', 0.3), 45); break;
      case 'cancel': this.blip(300, 0.08, 'square', 0.3); break;
      case 'hit': this.sweep(420, 90, 0.14, 'square'); break;
      case 'crit': this.sweep(700, 120, 0.2, 'sawtooth'); break;
      case 'magic': this.sweep(300, 1400, 0.28, 'triangle'); break;
      case 'heal': [660, 880, 1100, 1320].forEach((f, i) => setTimeout(() => this.blip(f, 0.12, 'triangle', 0.3), i * 60)); break;
      case 'ko': this.sweep(400, 60, 0.5, 'sawtooth'); break;
      case 'item': this.blip(990, 0.06, 'triangle', 0.35); setTimeout(() => this.blip(1480, 0.1, 'triangle', 0.3), 60); break;
      case 'encounter': [880, 0, 880, 0, 1200].forEach((f, i) => setTimeout(() => f && this.sweep(f, f * 1.6, 0.09, 'square'), i * 70)); break;
      case 'victory': [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => this.blip(f, 0.22, 'square', 0.4), i * 130)); break;
      case 'levelup': [784, 988, 1175, 1568].forEach((f, i) => setTimeout(() => this.blip(f, 0.16, 'triangle', 0.4), i * 90)); break;
    }
  },
  // note tables: 0 = rest
  themes: {
    town: { bpm: 340, lead: [523,0,659,0,784,0,659,0, 587,0,698,0,880,0,698,0, 523,0,659,0,784,659,523,0, 494,0,587,0,494,0,440,0],
            bass: [131,0,196,0,131,0,196,0, 147,0,220,0,147,0,220,0, 131,0,196,0,131,0,196,0, 123,0,185,0,110,0,110,0] },
    field: { bpm: 380, lead: [440,494,523,587,659,587,523,494, 440,0,523,0,659,0,523,0, 392,440,494,523,587,523,494,440, 392,0,494,0,392,0,330,0],
             bass: [110,0,165,0,110,0,165,0, 131,0,196,0,131,0,196,0, 98,0,147,0,98,0,147,0, 110,0,165,0,110,110,110,0] },
    battle: { bpm: 480, lead: [659,0,659,622,659,0,784,0, 587,0,587,523,587,0,698,0, 659,0,659,622,659,784,880,784, 659,587,523,494,440,494,523,587],
              bass: [165,165,0,165,165,0,165,0, 147,147,0,147,147,0,147,0, 165,165,0,165,165,0,165,0, 110,110,110,110,147,147,165,165] },
    inn: { bpm: 260, lead: [659,0,784,0,880,0,784,0, 659,0,587,0,523,0,587,0],
           bass: [131,0,131,0,175,0,175,0, 196,0,196,0,131,0,131,0] }
  },
  play(name) {
    if (this.track === name) return;
    this.track = name;
    clearInterval(this.timer);
    this.step = 0;
    const th = this.themes[name];
    if (!th) return;
    const ms = 60000 / th.bpm;
    this.timer = setInterval(() => {
      if (this.muted) return;
      const i = this.step % th.lead.length;
      if (th.lead[i]) this.blip(th.lead[i], ms / 1000 * 0.9, 'square', 0.18);
      if (th.bass[i % th.bass.length]) this.blip(th.bass[i % th.bass.length], ms / 1000 * 1.1, 'triangle', 0.22);
      this.step++;
    }, ms);
  },
  stop() { clearInterval(this.timer); this.track = null; },
  toggleMute() {
    this.muted = !this.muted;
    if (this.gain) this.gain.gain.value = this.muted ? 0 : 0.16;
    return this.muted;
  }
};

/* ------------------------------------------------------------ utilities -- */
const rnd = (a, b) => a + Math.random() * (b - a);
const rndInt = (a, b) => Math.floor(rnd(a, b + 1));
const pick = arr => arr[Math.floor(Math.random() * arr.length)];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;

/* ============================================================== game data */

const SPELLS = {
  fire:  { name: 'Fire',   mp: 4,  power: 22, kind: 'attack', element: 'fire',  target: 'enemy', fx: 'fire' },
  ice:   { name: 'Blizzard', mp: 4, power: 20, kind: 'attack', element: 'ice',  target: 'enemy', fx: 'ice' },
  bolt:  { name: 'Thunder', mp: 6, power: 28, kind: 'attack', element: 'bolt',  target: 'enemy', fx: 'bolt' },
  flare: { name: 'Flare',  mp: 18, power: 62, kind: 'attack', element: null,    target: 'enemy', fx: 'flare' },
  quake: { name: 'Quake',  mp: 14, power: 30, kind: 'attack', element: 'earth', target: 'enemies', fx: 'quake' },
  cure:  { name: 'Cure',   mp: 4,  power: 46, kind: 'heal',   target: 'ally',   fx: 'heal' },
  cura:  { name: 'Cura',   mp: 10, power: 110, kind: 'heal',  target: 'ally',   fx: 'heal' },
  vigil: { name: 'Vigil',  mp: 8,  power: 40, kind: 'healAll', target: 'allies', fx: 'heal' },
  life:  { name: 'Raise',  mp: 16, power: 0.5, kind: 'revive', target: 'ally',  fx: 'holy' },
  holy:  { name: 'Radiance', mp: 20, power: 58, kind: 'attack', element: 'holy', target: 'enemy', fx: 'holy' }
};

const ITEMS = {
  potion:  { name: 'Potion',   icon: 'i_potion',  price: 40,  kind: 'heal',   power: 70,  desc: 'Restores 70 HP.' },
  hipotion:{ name: 'Hi-Potion',icon: 'i_potion',  price: 150, kind: 'heal',   power: 250, desc: 'Restores 250 HP.' },
  ether:   { name: 'Ether',    icon: 'i_ether',   price: 200, kind: 'mp',     power: 40,  desc: 'Restores 40 MP.' },
  phoenix: { name: 'Phoenix Down', icon: 'i_phoenix', price: 260, kind: 'revive', power: 0.4, desc: 'Revives a fallen ally.' },
  bomb:    { name: 'Fire Bomb', icon: 'i_phoenix', price: 120, kind: 'damage', power: 90, desc: 'Hurls fire at one foe.' }
};

/* Growth is flat per level and deliberately readable; no hidden curves. */
const CLASSES = {
  aldric: {
    name: 'Aldric', title: 'Knight', sprite: 'aldric',
    base: { hp: 130, mp: 0, atk: 16, def: 12, mag: 4, spd: 9 },
    grow: { hp: 22, mp: 0, atk: 3.1, def: 2.4, mag: 0.5, spd: 0.8 },
    spells: [], skill: null
  },
  lyra: {
    name: 'Lyra', title: 'Black Mage', sprite: 'lyra',
    base: { hp: 74, mp: 34, atk: 8, def: 6, mag: 17, spd: 11 },
    grow: { hp: 12, mp: 7, atk: 1.1, def: 1.2, mag: 3.4, spd: 1.1 },
    spells: [{ id: 'fire', lv: 1 }, { id: 'ice', lv: 1 }, { id: 'bolt', lv: 3 },
             { id: 'quake', lv: 6 }, { id: 'flare', lv: 9 }]
  },
  mira: {
    name: 'Mira', title: 'White Mage', sprite: 'mira',
    base: { hp: 88, mp: 30, atk: 9, def: 8, mag: 15, spd: 10 },
    grow: { hp: 15, mp: 6, atk: 1.3, def: 1.6, mag: 3.0, spd: 1.0 },
    spells: [{ id: 'cure', lv: 1 }, { id: 'cura', lv: 4 }, { id: 'vigil', lv: 6 },
             { id: 'life', lv: 5 }, { id: 'holy', lv: 8 }]
  }
};

const ENEMIES = {
  slime:  { name: 'Bog Slime', sprite: 'e_slime', hp: 34, atk: 10, def: 6, mag: 4, spd: 5, exp: 8, gil: 7,
            weak: 'bolt', ai: [{ w: 100, act: 'attack' }] },
  bat:    { name: 'Cave Bat', sprite: 'e_bat', hp: 26, atk: 12, def: 4, mag: 5, spd: 15, exp: 9, gil: 9,
            weak: 'fire', ai: [{ w: 80, act: 'attack' }, { w: 20, act: 'drain' }] },
  goblin: { name: 'Goblin', sprite: 'e_goblin', hp: 52, atk: 15, def: 9, mag: 4, spd: 9, exp: 14, gil: 16,
            ai: [{ w: 85, act: 'attack' }, { w: 15, act: 'rally' }] },
  wolf:   { name: 'Direwolf', sprite: 'e_wolf', hp: 68, atk: 19, def: 10, mag: 4, spd: 14, exp: 20, gil: 18,
            weak: 'fire', ai: [{ w: 70, act: 'attack' }, { w: 30, act: 'pounce' }] },
  wisp:   { name: 'Marsh Wisp', sprite: 'e_wisp', hp: 58, atk: 11, def: 8, mag: 18, spd: 12, exp: 22, gil: 24,
            weak: 'holy', ai: [{ w: 45, act: 'attack' }, { w: 55, act: 'spell', spell: 'fire' }] },
  bandit: { name: 'Road Bandit', sprite: 'e_bandit', hp: 92, atk: 22, def: 12, mag: 6, spd: 12, exp: 30, gil: 45,
            ai: [{ w: 70, act: 'attack' }, { w: 30, act: 'steal' }] },
  ogre:   { name: 'Ogre Chieftain', sprite: 'e_ogre', boss: true, hp: 520, atk: 30, def: 16, mag: 12, spd: 10,
            exp: 260, gil: 500, weak: 'ice',
            ai: [{ w: 55, act: 'attack' }, { w: 25, act: 'smash' }, { w: 20, act: 'spell', spell: 'quake' }] }
};

/* Encounter tables are weighted; deeper in the wilds means nastier company. */
const ENCOUNTERS = [
  { w: 26, group: ['slime'] },
  { w: 20, group: ['bat', 'bat'] },
  { w: 18, group: ['goblin'] },
  { w: 14, group: ['slime', 'slime', 'bat'] },
  { w: 12, group: ['wolf'] },
  { w: 10, group: ['goblin', 'goblin'] },
  { w: 8,  group: ['wisp'] },
  { w: 7,  group: ['wolf', 'goblin'] },
  { w: 5,  group: ['bandit'] },
  { w: 4,  group: ['wisp', 'bat', 'bat'] }
];

/* ----------------------------------------------------------------- NPCs -- */
const NPCS = {
  town: [
    { x: 20, y: 17, sprite: 'elder', dir: 'down', name: 'Elder Halvard', wander: false,
      lines: ["Rivenbrook has stood a hundred years, {name}.",
              "But something stirs in the Thornwilds. A chieftain, the scouts say.",
              "Take the south gate. And take care."] },
    { x: 16, y: 21, sprite: 'villager', dir: 'right', name: 'Gardener Pell', wander: true,
      lines: ["These beds were carrots last spring.",
              "Now? Weeds and worry. Nothing grows with monsters at the fence."] },
    { x: 24, y: 14, sprite: 'child', dir: 'left', name: 'Tam', wander: true,
      lines: ["I saw a wolf as big as a cart!", "Mum says I made it up. I did not."] },
    { x: 19, y: 26, sprite: 'guard', dir: 'down', name: 'Gate Guard', wander: false,
      lines: ["Beyond the gate is the Thornwilds. Fight or flee, but never dawdle.",
              "Press {menu} any time to open your journal."] },
    { x: 21, y: 26, sprite: 'guard', dir: 'down', name: 'Gate Guard', wander: false,
      lines: ["The Amber Lantern keeps a bed and a stocked shelf.",
              "Rest before you go. Only a fool walks the wilds tired."] },
    { x: 9, y: 12, sprite: 'villager', dir: 'down', name: 'Smith Orla', wander: true,
      lines: ["Steel I can give you. Courage you bring yourself.",
              "Lyra's fire and Mira's mercy - that's a party worth its salt."] },
    { x: 33, y: 16, sprite: 'merchant', dir: 'left', name: 'Pedlar Voss', wander: true,
      lines: ["Buying? The inn keeps my stock these days.",
              "Too many bandits on the south road for an honest cart."] }
  ],
  inn: [
    { x: 4, y: 4, sprite: 'merchant', dir: 'down', name: 'Innkeeper Bryn', wander: false, service: 'inn',
      lines: ["Welcome to the Amber Lantern."] },
    { x: 6, y: 6, sprite: 'villager', dir: 'down', name: 'Quartermaster', wander: false, service: 'shop',
      lines: ["Potions, ethers, and a bomb or two."] },
    { x: 12, y: 9, sprite: 'child', dir: 'left', name: 'Nib', wander: true,
      lines: ["If you press {cancel} you can run! Grown-ups always forget."] }
  ],
  wild: []
};

const SHOP_STOCK = ['potion', 'hipotion', 'ether', 'phoenix', 'bomb'];

/* --------------------------------------------------------- tile legend -- */
/* char -> [sprite, solid, tag] */
const LEGEND = {
  '.': ['t_grass', 0], 'F': ['t_plank', 0], ',': ['t_grass2', 0], '*': ['t_flowers', 0], '"': ['t_tallgrass', 0],
  '-': ['t_path', 0], '=': ['t_cobble', 0], 'x': ['t_sand', 0],
  'B': ['t_bridge', 0], 'D': ['t_door', 0, 'door'],
  '~': ['t_water0', 1, 'water'], 'T': ['t_tree', 1], 'b': ['t_bush', 1], 'r': ['t_rock', 1],
  'K': ['t_counter', 1], 'A': ['t_barrel', 1], 'H': ['t_shelf', 1],
  '1': ['t_bedtop', 1, 'bed'], '2': ['t_bedbot', 1, 'bed'], 'U': ['t_rug', 0],
  'M': ['t_mountain', 1], 'W': ['t_wall', 1], 'R': ['t_roof', 1], '^': ['t_rooftop', 1],
  'G': ['t_window', 1], 'f': ['t_fence', 1], 's': ['t_sign', 1, 'sign'],
  'o': ['t_well', 1, 'well'], 'c': ['t_chest', 1, 'chest'], 'l': ['t_lamp', 1, 'lamp']
};
/* What sits under a prop, so props never float on a void. 'ground' resolves
   to each map's own ground tile (grass outdoors, floorboards indoors). */
const UNDERLAY = {
  'T': 'ground', 'b': 'ground', 'r': 'ground', 'f': 'ground', 's': 'ground',
  'c': 'ground', 'A': 'ground', 'l': 't_cobble', 'o': 't_cobble', 'B': 't_water0',
  '1': 'ground', '2': 'ground', 'U': 'ground'
};

const SIGN_TEXT = {
  town: 'RIVENBROOK - The Amber Lantern, rooms and remedies.',
  wild: 'THORNWILDS SHRINE - Turn back. The chieftain does not sleep.'
};

const CHEST_LOOT = {
  'town:4,5': { item: 'potion', n: 2 },
  'town:35,24': { item: 'ether', n: 1 },
  'inn:11,2': { gil: 120 },
  'wild:43,39': { item: 'hipotion', n: 2 }
};

/* ============================================================ party model */

function expToNext(lv) { return Math.floor(22 * Math.pow(lv, 1.75)); }

function statAt(cls, key, lv) {
  return Math.floor(cls.base[key] + cls.grow[key] * (lv - 1));
}

function makeHero(id, lv) {
  const cls = CLASSES[id];
  lv = lv || 1;
  const h = {
    id, name: cls.name, title: cls.title, sprite: cls.sprite,
    lv, exp: 0, alive: true, defending: false, atb: 0
  };
  refreshStats(h);
  h.hp = h.maxhp; h.mp = h.maxmp;
  return h;
}

function refreshStats(h) {
  const cls = CLASSES[h.id];
  h.maxhp = statAt(cls, 'hp', h.lv);
  h.maxmp = statAt(cls, 'mp', h.lv);
  h.atk = statAt(cls, 'atk', h.lv);
  h.def = statAt(cls, 'def', h.lv);
  h.mag = statAt(cls, 'mag', h.lv);
  h.spd = statAt(cls, 'spd', h.lv);
  h.spells = cls.spells.filter(s => s.lv <= h.lv).map(s => s.id);
}

function grantExp(h, amount) {
  if (!h.alive) return [];
  const gained = [];
  h.exp += amount;
  while (h.exp >= expToNext(h.lv)) {
    h.exp -= expToNext(h.lv);
    h.lv++;
    const before = { hp: h.maxhp, mp: h.maxmp, spells: h.spells.slice() };
    refreshStats(h);
    h.hp += h.maxhp - before.hp;
    h.mp += h.maxmp - before.mp;
    const learned = h.spells.filter(s => before.spells.indexOf(s) < 0);
    gained.push({ lv: h.lv, learned });
  }
  return gained;
}

/* ============================================================= game state */

const G = {
  mode: 'title',
  party: [], gil: 200, bag: {},
  mapId: 'town', px: 0, py: 0, dir: 'down',
  steps: 0, stepsToEncounter: 0, playtime: 0,
  flags: { chests: {}, bossDown: false, visitedWild: false },
  fade: 0, fadeDir: 0, fadeThen: null
};

function newGame() {
  G.party = [makeHero('aldric'), makeHero('lyra'), makeHero('mira')];
  G.gil = 200;
  G.bag = { potion: 5, ether: 1, phoenix: 1 };
  G.flags = { chests: {}, bossDown: false, visitedWild: false };
  G.steps = 0; G.playtime = 0;
  enterMap('town', MAPS.town.spawn[0], MAPS.town.spawn[1], 'down');
}

const SAVE_KEY = 'rivenbrook.save.v1';
function saveGame() {
  const data = {
    party: G.party.map(h => ({ id: h.id, lv: h.lv, exp: h.exp, hp: h.hp, mp: h.mp, alive: h.alive })),
    gil: G.gil, bag: G.bag, mapId: G.mapId, px: G.px, py: G.py, dir: G.dir,
    flags: G.flags, playtime: G.playtime
  };
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(data)); return true; }
  catch (e) { return false; }
}
function hasSave() {
  try { return !!localStorage.getItem(SAVE_KEY); } catch (e) { return false; }
}
function loadGame() {
  try {
    const d = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (!d) return false;
    G.party = d.party.map(p => {
      const h = makeHero(p.id, p.lv);
      h.exp = p.exp; h.hp = p.hp; h.mp = p.mp; h.alive = p.alive !== false;
      return h;
    });
    G.gil = d.gil; G.bag = d.bag || {}; G.flags = d.flags || { chests: {} };
    G.playtime = d.playtime || 0;
    enterMap(d.mapId, d.px, d.py, d.dir);
    return true;
  } catch (e) { return false; }
}

/* =================================================================== field */

const Field = {
  map: null, npcs: [], anim: 0, moving: null, walkPhase: 0,
  msg: null, chestGlow: 0
};

function enterMap(id, tx, ty, dir) {
  Field.map = MAPS[id];
  G.mapId = id;
  G.px = tx; G.py = ty; G.dir = dir || G.dir;
  Field.moving = null;
  Field.msg = null;
  Field.walkPhase = 0;
  Field.npcs = (NPCS[id] || []).map(n => {
    const spot = nearestFree(n.x, n.y);
    return Object.assign({
      tx: spot[0], ty: spot[1], ox: 0, oy: 0, phase: 0, cool: rnd(1, 4), move: null
    }, n);
  });
  if (id === 'wild' && !G.flags.bossDown && Field.map.boss) {
    Field.npcs.push({
      boss: true, tx: Field.map.boss.x, ty: Field.map.boss.y, ox: 0, oy: 0,
      sprite: 'e_ogre', dir: 'down', name: 'Ogre Chieftain', phase: 0, cool: 99, move: null,
      lines: ['A shape rises from the shrine stones...']
    });
  }
  G.stepsToEncounter = rollEncounterCountdown();
  Audio_.play(Field.map.music === 'town' ? 'town' : Field.map.music === 'inn' ? 'inn' : 'field');
}

/* Scenery is scattered procedurally, so an NPC's authored tile can end up
   under a tree. Walk outwards until we find somewhere it can actually stand. */
function nearestFree(x, y) {
  if (!solidAt(x, y)) return [x, y];
  for (let r = 1; r <= 5; r++) {
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        if (Math.abs(dx) !== r && Math.abs(dy) !== r) continue;
        if (!solidAt(x + dx, y + dy)) return [x + dx, y + dy];
      }
    }
  }
  return [x, y];
}

function rollEncounterCountdown() {
  const e = Field.map ? Field.map.encounter : 0;
  return e ? rndInt(Math.floor(e * 0.5), Math.floor(e * 1.6)) : Infinity;
}

function tileAt(x, y) {
  const m = Field.map;
  if (x < 0 || y < 0 || x >= m.w || y >= m.h) return null;
  return m.rows[y][x];
}

function solidAt(x, y) {
  const ch = tileAt(x, y);
  if (ch === null) return true;
  const def = LEGEND[ch];
  if (!def) return true;
  if (def[1]) return true;
  return false;
}

function npcAt(x, y) {
  return Field.npcs.find(n => n.tx === x && n.ty === y) || null;
}

function warpAt(x, y) {
  return (Field.map.warps || []).find(w => w.x === x && w.y === y) || null;
}

const DIRV = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
const GRASS_VARIANTS = ['t_grass', 't_grass3', 't_grass2'];

function tryStep(dir) {
  const [dx, dy] = DIRV[dir];
  const nx = G.px + dx, ny = G.py + dy;
  G.dir = dir;
  if (solidAt(nx, ny) || npcAt(nx, ny)) return false;
  Field.moving = { fx: G.px, fy: G.py, tx: nx, ty: ny, t: 0, dur: 0.155 };
  return true;
}

function onStepComplete() {
  G.steps++;
  const w = warpAt(G.px, G.py);
  if (w) { doWarp(w); return; }
  // Step within reach of the chieftain and it stirs - but you get one last
  // chance to back away, because this fight cannot be fled.
  const boss = Field.npcs.find(n => n.boss &&
    Math.abs(n.tx - G.px) + Math.abs(n.ty - G.py) <= 1);
  if (boss) { challengeBoss(); return; }
  if (Field.map.encounter) {
    G.stepsToEncounter--;
    if (G.stepsToEncounter <= 0) {
      G.stepsToEncounter = rollEncounterCountdown();
      startEncounter(pickEncounter());
    }
  }
}

function doWarp(w) {
  fadeTo(() => {
    enterMap(w.to, w.tx, w.ty, w.dir || G.dir);
    if (w.to === 'wild' && !G.flags.visitedWild) {
      G.flags.visitedWild = true;
      Field.msg = makeMessage([
        'THE THORNWILDS',
        'Monsters roam the grass. Press ' + keyName('menu') + ' for your journal.'
      ]);
    }
  });
}

function pickEncounter() {
  const total = ENCOUNTERS.reduce((a, e) => a + e.w, 0);
  let r = Math.random() * total;
  for (const e of ENCOUNTERS) { r -= e.w; if (r <= 0) return e.group.slice(); }
  return ['slime'];
}

function keyName(action) {
  return { confirm: '[Z]', cancel: '[X]', menu: '[C]' }[action] || '';
}

function makeMessage(lines, opts) {
  return Object.assign({
    lines: lines.slice(), page: 0, chars: 0, done: false, speaker: null
  }, opts || {});
}

function interact() {
  const [dx, dy] = DIRV[G.dir];
  const tx = G.px + dx, ty = G.py + dy;
  const npc = npcAt(tx, ty);
  if (npc) {
    if (npc.boss) { challengeBoss(); return; }
    npc.dir = { up: 'down', down: 'up', left: 'right', right: 'left' }[G.dir];
    npc.cool = 3;
    if (npc.service === 'inn') { openInn(npc); return; }
    if (npc.service === 'shop') { openShop(npc); return; }
    Field.msg = makeMessage(npc.lines.map(fillTokens), { speaker: npc.name });
    Audio_.sfx('confirm');
    return;
  }
  const ch = tileAt(tx, ty);
  const def = LEGEND[ch];
  const tag = def && def[2];
  if (tag === 'sign') {
    Field.msg = makeMessage([SIGN_TEXT[G.mapId] || 'The paint has weathered away.']);
  } else if (tag === 'chest') {
    openChest(tx, ty);
  } else if (tag === 'well') {
    Field.msg = makeMessage(['The well is cold and deep. Coins glint at the bottom.']);
  } else if (tag === 'bed') {
    Field.msg = makeMessage(['A made bed with a wool blanket. Speak to the innkeeper to rest.']);
  } else if (tag === 'lamp') {
    Field.msg = makeMessage(['A lantern burns low against the dark.']);
  } else if (tag === 'water' || ch === '~') {
    Field.msg = makeMessage(['Clear water. Too deep to wade.']);
  }
  if (Field.msg) Audio_.sfx('confirm');
}

function challengeBoss() {
  Audio_.sfx('cancel');
  Field.msg = makeMessage([
    'The Ogre Chieftain hauls itself off the shrine stones.',
    'There will be no fleeing from this one. Stand and fight?'
  ], {
    speaker: 'Ogre Chieftain',
    choice: {
      options: ['Fight', 'Back away'], index: 0,
      onPick: idx => {
        if (idx === 0) { Audio_.sfx('encounter'); startEncounter(['ogre'], true); }
        else { G.py = clamp(G.py - 2, 0, Field.map.h - 1); G.dir = 'up'; }
      }
    }
  });
}

function fillTokens(line) {
  return line.replace('{name}', G.party[0].name)
    .replace('{menu}', keyName('menu'))
    .replace('{cancel}', keyName('cancel'))
    .replace('{confirm}', keyName('confirm'));
}

function openChest(tx, ty) {
  const key = G.mapId + ':' + tx + ',' + ty;
  if (G.flags.chests[key]) {
    Field.msg = makeMessage(['The chest is empty.']);
    return;
  }
  G.flags.chests[key] = true;
  const loot = CHEST_LOOT[key] || { gil: 50 };
  let line;
  if (loot.gil) { G.gil += loot.gil; line = 'Found ' + loot.gil + ' gil!'; }
  else {
    G.bag[loot.item] = (G.bag[loot.item] || 0) + loot.n;
    line = 'Found ' + ITEMS[loot.item].name + ' x' + loot.n + '!';
  }
  Audio_.sfx('item');
  Field.msg = makeMessage([line]);
}

function updateField(dt) {
  Field.anim += dt;
  G.playtime += dt;

  if (Field.msg) { updateMessage(dt); return; }

  if (Input.tap('menu')) { openMenu(); return; }
  if (Input.tap('confirm')) { interact(); return; }

  if (Field.moving) {
    const m = Field.moving;
    m.t += dt;
    Field.walkPhase += dt * (Input.held('cancel') ? 11 : 7);
    if (m.t >= m.dur) {
      G.px = m.tx; G.py = m.ty;
      Field.moving = null;
      onStepComplete();
      return;
    }
  } else {
    const speedMul = Input.held('cancel') ? 0.62 : 1;  // hold cancel to dash
    let dir = null;
    if (Input.held('up')) dir = 'up';
    else if (Input.held('down')) dir = 'down';
    else if (Input.held('left')) dir = 'left';
    else if (Input.held('right')) dir = 'right';
    if (dir) {
      const moved = tryStep(dir);
      if (moved) Field.moving.dur *= speedMul;
      else Field.walkPhase += dt * 5;
    } else {
      Field.walkPhase = 0;
    }
  }
  updateNpcs(dt);
}

function updateNpcs(dt) {
  for (const n of Field.npcs) {
    if (n.move) {
      n.move.t += dt;
      const k = Math.min(1, n.move.t / n.move.dur);
      n.ox = lerp(n.move.fx - n.tx, 0, k);
      n.oy = lerp(n.move.fy - n.ty, 0, k);
      n.phase += dt * 6;
      if (k >= 1) { n.move = null; n.ox = 0; n.oy = 0; n.phase = 0; }
      continue;
    }
    if (!n.wander) continue;
    n.cool -= dt;
    if (n.cool > 0) continue;
    n.cool = rnd(1.4, 4.5);
    const dir = pick(['up', 'down', 'left', 'right']);
    const [dx, dy] = DIRV[dir];
    const nx = n.tx + dx, ny = n.ty + dy;
    n.dir = dir;
    if (solidAt(nx, ny) || npcAt(nx, ny) || (nx === G.px && ny === G.py)) continue;
    n.move = { fx: n.tx, fy: n.ty, t: 0, dur: 0.28 };
    n.tx = nx; n.ty = ny;
    n.ox = dx * -1; n.oy = dy * -1;
  }
}

function updateMessage(dt) {
  const m = Field.msg;
  const line = m.lines[m.page] || '';
  if (m.chars < line.length) {
    m.chars += dt * 90;
    if (Input.tap('confirm')) m.chars = line.length;
    return;
  }
  // A choice waits on the final page instead of closing the box.
  if (m.choice && m.page === m.lines.length - 1) {
    const c = m.choice;
    if (Input.nav('up', dt)) { c.index = (c.index + c.options.length - 1) % c.options.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { c.index = (c.index + 1) % c.options.length; Audio_.sfx('cursor'); }
    if (Input.tap('cancel')) { Audio_.sfx('cancel'); Field.msg = null; c.onPick(c.options.length - 1); return; }
    if (Input.tap('confirm')) { Audio_.sfx('confirm'); Field.msg = null; c.onPick(c.index); }
    return;
  }
  if (Input.tap('confirm') || Input.tap('cancel')) {
    m.page++;
    m.chars = 0;
    if (m.page >= m.lines.length) {
      const after = m.onClose;
      Field.msg = null;
      if (after) after();
    } else Audio_.sfx('cursor');
  }
}

/* ------------------------------------------------------------ field draw */

function cameraFor(px, py, ox, oy) {
  const m = Field.map;
  let cx = (px + ox) * TILE + TILE / 2 - VW / 2;
  let cy = (py + oy) * TILE + TILE / 2 - VH / 2;
  cx = clamp(cx, 0, Math.max(0, m.w * TILE - VW));
  cy = clamp(cy, 0, Math.max(0, m.h * TILE - VH));
  return [Math.round(cx), Math.round(cy)];
}

function playerOffset() {
  if (!Field.moving) return [0, 0];
  const m = Field.moving;
  const k = Math.min(1, m.t / m.dur);
  return [lerp(m.fx - m.tx, 0, k) + (m.tx - G.px), lerp(m.fy - m.ty, 0, k) + (m.ty - G.py)];
}

function walkFrame(phase) {
  const f = Math.floor(phase) % 4;
  return f === 1 ? 1 : f === 3 ? 2 : 0;
}

function drawField() {
  const m = Field.map;
  const [pox, poy] = playerOffset();
  const [camX, camY] = cameraFor(G.px, G.py, pox, poy);
  const waterFrame = Math.floor(Field.anim * 3) % 2;

  ctx.fillStyle = '#12101c';
  ctx.fillRect(0, 0, VW, VH);

  const x0 = Math.floor(camX / TILE), y0 = Math.floor(camY / TILE);
  const x1 = Math.ceil((camX + VW) / TILE), y1 = Math.ceil((camY + VH) / TILE);
  for (let y = y0; y <= y1; y++) {
    for (let x = x0; x <= x1; x++) {
      const ch = tileAt(x, y);
      if (ch === null) continue;
      const def = LEGEND[ch];
      if (!def) continue;
      const sx = x * TILE - camX, sy = y * TILE - camY;
      let under = UNDERLAY[ch];
      if (under === 'ground') under = m.ground || 't_grass';
      if (under) spr(under === 't_water0' ? 't_water' + waterFrame : under, sx, sy);
      let name = def[0];
      if (name === 't_water0') name = 't_water' + waterFrame;
      // Rotate through grass variants so open fields do not visibly tile.
      else if (name === 't_grass') name = GRASS_VARIANTS[(x * 7 + y * 13) % 3];
      spr(name, sx, sy);
    }
  }

  // Entities, sorted so southern sprites overlap northern ones.
  const ents = [];
  for (const n of Field.npcs) {
    ents.push({
      y: n.ty + n.oy, draw: () => {
        const sx = (n.tx + n.ox) * TILE - camX;
        const sy = (n.ty + n.oy) * TILE - camY;
        if (n.boss) {
          drawShadow(sx + 8, sy + 16, 11);
          const [w, h] = sprSize('e_ogre');
          spr('e_ogre', sx + 8 - w / 2, sy + 16 - h);
        } else {
          drawShadow(sx + 8, sy + 15, 6);
          spr(n.sprite + '_' + n.dir + walkFrame(n.phase), sx, sy - 8);
        }
      }
    });
  }
  ents.push({
    y: G.py + poy, draw: () => {
      const sx = (G.px + pox) * TILE - camX;
      const sy = (G.py + poy) * TILE - camY;
      drawShadow(sx + 8, sy + 15, 6);
      spr('aldric_' + G.dir + walkFrame(Field.walkPhase), sx, sy - 8);
    }
  });
  ents.sort((a, b) => a.y - b.y);
  ents.forEach(e => e.draw());

  drawLocationBanner();
  if (Field.msg) drawMessageBox(Field.msg);
}

function drawShadow(cx, cy, r) {
  ctx.fillStyle = 'rgba(10,8,20,0.32)';
  ctx.beginPath();
  ctx.ellipse(Math.round(cx), Math.round(cy), r, Math.round(r * 0.45), 0, 0, Math.PI * 2);
  ctx.fill();
}

let bannerTimer = 0, bannerName = '';
function drawLocationBanner() {
  if (bannerName !== Field.map.name) { bannerName = Field.map.name; bannerTimer = 2.6; }
  if (bannerTimer <= 0) return;
  const a = Math.min(1, bannerTimer);
  ctx.save();
  ctx.globalAlpha = a;
  const w = textWidth(Field.map.name) + 20;
  drawWindow(VW - w - 6, 6, w, 18, { tone: 'dark' });
  drawText(Field.map.name, VW - w / 2 - 6, 11, '#f6e2a8', { align: 'center' });
  ctx.restore();
}

function drawMessageBox(m) {
  const boxH = 42;
  const y = VH - boxH - 6;
  drawWindow(6, y, VW - 12, boxH);
  if (m.speaker) {
    const nw = textWidth(m.speaker) + 12;
    drawWindow(10, y - 9, nw, 15, { tone: 'dark' });
    drawText(m.speaker, 16, y - 5, '#f6e2a8');
  }
  const full = m.lines[m.page] || '';
  const shown = full.slice(0, Math.floor(m.chars));
  wrapText(shown, 47).slice(0, 2).forEach((ln, i) => drawText(ln, 16, y + 11 + i * 12, '#f2f4ff'));
  if (m.choice && m.page === m.lines.length - 1 && m.chars >= full.length) {
    const c = m.choice;
    const w = Math.max.apply(null, c.options.map(textWidth)) + 26;
    const h = 8 + c.options.length * 13;
    const cx = VW - w - 12, cy = y - h - 4;
    drawWindow(cx, cy, w, h, { tone: 'dark' });
    c.options.forEach((o, i) => {
      const oy = cy + 5 + i * 13;
      drawText(o, cx + 18, oy, i === c.index ? '#ffe9a0' : '#f2f4ff');
      if (i === c.index) drawCursor(cx + 6, oy - 1, Field.anim);
    });
    return;
  }
  if (m.chars >= full.length) {
    const bob = Math.sin(Field.anim * 7) > 0 ? 0 : 1;
    ctx.fillStyle = '#f4e08a';
    for (let i = 0; i < 4; i++) ctx.fillRect(VW - 26 + i, y + boxH - 12 + bob + i, 8 - i * 2, 1);
  }
}

/* ================================================================= battle */
/* Wait-mode ATB, the way FF4 plays with Battle Speed on the patient side:
   gauges fill in real time, and freeze while a command window is open. */

const ATB_RATE = 5.2;

const Battle = {
  on: false, phase: 'intro', t: 0, intro: 0,
  enemies: [], boss: false, escapable: true,
  actor: null, pending: [], acting: null,
  cmd: 0, sub: null, subIndex: 0, subScroll: 0, targetSide: 'enemy', target: 0,
  banner: '', bannerT: 0, popups: [], fx: [], shake: 0,
  rewards: null, resultLines: [], resultPage: 0, flash: 0
};

function startEncounter(group, isBoss) {
  Audio_.sfx('encounter');
  Battle.flash = 1;
  fadeTo(() => {
    Battle.on = true;
    Battle.phase = 'intro';
    Battle.intro = 0.6;
    Battle.t = 0;
    Battle.boss = !!isBoss;
    Battle.escapable = !isBoss;
    Battle.popups = []; Battle.fx = []; Battle.shake = 0;
    Battle.actor = null; Battle.acting = null; Battle.pending = [];
    Battle.cmd = 0; Battle.sub = null; Battle.subIndex = 0;
    Battle.banner = isBoss ? 'The Ogre Chieftain blocks your path!' : 'Monsters appear!';
    Battle.bannerT = 2.2;
    const counts = {};
    Battle.enemies = group.map((id, i) => {
      const base = ENEMIES[id];
      counts[id] = (counts[id] || 0) + 1;
      const e = Object.assign({}, base, {
        id, key: id + i, maxhp: base.hp, hp: base.hp, alive: true,
        atb: rnd(0, 30), hurt: 0, dying: 0, offset: 0, index: i,
        label: base.name + (group.filter(g => g === id).length > 1 ? ' ' + String.fromCharCode(64 + counts[id]) : '')
      });
      return e;
    });
    G.party.forEach(h => { h.atb = h.alive ? rnd(0, 45) : 0; h.defending = false; h.hurt = 0; h.offset = 0; });
    G.mode = 'battle';
    Audio_.play('battle');
  });
}

function livingEnemies() { return Battle.enemies.filter(e => e.alive); }
function livingHeroes() { return G.party.filter(h => h.alive); }

/* The party stands in a receding diagonal, the way the 16-bit games framed
   it: each member a little nearer and a little lower than the last. */
function heroSlot(i) { return { x: 266 - i * 18, y: 46 + i * 15 }; }
/* Enemies are baseline-anchored so tall and short monsters share a ground
   line and none of them dips behind the HUD. */
function enemySlot(e, i, n) {
  const [w, h] = sprSize(e.sprite);
  const cols = Math.min(3, n);
  const col = i % cols, row = Math.floor(i / cols);
  const baseY = 92 + col * 8 - row * 20;
  return { x: 24 + col * 48 + row * 20, y: baseY - h * 2, w: w * 2, h: h * 2, baseY };
}

/* ------------------------------------------------------------ mechanics -- */

function physDamage(attacker, target, mult) {
  const atk = attacker.atk * (mult || 1);
  const def = target.def * (target.defending ? 1.9 : 1);
  let dmg = Math.max(1, Math.round((atk * 2.2 - def * 1.1) * rnd(0.9, 1.12)));
  let crit = false;
  if (Math.random() < 0.07) { dmg = Math.round(dmg * 1.9); crit = true; }
  return { dmg, crit };
}

function magicDamage(caster, target, spell) {
  let dmg = Math.round((caster.mag * 1.6 + spell.power) * rnd(0.92, 1.1));
  const weak = target.weak && spell.element === target.weak;
  if (weak) dmg = Math.round(dmg * 1.6);
  dmg = Math.max(1, dmg - Math.round(target.def * 0.35));
  return { dmg, weak };
}

function popup(text, x, y, color) {
  Battle.popups.push({ text, x, y, color: color || '#ffffff', t: 0, life: 1.05 });
}

function addFx(kind, x, y, opts) {
  Battle.fx.push(Object.assign({ kind, x, y, t: 0, life: 0.55 }, opts || {}));
}

function applyDamage(target, dmg, isHero, opts) {
  opts = opts || {};
  target.hp = Math.max(0, target.hp - dmg);
  target.hurt = 0.28;
  const slot = isHero ? heroSlot(G.party.indexOf(target)) : null;
  const pos = isHero ? { x: slot.x + 8, y: slot.y } : enemyCenter(target);
  popup((opts.crit ? '' : '') + dmg, pos.x, pos.y - 6,
    opts.crit ? '#ffd75a' : opts.weak ? '#8fe8ff' : '#ffffff');
  if (opts.crit) popup('CRITICAL', pos.x, pos.y - 18, '#ffd75a');
  else if (opts.weak) popup('WEAK', pos.x, pos.y - 18, '#8fe8ff');
  Battle.shake = Math.max(Battle.shake, opts.crit ? 5 : 3);
  if (target.hp <= 0) {
    target.alive = false;
    if (!isHero) target.dying = 0.6;
    else target.atb = 0;
    Audio_.sfx('ko');
  }
}

function healTarget(target, amount, isHero) {
  const before = target.hp;
  target.hp = Math.min(target.maxhp, target.hp + amount);
  const slot = isHero ? heroSlot(G.party.indexOf(target)) : null;
  const pos = isHero ? { x: slot.x + 8, y: slot.y } : enemyCenter(target);
  popup('+' + (target.hp - before), pos.x, pos.y - 6, '#8fffa8');
}

function enemyCenter(e) {
  const alive = Battle.enemies;
  const i = alive.indexOf(e);
  const s = enemySlot(e, i, alive.length);
  return { x: s.x + s.w / 2, y: s.y };
}

/* --------------------------------------------------------------- update -- */

function updateBattle(dt) {
  Battle.t += dt;
  G.playtime += dt;
  Battle.bannerT = Math.max(0, Battle.bannerT - dt);
  Battle.shake = Math.max(0, Battle.shake - dt * 22);
  Battle.flash = Math.max(0, Battle.flash - dt * 2.2);

  Battle.popups = Battle.popups.filter(p => (p.t += dt) < p.life);
  Battle.fx = Battle.fx.filter(f => (f.t += dt) < f.life);
  Battle.enemies.forEach(e => {
    e.hurt = Math.max(0, e.hurt - dt);
    if (e.dying > 0) e.dying = Math.max(0, e.dying - dt);
    e.offset = lerp(e.offset, 0, Math.min(1, dt * 8));
  });
  G.party.forEach(h => {
    h.hurt = Math.max(0, h.hurt - dt);
    h.offset = lerp(h.offset, 0, Math.min(1, dt * 8));
  });

  switch (Battle.phase) {
    case 'intro':
      Battle.intro -= dt;
      if (Battle.intro <= 0) Battle.phase = 'active';
      break;
    case 'active': updateAtb(dt); break;
    case 'command': updateCommand(dt); break;
    case 'target': updateTargeting(dt); break;
    case 'action': updateAction(dt); break;
    case 'result': updateResult(dt); break;
  }
}

function updateAtb(dt) {
  if (!livingEnemies().length) { beginVictory(); return; }
  if (!livingHeroes().length) { beginDefeat(); return; }

  for (const h of G.party) {
    if (!h.alive) continue;
    h.atb = Math.min(100, h.atb + h.spd * ATB_RATE * dt);
    if (h.atb >= 100 && Battle.pending.indexOf(h) < 0) Battle.pending.push(h);
  }
  for (const e of livingEnemies()) {
    e.atb = Math.min(100, e.atb + e.spd * ATB_RATE * dt);
    if (e.atb >= 100) { e.atb = 0; beginEnemyAction(e); return; }
  }
  Battle.pending = Battle.pending.filter(h => h.alive);
  if (Battle.pending.length) {
    Battle.actor = Battle.pending[0];
    Battle.actor.defending = false;
    Battle.cmd = 0; Battle.sub = null; Battle.subIndex = 0; Battle.subScroll = 0;
    Battle.phase = 'command';
  }
}

function commandsFor(h) {
  const list = [{ id: 'fight', label: 'Fight' }];
  if (h.spells.length) list.push({ id: 'magic', label: 'Magic' });
  list.push({ id: 'item', label: 'Item' });
  list.push({ id: 'guard', label: 'Guard' });
  list.push({ id: 'run', label: 'Run' });
  return list;
}

function bagList() {
  return Object.keys(G.bag).filter(k => G.bag[k] > 0).map(k => ({ id: k, n: G.bag[k] }));
}

function updateCommand(dt) {
  const h = Battle.actor;
  if (Battle.sub === null) {
    const cmds = commandsFor(h);
    if (Input.nav('up', dt)) { Battle.cmd = (Battle.cmd + cmds.length - 1) % cmds.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Battle.cmd = (Battle.cmd + 1) % cmds.length; Audio_.sfx('cursor'); }
    if (Input.tap('confirm')) {
      const c = cmds[Battle.cmd].id;
      Audio_.sfx('confirm');
      if (c === 'fight') { Battle.sub = null; beginTargeting('enemy', { kind: 'fight' }); }
      else if (c === 'guard') { chooseAction({ kind: 'guard' }); }
      else if (c === 'run') { chooseAction({ kind: 'run' }); }
      else { Battle.sub = c; Battle.subIndex = 0; Battle.subScroll = 0; }
    }
    return;
  }
  const items = Battle.sub === 'magic'
    ? h.spells.map(id => ({ id, spell: SPELLS[id] }))
    : bagList();
  if (Input.tap('cancel')) { Battle.sub = null; Audio_.sfx('cancel'); return; }
  if (!items.length) { if (Input.tap('confirm')) { Battle.sub = null; Audio_.sfx('cancel'); } return; }
  if (Input.nav('up', dt)) { Battle.subIndex = (Battle.subIndex + items.length - 1) % items.length; Audio_.sfx('cursor'); }
  if (Input.nav('down', dt)) { Battle.subIndex = (Battle.subIndex + 1) % items.length; Audio_.sfx('cursor'); }
  Battle.subScroll = clamp(Battle.subScroll, Battle.subIndex - 3, Battle.subIndex);
  if (Input.tap('confirm')) {
    if (Battle.sub === 'magic') {
      const sp = SPELLS[items[Battle.subIndex].id];
      if (h.mp < sp.mp) { Audio_.sfx('cancel'); flashBanner('Not enough MP!'); return; }
      Audio_.sfx('confirm');
      const act = { kind: 'magic', spellId: items[Battle.subIndex].id };
      if (sp.target === 'enemy') beginTargeting('enemy', act);
      else if (sp.target === 'ally') beginTargeting('ally', act);
      else chooseAction(act);
    } else {
      const it = ITEMS[items[Battle.subIndex].id];
      Audio_.sfx('confirm');
      const act = { kind: 'item', itemId: items[Battle.subIndex].id };
      beginTargeting(it.kind === 'damage' ? 'enemy' : 'ally', act);
    }
  }
}

function beginTargeting(side, action) {
  Battle.targetSide = side;
  Battle.pendingAction = action;
  if (side === 'enemy') {
    const alive = Battle.enemies.filter(e => e.alive);
    Battle.target = Battle.enemies.indexOf(alive[0]);
  } else {
    Battle.target = G.party.indexOf(Battle.actor);
  }
  Battle.phase = 'target';
}

function updateTargeting(dt) {
  if (Input.tap('cancel')) { Battle.phase = 'command'; Audio_.sfx('cancel'); return; }
  const list = Battle.targetSide === 'enemy' ? Battle.enemies : G.party;
  const valid = i => Battle.targetSide === 'enemy' ? list[i].alive
    : (Battle.pendingAction.kind === 'item' && ITEMS[Battle.pendingAction.itemId].kind === 'revive') ||
      (Battle.pendingAction.kind === 'magic' && SPELLS[Battle.pendingAction.spellId].kind === 'revive')
      ? true : list[i].alive;
  const step = d => {
    for (let k = 1; k <= list.length; k++) {
      const i = (Battle.target + d * k + list.length * 2) % list.length;
      if (valid(i)) { Battle.target = i; Audio_.sfx('cursor'); return; }
    }
  };
  if (Input.nav('up', dt) || Input.nav('left', dt)) step(-1);
  if (Input.nav('down', dt) || Input.nav('right', dt)) step(1);
  if (Input.tap('confirm')) {
    Audio_.sfx('confirm');
    const act = Object.assign({}, Battle.pendingAction, { target: list[Battle.target] });
    chooseAction(act);
  }
}

function chooseAction(action) {
  const h = Battle.actor;
  Battle.pending = Battle.pending.filter(a => a !== h);
  h.atb = 0;
  Battle.acting = { who: h, isHero: true, action, t: 0, stage: 0 };
  Battle.phase = 'action';
  Battle.actor = null;
  Battle.sub = null;
}

function beginEnemyAction(e) {
  const total = e.ai.reduce((a, o) => a + o.w, 0);
  let r = Math.random() * total, choice = e.ai[0];
  for (const o of e.ai) { r -= o.w; if (r <= 0) { choice = o; break; } }
  Battle.acting = { who: e, isHero: false, action: { kind: choice.act, spellId: choice.spell }, t: 0, stage: 0 };
  Battle.phase = 'action';
}

function flashBanner(text) { Battle.banner = text; Battle.bannerT = 1.4; }

/* Actions play out in three beats: step in, resolve, step back. */
function updateAction(dt) {
  const a = Battle.acting;
  a.t += dt;
  const isHero = a.isHero;
  const dirSign = isHero ? -1 : 1;

  if (a.stage === 0) {
    a.who.offset = lerp(0, 14 * dirSign, Math.min(1, a.t / 0.18));
    if (a.t >= 0.18) { a.stage = 1; a.t = 0; resolveAction(a); }
  } else if (a.stage === 1) {
    if (a.t >= (a.hold || 0.5)) { a.stage = 2; a.t = 0; }
  } else {
    a.who.offset = lerp(14 * dirSign, 0, Math.min(1, a.t / 0.16));
    if (a.t >= 0.16) {
      a.who.offset = 0;
      Battle.acting = null;
      if (a.fled) { endBattle('fled'); return; }
      if (!livingEnemies().length) { beginVictory(); return; }
      if (!livingHeroes().length) { beginDefeat(); return; }
      Battle.phase = 'active';
    }
  }
}

function resolveAction(a) {
  const who = a.who, act = a.action;
  if (a.isHero) resolveHeroAction(a, who, act);
  else resolveEnemyAction(a, who, act);
}

function resolveHeroAction(a, h, act) {
  if (act.kind === 'guard') {
    h.defending = true;
    flashBanner(h.name + ' takes a guarded stance.');
    Audio_.sfx('cursor');
    a.hold = 0.35;
    return;
  }
  if (act.kind === 'run') {
    if (!Battle.escapable) { flashBanner('There is no escape!'); Audio_.sfx('cancel'); a.hold = 0.7; return; }
    const partySpd = livingHeroes().reduce((s, x) => s + x.spd, 0) / livingHeroes().length;
    const foeSpd = livingEnemies().reduce((s, x) => s + x.spd, 0) / livingEnemies().length;
    if (Math.random() < clamp(0.35 + (partySpd - foeSpd) * 0.06, 0.2, 0.9)) {
      flashBanner('Got away safely!');
      a.fled = true; a.hold = 0.5;
    } else { flashBanner("Couldn't escape!"); a.hold = 0.6; }
    return;
  }
  if (act.kind === 'fight') {
    let t = act.target;
    if (!t.alive) t = livingEnemies()[0];
    if (!t) return;
    const c = enemyCenter(t);
    addFx('slash', c.x, c.y);
    Audio_.sfx('hit');
    const r = physDamage(h, t);
    applyDamage(t, r.dmg, false, { crit: r.crit });
    t.offset = 6;
    flashBanner(h.name + ' attacks!');
    a.hold = 0.45;
    return;
  }
  if (act.kind === 'magic') {
    const sp = SPELLS[act.spellId];
    h.mp = Math.max(0, h.mp - sp.mp);
    flashBanner(h.name + ' casts ' + sp.name + '!');
    Audio_.sfx(sp.kind === 'heal' || sp.kind === 'healAll' || sp.kind === 'revive' ? 'heal' : 'magic');
    a.hold = 0.75;
    if (sp.kind === 'attack') {
      const targets = sp.target === 'enemies' ? livingEnemies() : [act.target && act.target.alive ? act.target : livingEnemies()[0]];
      targets.filter(Boolean).forEach(t => {
        const c = enemyCenter(t);
        addFx(sp.fx, c.x, c.y, { life: 0.7 });
        const r = magicDamage(h, t, sp);
        applyDamage(t, r.dmg, false, { weak: r.weak });
      });
    } else if (sp.kind === 'heal') {
      const t = act.target && act.target.alive ? act.target : h;
      const slot = heroSlot(G.party.indexOf(t));
      addFx('heal', slot.x + 8, slot.y - 4, { life: 0.7 });
      healTarget(t, Math.round(sp.power + h.mag * 1.2), true);
    } else if (sp.kind === 'healAll') {
      livingHeroes().forEach(t => {
        const slot = heroSlot(G.party.indexOf(t));
        addFx('heal', slot.x + 8, slot.y - 4, { life: 0.7 });
        healTarget(t, Math.round(sp.power + h.mag * 0.9), true);
      });
    } else if (sp.kind === 'revive') {
      const t = act.target;
      if (t && !t.alive) {
        t.alive = true;
        t.hp = Math.max(1, Math.round(t.maxhp * sp.power));
        t.atb = 0;
        const slot = heroSlot(G.party.indexOf(t));
        addFx('holy', slot.x + 8, slot.y - 4, { life: 0.9 });
        popup('REVIVED', slot.x + 8, slot.y - 18, '#ffe9a0');
      } else flashBanner('Nothing happened.');
    }
    return;
  }
  if (act.kind === 'item') {
    const it = ITEMS[act.itemId];
    G.bag[act.itemId] = Math.max(0, (G.bag[act.itemId] || 0) - 1);
    flashBanner(h.name + ' uses ' + it.name + '.');
    Audio_.sfx('item');
    a.hold = 0.55;
    const t = act.target;
    if (it.kind === 'heal' && t) { healTarget(t, it.power, true); addFx('heal', heroSlot(G.party.indexOf(t)).x + 8, heroSlot(G.party.indexOf(t)).y - 4); }
    else if (it.kind === 'mp' && t) { t.mp = Math.min(t.maxmp, t.mp + it.power); popup('+' + it.power + ' MP', heroSlot(G.party.indexOf(t)).x + 8, heroSlot(G.party.indexOf(t)).y - 6, '#9fd0ff'); }
    else if (it.kind === 'revive' && t) {
      if (!t.alive) { t.alive = true; t.hp = Math.round(t.maxhp * it.power); t.atb = 0; popup('REVIVED', heroSlot(G.party.indexOf(t)).x + 8, heroSlot(G.party.indexOf(t)).y - 18, '#ffe9a0'); }
      else flashBanner('Nothing happened.');
    } else if (it.kind === 'damage') {
      const foe = t && t.alive ? t : livingEnemies()[0];
      if (foe) {
        const c = enemyCenter(foe);
        addFx('fire', c.x, c.y, { life: 0.7 });
        applyDamage(foe, it.power + rndInt(0, 20), false, {});
      }
    }
  }
}

function resolveEnemyAction(a, e, act) {
  const targets = livingHeroes();
  if (!targets.length) return;
  const t = pick(targets);
  const slot = heroSlot(G.party.indexOf(t));
  a.hold = 0.5;
  if (act.kind === 'spell') {
    const sp = SPELLS[act.spellId];
    flashBanner(e.label + ' casts ' + sp.name + '!');
    Audio_.sfx('magic');
    const hit = sp.target === 'enemies' ? targets : [t];
    hit.forEach(x => {
      const s = heroSlot(G.party.indexOf(x));
      addFx(sp.fx, s.x + 8, s.y - 2, { life: 0.7 });
      const r = magicDamage(e, x, sp);
      applyDamage(x, r.dmg, true, {});
    });
    a.hold = 0.75;
    return;
  }
  if (act.kind === 'drain') {
    flashBanner(e.label + ' drains life!');
    Audio_.sfx('magic');
    const r = physDamage(e, t, 0.8);
    applyDamage(t, r.dmg, true, {});
    e.hp = Math.min(e.maxhp, e.hp + Math.round(r.dmg * 0.6));
    const c = enemyCenter(e);
    popup('+' + Math.round(r.dmg * 0.6), c.x, c.y - 6, '#8fffa8');
    return;
  }
  if (act.kind === 'rally') {
    flashBanner(e.label + ' howls for reinforcements!');
    livingEnemies().forEach(x => { x.atk = Math.round(x.atk * 1.08); x.offset = -4; });
    Audio_.sfx('cursor');
    return;
  }
  if (act.kind === 'steal') {
    const stolen = Math.min(G.gil, rndInt(10, 40));
    G.gil -= stolen;
    flashBanner(e.label + ' snatches ' + stolen + ' gil!');
    Audio_.sfx('cancel');
    return;
  }
  const mult = act.kind === 'pounce' ? 1.35 : act.kind === 'smash' ? 1.6 : 1;
  flashBanner(e.label + (act.kind === 'pounce' ? ' pounces!' : act.kind === 'smash' ? ' swings its club!' : ' attacks!'));
  addFx('slash', slot.x + 8, slot.y - 2);
  Audio_.sfx(mult > 1 ? 'crit' : 'hit');
  const r = physDamage(e, t, mult);
  applyDamage(t, r.dmg, true, { crit: r.crit });
  t.offset = -6;
}

/* --------------------------------------------------------------- result -- */

function beginVictory() {
  const exp = Battle.enemies.reduce((s, e) => s + e.exp, 0);
  const gil = Battle.enemies.reduce((s, e) => s + e.gil, 0);
  G.gil += gil;
  const lines = ['Victory!', 'Gained ' + exp + ' EXP and ' + gil + ' gil.'];
  const alive = livingHeroes();
  const share = Math.max(1, Math.round(exp / Math.max(1, alive.length)));
  alive.forEach(h => {
    grantExp(h, share).forEach(up => {
      lines.push(h.name + ' reached level ' + up.lv + '!');
      up.learned.forEach(s => lines.push(h.name + ' learned ' + SPELLS[s].name + '!'));
    });
  });
  if (Battle.boss) {
    G.flags.bossDown = true;
    lines.push('The Thornwilds fall quiet. Rivenbrook is safe.');
  }
  Battle.resultLines = lines;
  Battle.resultPage = 0;
  Battle.phase = 'result';
  Battle.result = 'win';
  Audio_.stop();
  Audio_.sfx(lines.length > 2 ? 'levelup' : 'victory');
}

function beginDefeat() {
  Battle.phase = 'result';
  Battle.result = 'lose';
  Battle.resultLines = ['The party has fallen...'];
  Battle.resultPage = 0;
  Audio_.stop();
  Audio_.sfx('ko');
}

function updateResult(dt) {
  if (!Input.tap('confirm') && !Input.tap('cancel')) return;
  Battle.resultPage++;
  Audio_.sfx('cursor');
  if (Battle.resultPage < Battle.resultLines.length) return;
  endBattle(Battle.result === 'win' ? 'win' : 'lose');
}

function endBattle(how) {
  fadeTo(() => {
    Battle.on = false;
    if (how === 'lose') {
      G.mode = 'gameover';
      Audio_.stop();
      return;
    }
    G.mode = 'field';
    G.party.forEach(h => { h.defending = false; h.atb = 0; });
    if (Battle.boss && how === 'win') {
      Field.npcs = Field.npcs.filter(n => !n.boss);
      Field.msg = makeMessage(['The chieftain crumbles into the shrine stones.',
        'The Thornwilds are quiet. Return to Rivenbrook a hero.']);
    }
    Audio_.play(Field.map.music === 'town' ? 'town' : Field.map.music === 'inn' ? 'inn' : 'field');
  });
}

/* ---------------------------------------------------------- battle draw -- */

const HORIZON = 76;

function drawBattleBackdrop() {
  const sky = ctx.createLinearGradient(0, 0, 0, HORIZON);
  if (Battle.boss) { sky.addColorStop(0, '#1d1024'); sky.addColorStop(1, '#63385a'); }
  else { sky.addColorStop(0, '#1b2b4a'); sky.addColorStop(1, '#5d84a4'); }
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, VW, HORIZON);

  // Two ridgelines for depth.
  const far = Battle.boss ? '#3a2440' : '#3c5f7c';
  const near = Battle.boss ? '#2a1a30' : '#2c4a64';
  const ridge = (color, base, amp, step, phase) => {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(-10, base);
    for (let x = -10; x <= VW + 10; x += step) {
      ctx.lineTo(x + step / 2, base - amp - ((x / step + phase) % 3) * 7);
      ctx.lineTo(x + step, base);
    }
    ctx.lineTo(VW + 10, base + 20); ctx.lineTo(-10, base + 20);
    ctx.closePath(); ctx.fill();
  };
  ridge(far, HORIZON, 22, 46, 0);
  ridge(near, HORIZON + 2, 12, 34, 1);
  ctx.fillStyle = Battle.boss ? 'rgba(255,220,255,0.10)' : 'rgba(220,240,255,0.12)';
  ctx.fillRect(0, HORIZON - 3, VW, 4);

  // Ground plane: banded so the perspective reads without a tile grid.
  const bands = Battle.boss
    ? [['#463c56', 84], ['#524668', 94], ['#5e5278', 104], ['#6a5e86', 116]]
    : [['#3a6136', 84], ['#45733e', 94], ['#52894a', 104], ['#5f9c54', 116]];
  let prev = HORIZON;
  bands.forEach(([c, y]) => { ctx.fillStyle = c; ctx.fillRect(0, prev, VW, y - prev + 1); prev = y; });
  ctx.fillStyle = 'rgba(0,0,0,0.13)';
  for (let i = 0; i < 26; i++) ctx.fillRect((i * 53 + (i % 3) * 11) % VW, 80 + (i % 5) * 7, 9 + (i % 3) * 3, 1);
  ctx.fillStyle = 'rgba(255,255,255,0.06)';
  for (let i = 0; i < 14; i++) ctx.fillRect((i * 71) % VW, 86 + (i % 4) * 8, 6, 1);
}

function drawBattle() {
  const sh = Battle.shake > 0 ? Math.round(rnd(-Battle.shake, Battle.shake)) : 0;
  ctx.save();
  ctx.translate(sh, 0);
  drawBattleBackdrop();

  // Enemies.
  Battle.enemies.forEach((e, i) => {
    if (!e.alive && e.dying <= 0) return;
    const s = enemySlot(e, i, Battle.enemies.length);
    const [w, h] = sprSize(e.sprite);
    const x = s.x + e.offset, y = s.y;
    ctx.save();
    if (e.dying > 0) ctx.globalAlpha = e.dying / 0.6;
    drawShadow(x + w, y + h * 2 - 2, w * 0.8);
    if (e.hurt > 0 && Math.floor(e.hurt * 30) % 2 === 0) {
      ctx.globalAlpha *= 0.65;
    }
    spr(e.sprite, x, y, { scale: 2 });
    ctx.restore();
  });

  // Party, right side (drawn far to near so the diagonal overlaps correctly).
  G.party.forEach((h, i) => {
    const s = heroSlot(i);
    const x = s.x + h.offset, y = s.y;
    if (!h.alive) {
      // Fallen party members lie on their back, the 16-bit shorthand for KO.
      ctx.save();
      ctx.globalAlpha = 0.5;
      ctx.translate(x + 12, y + 26);
      ctx.rotate(-Math.PI / 2);
      spr(h.sprite + '_hurt', -12, -18, { scale: 1.5 });
      ctx.restore();
      return;
    }
    const isActing = Battle.acting && Battle.acting.who === h && Battle.acting.stage >= 1;
    const isReady = Battle.actor === h;
    drawShadow(x + 12, y + 35, 9);
    if (h.hurt > 0 && Math.floor(h.hurt * 30) % 2 === 0) ctx.globalAlpha = 0.55;
    const pose = isActing ? '_attack' : '_ready';
    spr(h.sprite + pose, x, y + (isReady ? Math.sin(Battle.t * 6) * 1 : 0), { scale: 1.5 });
    ctx.globalAlpha = 1;
  });

  drawFx();

  // Damage numbers.
  Battle.popups.forEach(p => {
    const k = p.t / p.life;
    const y = p.y - 16 * Math.sin(Math.min(1, k * 1.6) * Math.PI * 0.5);
    ctx.save();
    ctx.globalAlpha = k > 0.75 ? (1 - k) * 4 : 1;
    drawText(p.text, p.x, y, p.color, { align: 'center' });
    ctx.restore();
  });
  ctx.restore();

  drawBattleUi();

  if (Battle.flash > 0) {
    ctx.fillStyle = 'rgba(255,255,255,' + Math.min(0.9, Battle.flash) + ')';
    ctx.fillRect(0, 0, VW, VH);
  }
}

function drawFx() {
  for (const f of Battle.fx) {
    const k = f.t / f.life;
    ctx.save();
    ctx.globalAlpha = 1 - k * k;
    switch (f.kind) {
      case 'slash': {
        ctx.strokeStyle = '#fff6d8'; ctx.lineWidth = 2;
        for (let i = 0; i < 3; i++) {
          ctx.beginPath();
          const off = i * 6 - 6;
          ctx.moveTo(f.x - 14 + off, f.y - 14 + k * 18);
          ctx.lineTo(f.x + 14 + off, f.y + 14 + k * 18);
          ctx.stroke();
        }
        break;
      }
      case 'fire': {
        for (let i = 0; i < 10; i++) {
          const a = i / 10 * Math.PI * 2 + k * 3;
          const r = 6 + k * 24;
          ctx.fillStyle = i % 2 ? '#ffb03c' : '#ff5a2c';
          ctx.fillRect(f.x + Math.cos(a) * r - 2, f.y + Math.sin(a) * r * 0.7 - 2, 4, 4);
        }
        ctx.fillStyle = 'rgba(255,220,140,0.6)';
        ctx.fillRect(f.x - 12, f.y - 12, 24, 24);
        break;
      }
      case 'ice': {
        for (let i = 0; i < 7; i++) {
          const a = i / 7 * Math.PI * 2;
          const r = 22 * (1 - k);
          ctx.fillStyle = i % 2 ? '#bff0ff' : '#5ac8f0';
          ctx.fillRect(f.x + Math.cos(a) * r - 1, f.y + Math.sin(a) * r - 5, 3, 10);
        }
        break;
      }
      case 'bolt': {
        ctx.strokeStyle = '#fff05a'; ctx.lineWidth = 2;
        ctx.beginPath();
        let x = f.x, y = f.y - 60;
        ctx.moveTo(x, y);
        for (let i = 0; i < 6; i++) { x += rnd(-7, 7); y += 12; ctx.lineTo(x, y); }
        ctx.stroke();
        ctx.fillStyle = 'rgba(255,255,180,0.45)';
        ctx.fillRect(f.x - 16, f.y - 10, 32, 20);
        break;
      }
      case 'quake': {
        ctx.fillStyle = '#a07a48';
        for (let i = 0; i < 14; i++) {
          const px = f.x + rnd(-26, 26), py = f.y + 16 - k * 30 + rnd(-6, 6);
          ctx.fillRect(px, py, 4, 4);
        }
        break;
      }
      case 'heal': {
        for (let i = 0; i < 8; i++) {
          const a = i / 8 * Math.PI * 2 + k * 2;
          const r = 14 * (1 - k * 0.4);
          ctx.fillStyle = i % 2 ? '#c8ffd8' : '#7ce8a0';
          ctx.fillRect(f.x + Math.cos(a) * r - 1, f.y + Math.sin(a) * r - 12 + k * -14, 3, 3);
        }
        break;
      }
      case 'holy':
      case 'flare': {
        ctx.fillStyle = f.kind === 'holy' ? 'rgba(255,246,200,0.8)' : 'rgba(255,180,255,0.8)';
        const r = 4 + k * 30;
        ctx.fillRect(f.x - r, f.y - 1, r * 2, 3);
        ctx.fillRect(f.x - 1, f.y - r, 3, r * 2);
        ctx.globalAlpha *= 0.6;
        ctx.beginPath(); ctx.arc(f.x, f.y, r * 0.8, 0, Math.PI * 2); ctx.fill();
        break;
      }
    }
    ctx.restore();
  }
}

function drawBattleUi() {
  // Top banner.
  if (Battle.bannerT > 0) {
    const w = Math.min(VW - 16, textWidth(Battle.banner) + 20);
    drawWindow(VW / 2 - w / 2, 6, w, 18, { tone: 'dark' });
    drawText(Battle.banner, VW / 2, 11, '#f6f0d8', { align: 'center' });
  }

  const panelY = 116, panelH = 60;
  // Party status, right.
  drawWindow(120, panelY, 196, panelH);
  G.party.forEach((h, i) => {
    const y = panelY + 8 + i * 16;
    const active = Battle.actor === h;
    drawText(h.name, 134, y, h.alive ? (active ? '#ffe9a0' : '#f2f4ff') : '#9a8090');
    if (h.defending && h.alive) spr('i_shield', 124, y - 1);
    else if (h.alive && h.hp / h.maxhp < 0.25) spr('i_heart', 124, y - 1);
    drawText(h.alive ? h.hp + '/' + h.maxhp : 'K.O.', 218, y, hpColor(h), { align: 'right' });
    drawText(h.maxmp ? h.mp + '/' + h.maxmp : '-', 254, y, '#9fd0ff', { align: 'right' });
    drawBar(260, y + 1, 50, 5, h.alive ? h.atb / 100 : 0,
      h.atb >= 100 ? '#fff0a8' : '#8fd8ff', h.atb >= 100 ? '#e0a83c' : '#3a72c8');
    if (active) drawCursor(124, y - 1, Battle.t);
  });

  // Command / list window, left.
  drawWindow(4, panelY, 112, panelH);
  if (Battle.phase === 'command' && Battle.actor) {
    if (Battle.sub === null) {
      const cmds = commandsFor(Battle.actor);
      cmds.forEach((c, i) => {
        const cx = 18 + (i % 2) * 50, cy = panelY + 9 + Math.floor(i / 2) * 15;
        drawText(c.label, cx, cy, '#f2f4ff');
        if (i === Battle.cmd) drawCursor(cx - 10, cy - 1, Battle.t);
      });
    } else {
      const items = Battle.sub === 'magic'
        ? Battle.actor.spells.map(id => ({ label: SPELLS[id].name, cost: SPELLS[id].mp, dim: Battle.actor.mp < SPELLS[id].mp }))
        : bagList().map(b => ({ label: ITEMS[b.id].name, cost: b.n, suffix: true }));
      if (!items.length) drawText('(nothing)', 20, panelY + 8, '#9aa4c8');
      const start = clamp(Battle.subIndex - 3, 0, Math.max(0, items.length - 4));
      for (let i = start; i < Math.min(items.length, start + 4); i++) {
        const cy = panelY + 8 + (i - start) * 13;
        const it = items[i];
        drawText(it.label, 18, cy, it.dim ? '#8a8fb0' : '#f2f4ff');
        drawText(it.cost + '', 110, cy, it.dim ? '#8a8fb0' : '#9fd0ff', { align: 'right' });
        if (i === Battle.subIndex) drawCursor(8, cy - 1, Battle.t);
      }
    }
  } else if (Battle.phase === 'target') {
    drawText('Choose a', 14, panelY + 10, '#f6e2a8');
    drawText('target', 14, panelY + 22, '#f6e2a8');
    drawText('[X] back', 14, panelY + 40, '#9aa4c8');
  } else if (Battle.phase === 'result') {
    wrapText(Battle.resultLines[Math.min(Battle.resultPage, Battle.resultLines.length - 1)], 17)
      .slice(0, 4).forEach((ln, i) => drawText(ln, 10, panelY + 7 + i * 12, '#f6f0d8'));
  } else {
    drawText('Gil', 14, panelY + 9, '#9aa4c8');
    drawText(G.gil + '', 108, panelY + 9, '#f6e2a8', { align: 'right' });
    const foe = livingEnemies()[0];
    if (foe) {
      drawText(foe.label.slice(0, 15), 14, panelY + 26, '#f2f4ff');
      drawBar(14, panelY + 40, 94, 5, foe.hp / foe.maxhp, '#ff9a9a', '#c0384c');
    }
  }

  // Target cursor over the battlefield.
  if (Battle.phase === 'target') {
    if (Battle.targetSide === 'enemy') {
      const e = Battle.enemies[Battle.target];
      if (e) {
        const s = enemySlot(e, Battle.target, Battle.enemies.length);
        drawCursor(s.x + s.w / 2 - 3, s.y - 14, Battle.t);
        const w = textWidth(e.label) + 12;
        drawWindow(clamp(s.x + s.w / 2 - w / 2, 2, VW - w - 2), s.y - 30, w, 15, { tone: 'dark' });
        drawText(e.label, clamp(s.x + s.w / 2, w / 2 + 8, VW - w / 2 - 8), s.y - 26, '#ffd0d0', { align: 'center' });
      }
    } else {
      const s = heroSlot(Battle.target);
      drawCursor(s.x - 12, s.y + 12, Battle.t);
    }
  }
}

function classIcon(h) { return h.id === 'aldric' ? 'i_sword' : 'i_staff'; }

function hpColor(h) {
  if (!h.alive) return '#c08090';
  const r = h.hp / h.maxhp;
  return r < 0.2 ? '#ff6a6a' : r < 0.5 ? '#ffd75a' : '#f2f4ff';
}

/* ================================================================== menus */

function drawTextBig(str, x, y, color, scale, opts) {
  opts = opts || {};
  scale = scale || 2;
  const w = textWidth(str) * scale;
  if (opts.align === 'center') x -= w / 2;
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  const sheet = FontCache.tint(color);
  const shadow = FontCache.tint(opts.shadowColor || '#12101c');
  for (let pass = 0; pass < 2; pass++) {
    const s = pass === 0 ? shadow : sheet;
    const ox = pass === 0 ? scale : 0, oy = pass === 0 ? scale : 0;
    for (let i = 0; i < str.length; i++) {
      const idx = FontCache.index[str[i]];
      if (idx === undefined) continue;
      ctx.drawImage(s, idx * GLYPH_W, 0, GLYPH_W, GLYPH_H,
        Math.round(x + i * GLYPH_W * scale + ox), Math.round(y + oy),
        GLYPH_W * scale, GLYPH_H * scale);
    }
  }
  ctx.restore();
  return w;
}

const Menu = {
  state: 'root', root: 0, index: 0, scroll: 0, who: 0, spell: 0, note: '', noteT: 0
};

const MENU_ROOT = [
  { id: 'item', label: 'Item' },
  { id: 'magic', label: 'Magic' },
  { id: 'status', label: 'Status' },
  { id: 'save', label: 'Save' },
  { id: 'sound', label: 'Sound' },
  { id: 'close', label: 'Return' }
];

function openMenu() {
  G.mode = 'menu';
  Menu.state = 'root'; Menu.root = 0; Menu.index = 0; Menu.scroll = 0;
  Audio_.sfx('confirm');
}

function menuNote(text) { Menu.note = text; Menu.noteT = 2.2; }

function updateMenu(dt) {
  G.playtime += dt;
  Menu.noteT = Math.max(0, Menu.noteT - dt);
  const bag = bagList();

  if (Menu.state === 'root') {
    if (Input.nav('up', dt)) { Menu.root = (Menu.root + MENU_ROOT.length - 1) % MENU_ROOT.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Menu.root = (Menu.root + 1) % MENU_ROOT.length; Audio_.sfx('cursor'); }
    if (Input.tap('cancel') || Input.tap('menu')) { closeMenu(); return; }
    if (Input.tap('confirm')) {
      const id = MENU_ROOT[Menu.root].id;
      Audio_.sfx('confirm');
      if (id === 'close') { closeMenu(); return; }
      if (id === 'item') { Menu.state = 'item'; Menu.index = 0; Menu.scroll = 0; }
      else if (id === 'magic') { Menu.state = 'magicWho'; Menu.who = 0; }
      else if (id === 'status') { Menu.state = 'status'; Menu.who = 0; }
      else if (id === 'sound') { menuNote(Audio_.toggleMute() ? 'Sound off.' : 'Sound on.'); }
      else if (id === 'save') { menuNote(saveGame() ? 'Journal saved.' : 'Could not save.'); }
    }
    return;
  }

  if (Menu.state === 'item') {
    if (Input.tap('cancel')) { Menu.state = 'root'; Audio_.sfx('cancel'); return; }
    if (!bag.length) return;
    if (Input.nav('up', dt)) { Menu.index = (Menu.index + bag.length - 1) % bag.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Menu.index = (Menu.index + 1) % bag.length; Audio_.sfx('cursor'); }
    if (Input.tap('confirm')) {
      const it = ITEMS[bag[Menu.index].id];
      if (it.kind === 'damage') { menuNote('Only useful in battle.'); Audio_.sfx('cancel'); return; }
      Menu.state = 'itemTarget'; Menu.who = 0; Audio_.sfx('confirm');
    }
    return;
  }

  if (Menu.state === 'itemTarget') {
    if (Input.tap('cancel')) { Menu.state = 'item'; Audio_.sfx('cancel'); return; }
    if (Input.nav('up', dt)) { Menu.who = (Menu.who + G.party.length - 1) % G.party.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Menu.who = (Menu.who + 1) % G.party.length; Audio_.sfx('cursor'); }
    if (Input.tap('confirm')) {
      const entry = bag[Math.min(Menu.index, bag.length - 1)];
      if (!entry) { Menu.state = 'item'; return; }
      const it = ITEMS[entry.id], h = G.party[Menu.who];
      let used = false;
      if (it.kind === 'heal' && h.alive && h.hp < h.maxhp) { h.hp = Math.min(h.maxhp, h.hp + it.power); used = true; }
      else if (it.kind === 'mp' && h.alive && h.mp < h.maxmp) { h.mp = Math.min(h.maxmp, h.mp + it.power); used = true; }
      else if (it.kind === 'revive' && !h.alive) { h.alive = true; h.hp = Math.round(h.maxhp * it.power); used = true; }
      if (used) {
        G.bag[entry.id]--;
        if (G.bag[entry.id] <= 0) delete G.bag[entry.id];
        Audio_.sfx('heal');
        menuNote(h.name + ' used ' + it.name + '.');
        if (!bagList().length) Menu.state = 'root';
        else { Menu.state = 'item'; Menu.index = clamp(Menu.index, 0, bagList().length - 1); }
      } else { Audio_.sfx('cancel'); menuNote('It had no effect.'); }
    }
    return;
  }

  if (Menu.state === 'magicWho') {
    if (Input.tap('cancel')) { Menu.state = 'root'; Audio_.sfx('cancel'); return; }
    if (Input.nav('up', dt)) { Menu.who = (Menu.who + G.party.length - 1) % G.party.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Menu.who = (Menu.who + 1) % G.party.length; Audio_.sfx('cursor'); }
    if (Input.tap('confirm')) {
      const h = G.party[Menu.who];
      if (!h.spells.length) { menuNote(h.name + ' knows no magic.'); Audio_.sfx('cancel'); return; }
      Menu.state = 'magicList'; Menu.spell = 0; Audio_.sfx('confirm');
    }
    return;
  }

  if (Menu.state === 'magicList') {
    const h = G.party[Menu.who];
    if (Input.tap('cancel')) { Menu.state = 'magicWho'; Audio_.sfx('cancel'); return; }
    if (Input.nav('up', dt)) { Menu.spell = (Menu.spell + h.spells.length - 1) % h.spells.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Menu.spell = (Menu.spell + 1) % h.spells.length; Audio_.sfx('cursor'); }
    if (Input.tap('confirm')) {
      const sp = SPELLS[h.spells[Menu.spell]];
      if (sp.kind === 'attack') { menuNote('Save that for a fight.'); Audio_.sfx('cancel'); return; }
      if (!h.alive) { menuNote(h.name + ' cannot act.'); Audio_.sfx('cancel'); return; }
      if (h.mp < sp.mp) { menuNote('Not enough MP.'); Audio_.sfx('cancel'); return; }
      Menu.state = 'magicTarget'; Menu.target = 0; Audio_.sfx('confirm');
    }
    return;
  }

  if (Menu.state === 'magicTarget') {
    const h = G.party[Menu.who];
    const sp = SPELLS[h.spells[Menu.spell]];
    if (Input.tap('cancel')) { Menu.state = 'magicList'; Audio_.sfx('cancel'); return; }
    if (Input.nav('up', dt)) { Menu.target = (Menu.target + G.party.length - 1) % G.party.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Menu.target = (Menu.target + 1) % G.party.length; Audio_.sfx('cursor'); }
    if (Input.tap('confirm')) {
      const t = G.party[Menu.target];
      let ok = false;
      if (sp.kind === 'heal' && t.alive && t.hp < t.maxhp) { t.hp = Math.min(t.maxhp, t.hp + Math.round(sp.power + h.mag * 1.2)); ok = true; }
      else if (sp.kind === 'healAll') { G.party.forEach(x => { if (x.alive) x.hp = Math.min(x.maxhp, x.hp + Math.round(sp.power + h.mag * 0.9)); }); ok = true; }
      else if (sp.kind === 'revive' && !t.alive) { t.alive = true; t.hp = Math.max(1, Math.round(t.maxhp * sp.power)); ok = true; }
      if (ok) { h.mp -= sp.mp; Audio_.sfx('heal'); menuNote(h.name + ' casts ' + sp.name + '.'); Menu.state = 'magicList'; }
      else { Audio_.sfx('cancel'); menuNote('Nothing happened.'); }
    }
    return;
  }

  if (Menu.state === 'status') {
    if (Input.tap('cancel')) { Menu.state = 'root'; Audio_.sfx('cancel'); return; }
    if (Input.nav('up', dt)) { Menu.who = (Menu.who + G.party.length - 1) % G.party.length; Audio_.sfx('cursor'); }
    if (Input.nav('down', dt)) { Menu.who = (Menu.who + 1) % G.party.length; Audio_.sfx('cursor'); }
    return;
  }
}

function closeMenu() { G.mode = 'field'; Audio_.sfx('cancel'); }

function fmtTime(sec) {
  const h = Math.floor(sec / 3600), m = Math.floor(sec / 60) % 60, s = Math.floor(sec) % 60;
  const pad = n => (n < 10 ? '0' : '') + n;
  return pad(h) + ':' + pad(m) + ':' + pad(s);
}

function drawMenu() {
  drawField();
  ctx.fillStyle = 'rgba(8,6,18,0.72)';
  ctx.fillRect(0, 0, VW, VH);

  // Command column.
  drawWindow(6, 6, 84, 108);
  MENU_ROOT.forEach((c, i) => {
    const y = 14 + i * 16;
    const dim = Menu.state !== 'root' && i !== Menu.root;
    drawText(c.label, 26, y, dim ? '#8a92b8' : '#f2f4ff');
    if (i === Menu.root) drawCursor(14, y - 1, Field.anim);
  });

  // Purse.
  drawWindow(6, 118, 84, 56);
  spr('i_gil', 14, 124);
  drawText('Gil', 25, 125, '#9aa4c8');
  drawText(G.gil + '', 82, 136, '#f6e2a8', { align: 'right' });
  drawText('Time', 14, 148, '#9aa4c8');
  drawText(fmtTime(G.playtime), 82, 159, '#f2f4ff', { align: 'right' });

  // Right pane.
  drawWindow(96, 6, VW - 102, VH - 12);
  if (Menu.state === 'status') drawStatusPane();
  else if (Menu.state === 'item' || Menu.state === 'itemTarget') drawItemPane();
  else if (Menu.state.indexOf('magic') === 0) drawMagicPane();
  else drawPartyPane();

  if (Menu.noteT > 0) {
    const w = textWidth(Menu.note) + 20;
    drawWindow(VW / 2 - w / 2, VH - 26, w, 18, { tone: 'dark' });
    drawText(Menu.note, VW / 2, VH - 21, '#f6e2a8', { align: 'center' });
  }
}

function drawPartyRow(h, x, y, highlight) {
  if (highlight) {
    ctx.fillStyle = 'rgba(120,160,255,0.14)';
    ctx.fillRect(x - 4, y - 4, 202, 46);
  }
  spr(h.sprite + '_down0', x, y - 6, { scale: 1.5 });
  spr(classIcon(h), x + 30, y - 1);
  drawText(h.name, x + 40, y, h.alive ? '#f2f4ff' : '#c08090');
  drawText(h.title, x + 40, y + 11, '#9aa4c8');
  drawText('Lv ' + h.lv, x + 132, y, '#f6e2a8');
  drawText('HP', x + 30, y + 24, '#9aa4c8');
  drawText(h.hp + '/' + h.maxhp, x + 108, y + 24, hpColor(h), { align: 'right' });
  drawBar(x + 30, y + 34, 78, 4, h.hp / h.maxhp, '#9fffb0', '#3f9a54');
  if (h.maxmp) {
    drawText('MP', x + 120, y + 24, '#9aa4c8');
    drawText(h.mp + '/' + h.maxmp, x + 196, y + 24, '#9fd0ff', { align: 'right' });
    drawBar(x + 120, y + 34, 76, 4, h.mp / h.maxmp, '#bfe4ff', '#3a72c8');
  } else {
    drawText('No magic', x + 120, y + 24, '#7a82a8');
  }
}

function drawPartyPane() {
  drawText('PARTY', 106, 12, '#f6e2a8');
  G.party.forEach((h, i) => drawPartyRow(h, 110, 30 + i * 48, false));
}

function drawItemPane() {
  const bag = bagList();
  drawText('ITEMS', 106, 12, '#f6e2a8');
  if (!bag.length) { drawText('The bag is empty.', 110, 34, '#9aa4c8'); return; }
  const start = clamp(Menu.index - 3, 0, Math.max(0, bag.length - 5));
  for (let i = start; i < Math.min(bag.length, start + 5); i++) {
    const y = 28 + (i - start) * 16;
    const it = ITEMS[bag[i].id];
    spr(it.icon, 116, y - 1);
    drawText(it.name, 128, y, Menu.state === 'item' && i === Menu.index ? '#ffe9a0' : '#f2f4ff');
    drawText('x' + bag[i].n, 300, y, '#9fd0ff', { align: 'right' });
    if (i === Menu.index) drawCursor(106, y - 1, Field.anim);
  }
  const cur = ITEMS[bag[Math.min(Menu.index, bag.length - 1)].id];
  drawText(cur.desc, 110, 112, '#9aa4c8');
  if (Menu.state === 'itemTarget') {
    drawText('Use on:', 110, 126, '#f6e2a8');
    G.party.forEach((h, i) => {
      const y = 138 + i * 12;
      drawText(h.name, 128, y, h.alive ? '#f2f4ff' : '#c08090');
      drawText(h.hp + '/' + h.maxhp, 250, y, hpColor(h), { align: 'right' });
      if (h.maxmp) drawText('MP ' + h.mp, 300, y, '#9fd0ff', { align: 'right' });
      if (i === Menu.who) drawCursor(116, y - 1, Field.anim);
    });
  }
}

function drawMagicPane() {
  drawText('MAGIC', 106, 12, '#f6e2a8');
  G.party.forEach((h, i) => {
    const y = 28 + i * 14;
    drawText(h.name, 128, y, i === Menu.who ? '#ffe9a0' : '#f2f4ff');
    drawText(h.spells.length ? 'MP ' + h.mp + '/' + h.maxmp : '-', 300, y, '#9fd0ff', { align: 'right' });
    if (i === Menu.who && Menu.state === 'magicWho') drawCursor(116, y - 1, Field.anim);
  });
  if (Menu.state === 'magicWho') { drawText('Choose a caster.', 110, 84, '#9aa4c8'); return; }
  const h = G.party[Menu.who];
  h.spells.forEach((id, i) => {
    const sp = SPELLS[id];
    const y = 84 + i * 14;
    const dim = h.mp < sp.mp;
    drawText(sp.name, 128, y, dim ? '#8a8fb0' : (i === Menu.spell ? '#ffe9a0' : '#f2f4ff'));
    drawText(sp.mp + ' MP', 240, y, dim ? '#8a8fb0' : '#9fd0ff', { align: 'right' });
    drawText(sp.kind === 'attack' ? 'battle' : 'field', 306, y, '#7a82a8', { align: 'right' });
    if (i === Menu.spell) drawCursor(116, y - 1, Field.anim);
  });
  if (Menu.state === 'magicTarget') {
    ctx.fillStyle = 'rgba(8,6,18,0.6)';
    ctx.fillRect(100, 118, VW - 110, 52);
    drawText('Cast on:', 110, 122, '#f6e2a8');
    G.party.forEach((x, i) => {
      const y = 136 + i * 11;
      drawText(x.name, 128, y, x.alive ? '#f2f4ff' : '#c08090');
      drawText(x.hp + '/' + x.maxhp, 250, y, hpColor(x), { align: 'right' });
      if (i === Menu.target) drawCursor(116, y - 1, Field.anim);
    });
  }
}

function drawStatusPane() {
  const h = G.party[Menu.who];
  drawText('STATUS', 106, 12, '#f6e2a8');

  // Who-to-inspect column on the left, detail sheet on the right.
  G.party.forEach((x, i) => {
    const y = 30 + i * 14;
    drawText(x.name, 118, y, i === Menu.who ? '#ffe9a0' : (x.alive ? '#bfc8ea' : '#c08090'));
    if (i === Menu.who) drawCursor(106, y - 1, Field.anim);
  });
  ctx.fillStyle = '#4d63b4';
  ctx.fillRect(154, 24, 1, VH - 46);

  spr(h.sprite + '_ready', 162, 26, { scale: 2 });
  drawText(h.name, 200, 30, '#f2f4ff');
  spr(classIcon(h), 200, 41);
  drawText(h.title, 212, 42, '#9aa4c8');
  drawText('Level ' + h.lv, 200, 56, '#f6e2a8');
  const need = expToNext(h.lv) - h.exp;
  drawText('Next in ' + need, 200, 68, '#9aa4c8');
  drawBar(200, 79, 100, 4, h.exp / expToNext(h.lv), '#ffe9a0', '#c08a2c');

  const stats = [['HP', h.hp + '/' + h.maxhp], ['MP', h.maxmp ? h.mp + '/' + h.maxmp : '-'],
  ['Attack', h.atk], ['Defense', h.def], ['Magic', h.mag], ['Speed', h.spd]];
  stats.forEach((st, i) => {
    const x = 106 + (i % 2) * 104, y = 96 + Math.floor(i / 2) * 14;
    drawText(st[0], x, y, '#9aa4c8');
    drawText(st[1] + '', x + 94, y, '#f2f4ff', { align: 'right' });
  });

  drawText('Spells', 106, 140, '#9aa4c8');
  const known = h.spells.map(sp => SPELLS[sp].name).join(', ') || 'none';
  wrapText(known, 30).slice(0, 2).forEach((ln, i) => drawText(ln, 106, 152 + i * 11, '#bfc8ea'));
}

/* =========================================================== inn and shop */

const Shop = { open: false, index: 0, mode: 'buy', note: '', noteT: 0 };

function openShop(npc) {
  G.mode = 'shop'; Shop.index = 0; Shop.note = ''; Shop.noteT = 0;
  Audio_.sfx('confirm');
}

function updateShop(dt) {
  Shop.noteT = Math.max(0, Shop.noteT - dt);
  if (Input.tap('cancel') || Input.tap('menu')) { G.mode = 'field'; Audio_.sfx('cancel'); return; }
  if (Input.nav('up', dt)) { Shop.index = (Shop.index + SHOP_STOCK.length - 1) % SHOP_STOCK.length; Audio_.sfx('cursor'); }
  if (Input.nav('down', dt)) { Shop.index = (Shop.index + 1) % SHOP_STOCK.length; Audio_.sfx('cursor'); }
  if (Input.tap('confirm')) {
    const id = SHOP_STOCK[Shop.index], it = ITEMS[id];
    if (G.gil < it.price) { Shop.note = 'Not enough gil.'; Shop.noteT = 1.6; Audio_.sfx('cancel'); return; }
    G.gil -= it.price;
    G.bag[id] = (G.bag[id] || 0) + 1;
    Shop.note = 'Bought ' + it.name + '.';
    Shop.noteT = 1.6;
    Audio_.sfx('item');
  }
}

function drawShop() {
  drawField();
  ctx.fillStyle = 'rgba(8,6,18,0.7)';
  ctx.fillRect(0, 0, VW, VH);
  drawWindow(20, 14, 180, 150);
  drawText('QUARTERMASTER', 30, 22, '#f6e2a8');
  SHOP_STOCK.forEach((id, i) => {
    const it = ITEMS[id], y = 40 + i * 18;
    spr(it.icon, 38, y - 1);
    drawText(it.name, 52, y, i === Shop.index ? '#ffe9a0' : '#f2f4ff');
    drawText(it.price + 'g', 192, y, G.gil >= it.price ? '#9fd0ff' : '#8a8fb0', { align: 'right' });
    if (i === Shop.index) drawCursor(28, y - 1, Field.anim);
  });
  drawText(ITEMS[SHOP_STOCK[Shop.index]].desc, 30, 136, '#9aa4c8');
  drawText('[Z] buy   [X] leave', 30, 150, '#7a82a8');

  drawWindow(206, 14, 96, 44);
  spr('i_gil', 214, 21);
  drawText('Gil', 225, 22, '#9aa4c8');
  drawText(G.gil + '', 294, 36, '#f6e2a8', { align: 'right' });
  drawWindow(206, 64, 96, 100);
  drawText('BAG', 214, 72, '#9aa4c8');
  bagList().slice(0, 6).forEach((b, i) => {
    drawText(ITEMS[b.id].name.slice(0, 10), 214, 88 + i * 12, '#f2f4ff');
    drawText('x' + b.n, 294, 88 + i * 12, '#9fd0ff', { align: 'right' });
  });
  if (Shop.noteT > 0) {
    const w = textWidth(Shop.note) + 20;
    drawWindow(VW / 2 - w / 2, VH - 24, w, 18, { tone: 'dark' });
    drawText(Shop.note, VW / 2, VH - 19, '#f6e2a8', { align: 'center' });
  }
}

const INN_COST = 50;
function openInn(npc) {
  const dead = G.party.some(h => !h.alive);
  Field.msg = makeMessage([
    'Welcome to the Amber Lantern.',
    'A bed and a hot meal, ' + INN_COST + ' gil.' + (dead ? ' Your fallen will wake, too.' : '') + ' Rest here?'
  ], {
    speaker: npc.name,
    choice: {
      options: ['Yes', 'No'], index: 0,
      onPick: idx => {
        if (idx !== 0) { Field.msg = makeMessage(['Mind how you go, then.'], { speaker: npc.name }); return; }
        if (G.gil < INN_COST) {
          Field.msg = makeMessage(['You are short on coin. Come back richer.'], { speaker: npc.name });
          Audio_.sfx('cancel');
          return;
        }
        G.gil -= INN_COST;
        G.party.forEach(h => { h.alive = true; h.hp = h.maxhp; h.mp = h.maxmp; });
        Audio_.sfx('heal');
        Field.msg = makeMessage(['You sleep until the lanterns burn low.',
          'The party is fully restored!']);
      }
    }
  });
  Audio_.sfx('confirm');
}

/* ====================================================== title / game over */

const Title = { index: 0, t: 0 };

function drawTitle() {
  const g = ctx.createLinearGradient(0, 0, 0, VH);
  g.addColorStop(0, '#0d1030'); g.addColorStop(0.55, '#24244e'); g.addColorStop(1, '#5a3a54');
  ctx.fillStyle = g; ctx.fillRect(0, 0, VW, VH);
  for (let i = 0; i < 60; i++) {
    const x = (i * 71) % VW, y = (i * 37) % 90;
    const tw = 0.5 + 0.5 * Math.sin(Title.t * 2 + i);
    ctx.fillStyle = 'rgba(255,255,255,' + (0.15 + tw * 0.5) + ')';
    ctx.fillRect(x, y, 1, 1);
  }
  // Skyline of the town, silhouetted.
  ctx.fillStyle = '#171a38';
  ctx.fillRect(0, 128, VW, VH - 128);
  for (let i = 0; i < 9; i++) {
    const x = i * 38 - 10, h = 20 + (i % 4) * 12;
    ctx.fillRect(x, 128 - h, 30, h);
    ctx.beginPath();
    ctx.moveTo(x - 4, 128 - h); ctx.lineTo(x + 15, 128 - h - 12); ctx.lineTo(x + 34, 128 - h);
    ctx.closePath(); ctx.fill();
  }
  ctx.fillStyle = 'rgba(246,226,168,0.9)';
  for (let i = 0; i < 14; i++) ctx.fillRect(10 + i * 22, 118 + (i % 3) * 6, 2, 3);

  drawTextBig('RIVENBROOK', VW / 2, 26, '#f6e2a8', 3, { align: 'center' });
  drawText('a tale of the thornwilds', VW / 2, 60, '#c8cdf0', { align: 'center' });

  spr('aldric_right0', 128, 96, { scale: 2 });
  spr('lyra_right0', 152, 96, { scale: 2 });
  spr('mira_right0', 176, 96, { scale: 2 });

  const opts = ['New Game'];
  if (hasSave()) opts.push('Continue');
  drawWindow(VW / 2 - 52, 138, 104, 16 + opts.length * 14);
  opts.forEach((o, i) => {
    const y = 145 + i * 14;
    drawText(o, VW / 2 - 22, y, i === Title.index ? '#ffe9a0' : '#f2f4ff');
    if (i === Title.index) drawCursor(VW / 2 - 36, y - 1, Title.t);
  });
  drawText('Arrows move   Z confirm   X cancel   C menu', VW / 2, VH - 10, '#8f97c0', { align: 'center' });
}

function updateTitle(dt) {
  Title.t += dt;
  const opts = hasSave() ? 2 : 1;
  if (Input.nav('up', dt)) { Title.index = (Title.index + opts - 1) % opts; Audio_.sfx('cursor'); }
  if (Input.nav('down', dt)) { Title.index = (Title.index + 1) % opts; Audio_.sfx('cursor'); }
  if (Input.tap('confirm')) {
    Audio_.sfx('confirm');
    const choice = Title.index;
    fadeTo(() => {
      if (choice === 1 && hasSave()) { if (!loadGame()) newGame(); }
      else newGame();
      G.mode = 'field';
    });
  }
}

const GameOver = { index: 0, t: 0 };

function updateGameOver(dt) {
  GameOver.t += dt;
  const opts = hasSave() ? 2 : 1;
  if (Input.nav('up', dt)) { GameOver.index = (GameOver.index + opts - 1) % opts; Audio_.sfx('cursor'); }
  if (Input.nav('down', dt)) { GameOver.index = (GameOver.index + 1) % opts; Audio_.sfx('cursor'); }
  if (Input.tap('confirm')) {
    Audio_.sfx('confirm');
    const choice = GameOver.index;
    fadeTo(() => {
      if (choice === 0 && hasSave()) { loadGame(); G.mode = 'field'; }
      else { G.mode = 'title'; Title.index = 0; Audio_.stop(); }
    });
  }
}

function drawGameOver() {
  ctx.fillStyle = '#140810';
  ctx.fillRect(0, 0, VW, VH);
  ctx.fillStyle = 'rgba(120,20,40,0.25)';
  ctx.fillRect(0, 60, VW, 60);
  drawTextBig('GAME OVER', VW / 2, 44, '#e07a8a', 3, { align: 'center' });
  drawText('The Thornwilds claim another party.', VW / 2, 84, '#a8899a', { align: 'center' });
  const opts = hasSave() ? ['Load Journal', 'Title Screen'] : ['Title Screen'];
  drawWindow(VW / 2 - 56, 108, 112, 16 + opts.length * 14, { tone: 'red' });
  opts.forEach((o, i) => {
    const y = 115 + i * 14;
    drawText(o, VW / 2 - 26, y, i === GameOver.index ? '#ffe9a0' : '#f2f4ff');
    if (i === GameOver.index) drawCursor(VW / 2 - 40, y - 1, GameOver.t);
  });
}

/* ================================================================== fade */

function fadeTo(action) {
  if (G.fadeDir !== 0) return;
  G.fadeDir = 1;
  G.fadeThen = action;
}

function updateFade(dt) {
  if (G.fadeDir === 0) return false;
  G.fade += G.fadeDir * dt * 3.4;
  if (G.fade >= 1) {
    G.fade = 1;
    if (G.fadeThen) { const f = G.fadeThen; G.fadeThen = null; f(); }
    G.fadeDir = -1;
  } else if (G.fade <= 0) { G.fade = 0; G.fadeDir = 0; }
  return true;
}

function drawFade() {
  if (G.fade <= 0) return;
  ctx.fillStyle = 'rgba(6,4,12,' + G.fade + ')';
  ctx.fillRect(0, 0, VW, VH);
}

/* ============================================================== main loop */

let last = 0;
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000 || 0);
  last = now;

  const blocked = updateFade(dt) && G.fadeDir > 0;
  if (Input.tap('mute') && G.mode !== 'menu') {
    Audio_.toggleMute();
  }
  if (!blocked) {
    switch (G.mode) {
      case 'title': updateTitle(dt); break;
      case 'field': updateField(dt); break;
      case 'battle': updateBattle(dt); break;
      case 'menu': updateMenu(dt); break;
      case 'shop': updateShop(dt); break;
      case 'gameover': updateGameOver(dt); break;
    }
  }
  bannerTimer = Math.max(0, bannerTimer - dt);

  switch (G.mode) {
    case 'title': drawTitle(); break;
    case 'field': drawField(); break;
    case 'battle': drawBattle(); break;
    case 'menu': drawMenu(); break;
    case 'shop': drawShop(); break;
    case 'gameover': drawGameOver(); break;
  }
  drawFade();
  Input.endFrame();
  requestAnimationFrame(frame);
}

function boot() {
  FontCache.build();
  Input.init();
  fitCanvas();
  atlas.onload = () => {
    document.getElementById('loading').style.display = 'none';
    requestAnimationFrame(frame);
  };
  atlas.src = ATLAS_PNG;
  const start = () => { Audio_.ensure(); Audio_.resume(); };
  window.addEventListener('keydown', start, { once: true });
  window.addEventListener('pointerdown', start, { once: true });
}

boot();
