/* login.js — Auth + ciclo emocional del fondo */

const API = "http://localhost:8000";

// ── Ciclo emocional ──────────────────────────────────────────
const EMOCIONES = [
  { name:"calma",      ify:"#7dc86a", ifySh:"0 0 18px rgba(125,200,106,0.65)",
    bgA:"radial-gradient(ellipse at 20% 55%,rgba(20,90,40,0.55) 0%,transparent 50%),radial-gradient(ellipse at 80% 20%,rgba(10,60,80,0.4) 0%,transparent 45%),#060d09",
    tabBg:"rgba(15,40,15,0.85)",tabBd:"rgba(80,200,120,0.3)",tabSh:"0 0 18px rgba(80,200,120,0.2),0 0 1px rgba(120,220,100,0.35) inset",tabC:"#a8e890",
    btnBd:"rgba(80,200,120,0.3)",btnSh:"0 0 22px rgba(80,200,120,0.18),0 0 1px rgba(120,220,100,0.3) inset",btnC:"#b0e898",
    dotBg:"#7dc86a",dotSh:"0 0 6px rgba(125,200,106,0.6)",div:"linear-gradient(to bottom,transparent,rgba(80,200,120,0.2),transparent)" },
  { name:"frustración",ify:"#ff6b5b", ifySh:"0 0 18px rgba(255,107,91,0.65)",
    bgA:"radial-gradient(ellipse at 25% 50%,rgba(140,30,20,0.55) 0%,transparent 48%),radial-gradient(ellipse at 75% 25%,rgba(100,20,10,0.45) 0%,transparent 42%),#0d0605",
    tabBg:"rgba(40,10,8,0.85)",tabBd:"rgba(220,80,60,0.35)",tabSh:"0 0 18px rgba(220,80,60,0.22),0 0 1px rgba(255,100,80,0.4) inset",tabC:"#ffaa98",
    btnBd:"rgba(220,80,60,0.35)",btnSh:"0 0 22px rgba(220,80,60,0.2),0 0 1px rgba(255,100,80,0.35) inset",btnC:"#ffb8a8",
    dotBg:"#ff6b5b",dotSh:"0 0 6px rgba(255,107,91,0.6)",div:"linear-gradient(to bottom,transparent,rgba(220,80,60,0.2),transparent)" },
  { name:"paz",        ify:"#6ab4ff", ifySh:"0 0 18px rgba(106,180,255,0.65)",
    bgA:"radial-gradient(ellipse at 15% 55%,rgba(20,60,140,0.5) 0%,transparent 50%),radial-gradient(ellipse at 80% 20%,rgba(10,40,100,0.45) 0%,transparent 42%),#060810",
    tabBg:"rgba(10,20,45,0.85)",tabBd:"rgba(80,150,255,0.3)",tabSh:"0 0 18px rgba(80,150,255,0.2),0 0 1px rgba(120,180,255,0.35) inset",tabC:"#a8ccff",
    btnBd:"rgba(80,150,255,0.3)",btnSh:"0 0 22px rgba(80,150,255,0.18),0 0 1px rgba(120,180,255,0.3) inset",btnC:"#b0d4ff",
    dotBg:"#6ab4ff",dotSh:"0 0 6px rgba(106,180,255,0.6)",div:"linear-gradient(to bottom,transparent,rgba(80,150,255,0.2),transparent)" },
  { name:"urgencia",   ify:"#ffb830", ifySh:"0 0 18px rgba(255,184,48,0.65)",
    bgA:"radial-gradient(ellipse at 20% 50%,rgba(120,70,10,0.55) 0%,transparent 48%),radial-gradient(ellipse at 78% 22%,rgba(90,50,5,0.45) 0%,transparent 42%),#0d0a04",
    tabBg:"rgba(35,22,5,0.85)",tabBd:"rgba(220,160,40,0.32)",tabSh:"0 0 18px rgba(220,160,40,0.2),0 0 1px rgba(255,190,60,0.35) inset",tabC:"#ffd888",
    btnBd:"rgba(220,160,40,0.32)",btnSh:"0 0 22px rgba(220,160,40,0.18),0 0 1px rgba(255,190,60,0.3) inset",btnC:"#ffe0a0",
    dotBg:"#ffb830",dotSh:"0 0 6px rgba(255,184,48,0.6)",div:"linear-gradient(to bottom,transparent,rgba(220,160,40,0.2),transparent)" },
  { name:"melancolía", ify:"#b08aff", ifySh:"0 0 18px rgba(176,138,255,0.65)",
    bgA:"radial-gradient(ellipse at 18% 55%,rgba(70,30,130,0.55) 0%,transparent 50%),radial-gradient(ellipse at 78% 22%,rgba(50,20,100,0.45) 0%,transparent 42%),#07050e",
    tabBg:"rgba(22,12,42,0.85)",tabBd:"rgba(130,80,255,0.3)",tabSh:"0 0 18px rgba(130,80,255,0.2),0 0 1px rgba(170,120,255,0.35) inset",tabC:"#d0b8ff",
    btnBd:"rgba(130,80,255,0.3)",btnSh:"0 0 22px rgba(130,80,255,0.18),0 0 1px rgba(170,120,255,0.3) inset",btnC:"#d4b8ff",
    dotBg:"#b08aff",dotSh:"0 0 6px rgba(176,138,255,0.6)",div:"linear-gradient(to bottom,transparent,rgba(130,80,255,0.2),transparent)" },
  { name:"positivismo", ify:"#40e0c0",ifySh:"0 0 18px rgba(64,224,192,0.65)",
    bgA:"radial-gradient(ellipse at 20% 55%,rgba(15,100,80,0.5) 0%,transparent 50%),radial-gradient(ellipse at 78% 22%,rgba(10,70,60,0.4) 0%,transparent 42%),#050d0b",
    tabBg:"rgba(8,30,25,0.85)",tabBd:"rgba(40,200,170,0.3)",tabSh:"0 0 18px rgba(40,200,170,0.2),0 0 1px rgba(80,230,200,0.35) inset",tabC:"#90e8d8",
    btnBd:"rgba(40,200,170,0.3)",btnSh:"0 0 22px rgba(40,200,170,0.18),0 0 1px rgba(80,230,200,0.3) inset",btnC:"#a0eede",
    dotBg:"#40e0c0",dotSh:"0 0 6px rgba(64,224,192,0.6)",div:"linear-gradient(to bottom,transparent,rgba(40,200,170,0.2),transparent)" },
];

