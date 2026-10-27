// Reel timeline. Every frame is a pure function of time: render.mjs calls
// window.__seek(t) and takes a screenshot, so nothing depends on the real clock.
// Motion supplies the physics and easing (spring, easeOut, easeIn, mix, clamp);
// the values are written straight to the DOM on each seek.
const { spring, easeOut, easeIn, easeInOut, mix, clamp } = Motion;

const VIDEO = new URLSearchParams(location.search).get('mode') === 'video';
if (VIDEO) { document.body.classList.add('video'); document.documentElement.style.background = 'transparent'; }

// Beats (seconds). Script: hook 0-3, case 3-10, opinion 10-18, call to action 18-22.
const T = {
  coverOut: 0.30, hookIn: 0.54,
  wipe12: 2.86, s2aIn: 3.06, s2aOut: 5.96, s2bIn: 6.20, countIn: 6.44, countDur: 0.8,
  wipe23: 9.84, s3aIn: 10.04, s3aOut: 13.84, s3bIn: 14.10,
  wipe34: 17.84, s4In: 18.04, typeIn: 19.0, typeStep: 0.045,
  end: 22.0,
};
const WIPE = 0.18;
const W = 1080, MX = 72, MAXW = W - 2 * MX;

const $ = id => document.getElementById(id);
const tracks = [];
const at = f => tracks.push(f);
const prog = (t, t0, d, ease = x => x) => ease(clamp(0, 1, (t - t0) / d));
const px = v => v.toFixed(2) + 'px';

function springer(stiffness, damping) {
  const g = spring({ keyframes: [0, 1], stiffness, damping, restDelta: 0.0001, restSpeed: 0.001 });
  return dt => (dt <= 0 ? 0 : dt >= 1.5 ? 1 : g.next(dt * 1000).value);
}
const SLIDE = springer(360, 27);  // words sliding up
const POP = springer(420, 18);    // accent settles back from 1.08
const FLY = springer(300, 26);    // stickers flying in
const TAG = springer(400, 22);    // yellow label

// ---------- building ----------
// "Тобі / *не потрібна* / велика" -> lines split by "/", accent between asterisks.
function buildHead(el) {
  const src = el.textContent.trim();
  el.textContent = '';
  let acc = false;
  for (const line of src.split('/').map(s => s.trim())) {
    const ln = document.createElement('div');
    ln.className = 'ln';
    const toks = line.split(/\s+/);
    toks.forEach((tok, i) => {
      let word = tok, a = acc;
      if (word.startsWith('*')) { a = acc = true; word = word.slice(1); }
      const closes = word.endsWith('*');
      if (closes) word = word.slice(0, -1);
      const w = document.createElement('span');
      w.className = 'w' + (a ? ' acc' : '');
      w.innerHTML = `<span class="wi">${a ? '<span class="mk"></span>' : ''}<span class="tx">${word}</span></span>`;
      ln.appendChild(w);
      if (i < toks.length - 1) ln.appendChild(document.createTextNode(' '));
      if (closes) acc = false;
    });
    el.appendChild(ln);
  }
}

// Shrink from data-size until every line fits the 936 px text column.
function fit(el, maxW = MAXW) {
  let s = +el.dataset.size;
  const lines = el.querySelectorAll('.ln').length ? [...el.querySelectorAll('.ln')] : [el];
  for (; s > 40; s -= 2) {
    el.style.fontSize = s + 'px';
    if (lines.every(l => l.getBoundingClientRect().width <= maxW)) break;
  }
  return s;
}

// Let the marker of an accent phrase run under the space to the next accent word.
function joinMarkers(el) {
  const ws = [...el.querySelectorAll('.w')];
  ws.forEach((w, i) => {
    const n = ws[i + 1];
    if (!w.classList.contains('acc') || !n || !n.classList.contains('acc')) return;
    const a = w.getBoundingClientRect(), b = n.getBoundingClientRect();
    if (Math.abs(a.top - b.top) > 2) return;
    w.querySelector('.mk').style.right = px(-(b.left - a.right) - 1);
  });
}

const below = (el, ref, gap) => { el.style.top = px(ref.offsetTop + ref.offsetHeight + gap); };

// ---------- animation helpers ----------
function words(el, { tIn, tOut = null, stagger = 0.05, dy = 40, skipIn = false, accent = null }) {
  const ws = [...el.querySelectorAll('.w')];
  ws.forEach((w, i) => {
    // the old text is gone before the next one arrives: exit = 0.18 s + 0.015 s per word
    const t0 = tIn + i * stagger, t1 = tOut == null ? null : tOut + i * 0.015;
    at(t => {
      let y = 0, o = 1;
      if (!skipIn) {
        if (t < t0) { y = dy; o = 0; } else { y = mix(dy, 0, SLIDE(t - t0)); o = prog(t, t0, 0.25, easeOut); }
      }
      if (t1 != null && t >= t1) { const q = prog(t, t1, 0.18, easeIn); y = mix(y, -34, q); o *= 1 - q; }
      w.style.transform = `translate3d(0, ${px(y)}, 0)`;
      w.style.opacity = o.toFixed(3);
    });
  });
  // accent: pop 1 -> 1.08 -> 1 while the green marker draws left to right
  if (accent != null) ws.filter(w => w.classList.contains('acc')).forEach((w, i) => {
    const wi = w.querySelector('.wi'), mk = w.querySelector('.mk'), ta = accent + i * 0.14;
    at(t => {
      let s = 1;
      if (t >= ta) s = t < ta + 0.07 ? mix(1, 1.08, prog(t, ta, 0.07, easeOut)) : mix(1.08, 1, POP(t - ta - 0.07));
      wi.style.transform = `scale(${s.toFixed(4)})`;
      if (mk) mk.style.transform = `scaleX(${prog(t, ta, 0.3, easeOut).toFixed(4)})`;
    });
  });
}