let cur = 0, activeTab = 0, transitioning = false;
const bglA = document.getElementById('login-bgl-a');
const bglB = document.getElementById('login-bgl-b');

function applyAccent(e, spd) {
  const s = spd || '3.5s';
  const tr = `color ${s} ease, text-shadow ${s} ease`;
  const ify    = document.getElementById('login-ify');
  const h1acc  = document.getElementById('login-h1acc');
  const emolbl = document.getElementById('login-emolabel');
  const divider= document.getElementById('login-divider');
  if (ify)    { ify.style.transition = tr; ify.style.color = e.ify; ify.style.textShadow = e.ifySh; }
  if (h1acc)  { h1acc.style.transition = `color ${s} ease`; h1acc.style.color = e.ify; }
  if (emolbl) { emolbl.style.transition = `color ${s} ease`; emolbl.style.color = e.ify; emolbl.textContent = e.name; }
  if (divider){ divider.style.transition = `background ${s} ease`; divider.style.background = e.div; }
  ['login-d1','login-d2','login-d3','login-d4'].forEach(id => {
    const d = document.getElementById(id);
    if (d) { d.style.transition = `background ${s} ease, box-shadow ${s} ease`; d.style.background = e.dotBg; d.style.boxShadow = e.dotSh; }
  });
  ['btn-login','btn-registro'].forEach(id => {
    const b = document.getElementById(id);
    if (b) { b.style.transition = `border-color ${s} ease, box-shadow ${s} ease, color ${s} ease`; b.style.border = `1px solid ${e.btnBd}`; b.style.boxShadow = e.btnSh; b.style.color = e.btnC; }
  });
  const tabs = document.querySelectorAll('.login-tab-btn');
  if (tabs.length) {
    const ton  = tabs[activeTab];
    const toff = tabs[activeTab === 0 ? 1 : 0];
    ton.style.cssText  += `; background:${e.tabBg}; border:1px solid ${e.tabBd}; box-shadow:${e.tabSh}; color:${e.tabC}`;
    toff.style.cssText += `; background:transparent; border:none; box-shadow:none; color:rgba(255,255,255,0.18)`;
  }
}

function crossfadeBg(fromE, toE) {
  if (transitioning) return;
  transitioning = true;
  if (!bglA || !bglB) { transitioning = false; return; }
  bglA.style.background = fromE.bgA; bglA.style.opacity = '1';
  bglB.style.background = toE.bgA;  bglB.style.opacity = '0';
  requestAnimationFrame(() => requestAnimationFrame(() => {
    bglA.style.transition = 'opacity 4s ease'; bglB.style.transition = 'opacity 4s ease';
    bglA.style.opacity = '0'; bglB.style.opacity = '1';
    setTimeout(() => {
      bglA.style.background = toE.bgA; bglA.style.opacity = '1';
      bglA.style.transition = 'none';  bglB.style.opacity = '0'; bglB.style.transition = 'none';
      transitioning = false;
    }, 4200);
  }));
}

// Generar estrellas
(function() {
  const sc = document.getElementById('login-stars');
  if (!sc) return;
  const styleEl = document.createElement('style');
  styleEl.textContent = '@keyframes login-twinkle{0%,100%{opacity:var(--mn,0.08);}50%{opacity:var(--mx,0.5);}}';
  document.head.appendChild(styleEl);
  for (let i = 0; i < 90; i++) {
    const s = document.createElement('div');
    const sz = [1, 1.5, 2][i % 3];
    const ds = ['2.5s','3.5s','4s'][i % 3];
    const mn = [0.05, 0.1, 0.15][i % 3];
    const mx = [0.35, 0.5, 0.65][i % 3];
    s.style.cssText = `position:absolute;border-radius:50%;background:#fff;width:${sz}px;height:${sz}px;top:${Math.random()*100}%;left:${Math.random()*100}%;animation:login-twinkle ${ds} ease-in-out infinite ${(Math.random()*5).toFixed(1)}s;--mn:${mn};--mx:${mx};`;
    sc.appendChild(s);
  }
})();