function rise(el, tIn, tOut = null, dy = 30) {
  at(t => {
    let y = dy, o = 0;
    if (t >= tIn) { y = mix(dy, 0, SLIDE(t - tIn)); o = prog(t, tIn, 0.25, easeOut); }
    if (tOut != null && t >= tOut) { const q = prog(t, tOut, 0.18, easeIn); y = mix(y, -30, q); o *= 1 - q; }
    el.style.transform = `translate3d(0, ${px(y)}, 0)`;
    el.style.opacity = o.toFixed(3);
  });
}

function tag(el, tIn) {
  at(t => {
    const p = TAG(t - tIn);
    el.style.opacity = prog(t, tIn, 0.12).toFixed(3);
    el.style.transform = `rotate(-6deg) scale(${mix(0.4, 1, p).toFixed(4)})`;
  });
}

// generated stickers fly in with a small turn (-6deg -> -3deg) and an ink shadow
function sticker(el, tIn, tOut, fromX, fromY) {
  at(t => {
    let x = fromX, y = fromY, r = -6, s = 0.9, o = 0;
    if (t >= tIn) {
      const p = FLY(t - tIn);
      x = mix(fromX, 0, p); y = mix(fromY, 0, p); r = mix(-6, -3, p); s = mix(0.9, 1, p);
      o = prog(t, tIn, 0.2, easeOut);
    }
    if (tOut != null && t >= tOut) {
      const q = prog(t, tOut, 0.18, easeIn);
      y += 60 * q; s *= 1 - 0.15 * q; o *= 1 - q;
    }
    el.style.transform = `translate3d(${px(x)}, ${px(y)}, 0) rotate(${r.toFixed(3)}deg) scale(${s.toFixed(4)})`;
    el.style.opacity = o.toFixed(3);
  });
}

// slow parallax of halftone and blob across one scene (20-40 px)
function drift(el, t0, t1, dx, dy) {
  at(t => {
    const p = clamp(0, 1, (t - t0) / (t1 - t0));
    el.style.transform = `translate3d(${px(dx * p)}, ${px(dy * p)}, 0)`;
  });
}

// green wave draws itself through stroke-dashoffset (path has pathLength="1")
function draw(svg, t0, d = 0.5) {
  const p = svg.querySelector('path');
  p.style.strokeDasharray = '1 1';
  at(t => { p.style.strokeDashoffset = (1 - prog(t, t0, d, easeOut)).toFixed(4); });
}

// scene change: a yellow stripe crosses left to right and reveals the next scene
const wipes = [];
function wipe(next, prev, t0) {
  wipes.push(t0);
  at(t => {
    const E = mix(-80, W + 80, prog(t, t0, WIPE, easeInOut));
    next.style.visibility = t < t0 ? 'hidden' : 'visible';
    next.style.clipPath = t < t0 + WIPE ? `inset(0 ${px(clamp(0, W, W - E))} 0 0)` : 'none';
    if (prev) prev.style.visibility = t >= t0 + WIPE ? 'hidden' : 'visible';
  });
}
function stripeTrack() {
  const st = $('stripe');
  at(t => {
    const t0 = wipes.find(w => t >= w && t < w + WIPE);
    if (t0 == null) { st.style.display = 'none'; return; }
    const E = mix(-80, W + 80, prog(t, t0, WIPE, easeInOut));
    st.style.display = 'block';
    st.style.left = px(E - 32);
  });
}

const fmt = n => (n >= 1000 ? Math.floor(n / 1000) + ' ' + String(n % 1000).padStart(3, '0') : String(n));