// Init + ciclo automático
if (bglA) bglA.style.background = EMOCIONES[0].bgA;
setTimeout(() => applyAccent(EMOCIONES[0], '0s'), 300);
setInterval(() => {
  const from = EMOCIONES[cur];
  cur = (cur + 1) % EMOCIONES.length;
  crossfadeBg(from, EMOCIONES[cur]);
  applyAccent(EMOCIONES[cur], '3.5s');
}, 6000);

// ── Switch tabs ──────────────────────────────────────────────
function switchTab(tab) {
  activeTab = tab === 'login' ? 0 : 1;
  applyAccent(EMOCIONES[cur], '0.25s');

  document.querySelectorAll('.login-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.login-tab-btn').forEach(b => b.classList.remove('active'));

  document.getElementById(`panel-${tab}`).classList.add('active');
  document.getElementById(`tab-${tab}-btn`).classList.add('active');

  const sub = document.getElementById('login-card-sub');
  if (sub) sub.textContent = tab === 'login' ? 'Accede a tu cuenta para continuar.' : 'Crea tu cuenta gratuitamente.';

  clearMsg();
}

// ── Mensajes ─────────────────────────────────────────────────
function showMsg(id, text, ok) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = `login-msg visible ${ok ? 'login-msg-ok' : 'login-msg-err'}`;
}
function clearMsg() {
  document.querySelectorAll('.login-msg').forEach(el => { el.textContent = ''; el.className = 'login-msg'; });
}

// ── Guard: evita doble submit ─────────────────────────────────
let _loginPending    = false;
let _registroPending = false;

// ── Login ─────────────────────────────────────────────────────────
async function doLogin() {
  if (_loginPending) return;
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-pass').value;
  const btn      = document.getElementById('btn-login');
  if (!email || !password) { showMsg('msg-login', 'Completa todos los campos.', false); return; }

  _loginPending = true;
  btn.textContent = 'Entrando…'; btn.disabled = true;
  clearMsg();

  try {
    const res = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    let data;
    try { data = await res.json(); } catch { throw new Error('PARSE_ERROR'); }

    if (!res.ok) {
      showMsg('msg-login', data.detail || 'Correo o contraseña incorrectos.', false);
      return;
    }

    document.getElementById('login-email').value = '';
    document.getElementById('login-pass').value  = '';

    localStorage.setItem('moodify_token',    data.token);
    localStorage.setItem('moodify_username', data.username);
    showMsg('msg-login', 'Bienvenido. Cargando...', true);

    setTimeout(() => { window.location.href = '/app'; }, 400);

  } catch (e) {
    if (e.message === 'PARSE_ERROR') {
      showMsg('msg-login', 'Respuesta inesperada del servidor. Intenta de nuevo.', false);
    } else if (e.name === 'TypeError' && e.message.includes('fetch')) {
      showMsg('msg-login', 'No se pudo conectar al servidor.', false);
    } else {
      showMsg('msg-login', 'Error de conexión. Verifica que el servidor esté activo.', false);
    }
    console.error('[login] Error:', e);
  } finally {
    btn.textContent = 'Iniciar sesión'; btn.disabled = false;
    _loginPending = false;
  }
}

// ── Registro ──────────────────────────────────────────────────
async function doRegistro() {
  if (_registroPending) return;
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-pass').value;
  const btn      = document.getElementById('btn-registro');

  if (!username || !email || !password) {
    showMsg('msg-registro', 'Completa todos los campos.', false);
    return;
  }

  _registroPending = true;
  btn.textContent = 'Creando cuenta…'; btn.disabled = true;
  clearMsg();

  try {
    const res = await fetch(`${API}/api/auth/registro`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username }),
    });

    let data;
    try { data = await res.json(); } catch { throw new Error('PARSE_ERROR'); }

    if (!res.ok) {
      showMsg('msg-registro', data.detail || 'No se pudo crear la cuenta.', false);
      return;
    }

    document.getElementById('reg-username').value = '';
    document.getElementById('reg-email').value    = '';
    document.getElementById('reg-pass').value     = '';

    showMsg('msg-registro', 'Cuenta creada. Inicia sesión.', true);

    setTimeout(() => {
      switchTab('login');
      const loginEmail = document.getElementById('login-email');
      if (loginEmail) loginEmail.value = email;
    }, 1400);

  } catch (e) {
    if (e.message === 'PARSE_ERROR') {
      showMsg('msg-registro', 'Respuesta inesperada del servidor. Intenta de nuevo.', false);
    } else {
      showMsg('msg-registro', 'Error de conexión. Verifica que el servidor esté activo.', false);
    }
    console.error('[registro] Error:', e);
  } finally {
    btn.textContent = 'Crear cuenta'; btn.disabled = false;
    _registroPending = false;
  }
}