// ---------- setup ----------
async function setup() {
  await Promise.all([
    document.fonts.load('900 100px Unbounded', 'АБВ ABC 1'), document.fonts.load('700 100px Unbounded', 'АБВ'),
    document.fonts.load('400 40px Onest', 'абв abc'), document.fonts.load('500 40px Onest', 'абв abc'),
    document.fonts.load('700 40px Onest', 'абв abc'),
  ]);
  await document.fonts.ready;
  await Promise.all([...document.images].map(i => (i.complete ? null : new Promise(r => { i.onload = i.onerror = r; }))));

  const heads = ['coverHead', 'hook', 'h2a', 'h2b', 'h3a', 'h3b', 'h4'].map($);
  heads.forEach(buildHead);
  heads.forEach(h => fit(h));
  fit($('num'));
  heads.forEach(joinMarkers);
  const nb = $('numbox');
  nb.style.width = px(nb.getBoundingClientRect().width);

  document.querySelectorAll('[data-center]').forEach(el => { el.style.top = px(+el.dataset.center - el.offsetHeight / 2); });
  below($('coverSub'), $('coverHead'), 44);
  below($('h2b'), $('num'), 18);
  below($('field'), $('h4'), 70);

  // ----- scene 1: cover at t = 0, then the hook -----
  words($('coverHead'), { tIn: 0, skipIn: true, tOut: T.coverOut, stagger: 0.03 });
  at(t => {
    const q = prog(t, T.coverOut + 0.03, 0.18, easeIn);
    $('coverSub').style.transform = `translate3d(0, ${px(26 * q)}, 0)`;
    $('coverSub').style.opacity = (1 - q).toFixed(3);
    const r = prog(t, T.coverOut, 0.2, easeIn);
    $('play').style.transform = `scale(${mix(1, 0.4, r).toFixed(4)}) rotate(${mix(0, 20, r).toFixed(2)}deg)`;
    $('play').style.opacity = (1 - r).toFixed(3);
  });
  words($('hook'), { tIn: T.hookIn, accent: T.hookIn + 0.42 });
  drift($('ht1'), 0, T.wipe12 + WIPE, -30, 18);
  drift($('bl1'), 0, T.wipe12 + WIPE, 26, -20);
  if (VIDEO) {
    wipes.push(T.coverOut);
    at(t => {
      const E = mix(-80, W + 80, prog(t, T.coverOut, WIPE, easeInOut));
      $('deco1').style.clipPath = `inset(0 0 0 ${px(clamp(0, W, E))})`;
      $('footer1').style.color = t >= T.coverOut + WIPE ? 'var(--paper)' : '';
    });
  }

  // ----- scene 2: the case -----
  wipe($('sc2'), $('sc1'), T.wipe12);
  tag($('tag2'), T.s2aIn - 0.02);
  draw($('wv2'), T.s2aIn + 0.25);
  words($('h2a'), { tIn: T.s2aIn + 0.08, tOut: T.s2aOut, accent: T.s2aIn + 0.62 });
  sticker($('st-notebook'), T.s2aIn + 0.5, null, -160, 140);   // lessons stay on screen through the number
  sticker($('st-cards'), T.s2aIn + 0.68, null, 160, 140);
  rise($('lbl2b'), T.s2bIn);
  words($('num'), { tIn: T.s2bIn + 0.08, accent: T.countIn + T.countDur });
  at(t => {
    const p = prog(t, T.countIn, T.countDur, easeOut);
    const n = p >= 1 ? 1500 : Math.round((1500 * p) / 10) * 10;
    $('numval').textContent = fmt(n);
  });
  words($('h2b'), { tIn: T.s2bIn + 0.22, stagger: 0.06 });
  drift($('ht2'), T.wipe12, T.wipe23 + WIPE, -34, -16);

  // ----- scene 3: the opinion -----
  wipe($('sc3'), $('sc2'), T.wipe23);
  tag($('tag3'), T.s3aIn - 0.02);
  draw($('wv3'), T.s3aIn + 0.3);
  words($('h3a'), { tIn: T.s3aIn + 0.08, tOut: T.s3aOut, accent: T.s3aIn + 0.66 });
  sticker($('st-bubbles'), T.s3aIn + 0.5, T.s3aOut, 150, 150);
  words($('h3b'), { tIn: T.s3bIn + 0.04, accent: T.s3bIn + 0.52 });
  sticker($('st-laptop'), T.s3bIn + 0.42, null, -150, 150);
  drift($('ht3'), T.wipe23, T.wipe34 + WIPE, 32, -18);
  drift($('bl3'), T.wipe23, T.wipe34 + WIPE, -24, 22);

  // ----- scene 4: the call to action -----
  wipe($('sc4'), $('sc3'), T.wipe34);
  tag($('tag4'), T.s4In - 0.02);
  words($('h4'), { tIn: T.s4In + 0.08, accent: T.s4In + 0.48 });
  rise($('field'), T.s4In + 0.62, null, 60);
  const text = 'напиши цифру в коментарях';
  const typeEnd = T.typeIn + text.length * T.typeStep;
  at(t => {
    const n = clamp(0, text.length, Math.floor((t - T.typeIn) / T.typeStep) + 1);
    $('typed').textContent = t < T.typeIn ? '' : text.slice(0, n);
    const on = t < typeEnd && t >= T.typeIn ? true : Math.floor((t - (t < T.typeIn ? T.s4In : typeEnd)) / 0.45) % 2 === 0;
    $('caret').style.opacity = on ? '1' : '0';
  });
  sticker($('st-star'), T.s4In + 1.0, null, -140, 140);
  drift($('ht4'), T.wipe34, T.end, -30, -20);
  drift($('bl4'), T.wipe34, T.end, 24, 18);

  stripeTrack();
}

window.__T = T;
window.__seek = t => { window.__t = t; for (const f of tracks) f(t); };
window.__ready = setup().then(() => { window.__seek(0); return T.end; });
