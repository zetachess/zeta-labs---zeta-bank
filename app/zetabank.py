#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zetabank.py
===========
Laboratorio web (Easy) DELIBERADAMENTE vulnerable, solo para formación.

Eres el cliente "zeta" de ZetaBank. Objetivo: conseguir la flag.

Ejecución:
    python zetabank.py

Por defecto escucha solo en 127.0.0.1:8000 (variables HOST y PORT).
"""

import html
import json
import os
import secrets
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8000))

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DEL RETO
# ---------------------------------------------------------------------------
FLAG = os.environ.get("FLAG", "ZETA{v13w_s0urc3_y_t3_h4c3s_m1ll0n4r10}")
OBJETIVO = 1_000_000
ADMIN_USER, ADMIN_PASS = "admin", "admin"

# ---------------------------------------------------------------------------
# DATOS EN MEMORIA (se reinician al reiniciar el servidor)
# ---------------------------------------------------------------------------
def _dia(n):
    return (datetime.now() - timedelta(days=n)).strftime("%d %b")


def _datos_iniciales():
    # movs: (concepto, importe, fecha, icono)
    return {
        "ES2300491500051234567890": {"titular": "zeta", "nombre": "Zeta", "color": "#14b8a6", "saldo": 6464.00,
            "movs": [("Nómina · Zeta Empresa", 1850.00, _dia(9), "💼"), ("Alquiler casa", -730.00, _dia(8), "🏠"),
                     ("Compra supermercado", -67.87, _dia(4), "🛒"), ("GoblinAjedrez", -24.99, _dia(3), "♟️"),
                     ("Gasolinera", -40.00, _dia(1), "⛽")]},
        "ES7700494500123456789012": {"titular": "reserva", "nombre": "Fondo de reserva ZetaBank", "color": "#f59e0b",
            "saldo": 1_000_000.00,
            "movs": [("Aportación de capital", 1000000.00, _dia(30), "🏦")]},
        "ES6100810001230987654321": {"titular": "cris", "nombre": "Cris", "color": "#a855f7",
            "saldo": 3120.50, "movs": [("Nómina", 1700.00, _dia(4), "💼")]},
        "ES4500750000987654321098": {"titular": "mama", "nombre": "Mamá", "color": "#ec4899",
            "saldo": 5400.00, "movs": [("Pensión", 1200.00, _dia(5), "🏦")]},
        "ES9000300100112233445566": {"titular": "raul", "nombre": "Raúl", "color": "#3b82f6",
            "saldo": 1500.75, "movs": [("Freelance", 400.00, _dia(5), "💻")]},
        "ES1200491800221122334455": {"titular": "oliver", "nombre": "Oliver", "color": "#f97316",
            "saldo": 980.00, "movs": [("Bizum", 20.00, _dia(3), "💸")]},
    }


CUENTAS = _datos_iniciales()
USUARIOS = {"zeta": "Zeta123"}                       # usuario -> contraseña
IBAN_DE = {"zeta": "ES2300491500051234567890"}
CONTACTOS = ["ES6100810001230987654321", "ES4500750000987654321098",
             "ES9000300100112233445566", "ES1200491800221122334455"]   # Cris, Mamá, Raúl, Oliver
SESIONES = {}                                         # token -> usuario
SESIONES_ADMIN = set()


def norm_iban(s):
    return "".join(str(s).split()).upper()


def fmt_iban(s):
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def eur(x, signo=False):
    s = f"{abs(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    if signo:
        return ("+" if x >= 0 else "−") + s
    return ("−" if x < 0 else "") + s


def iniciales(nombre):
    p = nombre.split()
    return (p[0][0] + (p[1][0] if len(p) > 1 else "")).upper()


# ---------------------------------------------------------------------------
# ESTILO COMPARTIDO (app bancaria móvil)
# ---------------------------------------------------------------------------
SHARED_CSS = """
:root { color-scheme: dark; --bg:#0b0d12; --card:#151922; --card2:#1c2230; --line:#262d3d;
  --txt:#f1f3f8; --mut:#8a93a8; --acc:#2dd4bf; --acc2:#6366f1; --pos:#4ade80; --neg:#f87171; }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html,body { margin:0; min-height:100%; }
body { font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif; background:
  radial-gradient(900px 500px at 15% -10%,#14304a55,transparent),
  radial-gradient(800px 500px at 100% 0%,#3b1f6655,transparent), var(--bg);
  color:var(--txt); display:flex; justify-content:center; }
.app { width:100%; max-width:430px; min-height:100vh; padding:0 18px 96px; position:relative; }
.top { display:flex; align-items:center; justify-content:space-between; padding:20px 0 10px; }
.logo { display:flex; align-items:center; gap:10px; font-weight:800; letter-spacing:.2px; }
.logo i { width:34px; height:34px; border-radius:11px; display:grid; place-items:center; font-style:normal;
  background:linear-gradient(135deg,var(--acc),var(--acc2)); color:#04141a; font-size:19px; }
.avatar { width:40px; height:40px; border-radius:50%; display:grid; place-items:center; font-weight:700;
  font-size:14px; color:#fff; flex:none; }
.hello { color:var(--mut); font-size:14px; margin:6px 0 2px; }
.bal { text-align:center; margin:18px 0 22px; }
.bal small { color:var(--mut); font-size:13px; }
.bal h1 { font-size:2.9rem; margin:4px 0; font-weight:800; letter-spacing:-1px; }
.bal .iban { font-family:ui-monospace,monospace; color:var(--mut); font-size:12.5px; }
.pill { display:inline-block; background:var(--card2); border:1px solid var(--line); border-radius:99px;
  padding:6px 14px; font-size:12.5px; color:var(--mut); margin-top:8px; }
.actions { display:flex; justify-content:space-between; gap:10px; margin-bottom:22px; }
.act { flex:1; background:none; border:0; color:var(--txt); font:inherit; cursor:pointer; text-align:center; }
.act span { display:grid; place-items:center; width:54px; height:54px; margin:0 auto 7px; font-size:21px;
  border-radius:50%; background:var(--card2); border:1px solid var(--line); transition:.15s; }
.act:hover span { background:var(--acc); color:#04141a; transform:translateY(-2px); }
.act em { font-style:normal; font-size:12.5px; color:var(--mut); }
.card { background:var(--card); border:1px solid var(--line); border-radius:20px; padding:16px; margin-bottom:16px; }
.card h3 { margin:0 0 10px; font-size:15px; }
.card h3 a { float:right; font-weight:500; font-size:13px; color:var(--acc); text-decoration:none; cursor:pointer; }
.visa { border:0; padding:20px; color:#fff; min-height:150px; position:relative; overflow:hidden;
  background:linear-gradient(135deg,#0f766e 0%,#4f46e5 60%,#9333ea 100%); }
.visa::after { content:""; position:absolute; width:220px; height:220px; border-radius:50%; right:-60px; top:-70px;
  background:#ffffff18; }
.visa .chip { width:38px; height:28px; border-radius:6px; background:linear-gradient(135deg,#fde68a,#f59e0b); margin:14px 0; }
.visa .num { font-family:ui-monospace,monospace; letter-spacing:2px; opacity:.95; }
.visa .row { display:flex; justify-content:space-between; font-size:12px; opacity:.85; margin-top:10px; }
.mov { display:flex; align-items:center; gap:12px; padding:11px 0; border-bottom:1px solid var(--line); }
.mov:last-child { border:0; }
.mov .ic { width:42px; height:42px; border-radius:14px; background:var(--card2); display:grid; place-items:center; font-size:19px; flex:none; }
.mov .t { flex:1; min-width:0; } .mov .t b { display:block; font-weight:600; font-size:14.5px;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.mov .t small { color:var(--mut); font-size:12.5px; } .mov .v { font-weight:700; font-size:14.5px; }
.pos { color:var(--pos); } .neg { color:var(--txt); } .err { color:var(--neg); }
.contacts { display:flex; gap:14px; overflow-x:auto; padding:2px 0 8px; margin-bottom:6px; }
.ct { text-align:center; cursor:pointer; min-width:62px; background:none; border:0; color:var(--txt); font:inherit; }
.ct .avatar { margin:0 auto 6px; width:52px; height:52px; font-size:16px; border:2px solid transparent; }
.ct.sel .avatar { border-color:var(--acc); } .ct small { font-size:12px; color:var(--mut); }
label { display:block; font-size:12.5px; color:var(--mut); margin:12px 0 5px; }
input { width:100%; font:inherit; font-size:15px; padding:14px; border-radius:14px; border:1px solid var(--line);
  background:var(--card2); color:var(--txt); outline:none; }
input:focus { border-color:var(--acc); }
.big { font-size:2.2rem; text-align:center; font-weight:800; padding:18px; letter-spacing:-.5px; }
.btn { width:100%; margin-top:16px; padding:15px; border:0; border-radius:16px; font:inherit; font-weight:700;
  font-size:15.5px; background:linear-gradient(135deg,var(--acc),#38bdf8); color:#04141a; cursor:pointer; }
.btn:hover { filter:brightness(1.08); }
.msg { text-align:center; margin-top:12px; font-size:14px; min-height:20px; }
.flag { background:linear-gradient(135deg,#fbbf24,#f59e0b); color:#2a1700; border-radius:20px; padding:18px;
  text-align:center; margin-bottom:16px; font-weight:600; box-shadow:0 10px 40px #f59e0b44; }
.flag b { display:block; font-family:ui-monospace,monospace; font-size:15px; margin-top:6px; word-break:break-all; }
.tabbar { position:fixed; bottom:0; left:50%; transform:translateX(-50%); width:100%; max-width:430px;
  display:flex; background:#0e1118ee; backdrop-filter:blur(14px); border-top:1px solid var(--line); padding:8px 8px 14px; }
.tab { flex:1; text-align:center; background:none; border:0; color:var(--mut); font:inherit; font-size:11.5px; cursor:pointer; }
.tab span { display:block; font-size:21px; margin-bottom:2px; filter:grayscale(1) opacity(.7); }
.tab.on { color:var(--acc); } .tab.on span { filter:none; }
.view { display:none; animation:f .25s ease; } .view.on { display:block; }
@keyframes f { from { opacity:0; transform:translateY(6px);} to { opacity:1; transform:none;} }
.login { min-height:100vh; display:flex; flex-direction:column; justify-content:center; }
.login h1 { font-size:2rem; margin:22px 0 4px; letter-spacing:-.5px; }
.login p { color:var(--mut); margin:0 0 22px; }
.demo { background:var(--card2); border:1px dashed var(--line); border-radius:14px; padding:12px 14px;
  font-size:13px; color:var(--mut); margin-top:16px; } .demo b { color:var(--txt); }
.ok { display:grid; place-items:center; width:84px; height:84px; margin:10px auto; border-radius:50%;
  background:#14532d; font-size:40px; }
"""


def page_shell(title, body_html, script=""):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b0d12">
<title>{title}</title>
<style>{SHARED_CSS}</style>
</head>
<body>
{body_html}
<script>{script}</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# PÁGINAS
# ---------------------------------------------------------------------------
def login_body(error=""):
    err = f'<div class="msg err">{html.escape(error)}</div>' if error else ""
    return f"""<div class="app login">
  <div class="logo"><i>Z</i> ZetaBank</div>
  <h1>Tu dinero fácil,<br>tu inversión fácil.</h1>
  <p>Accede a tu banco.</p>
  <form method="POST" action="/login">
    <label>Usuario</label><input name="usuario" placeholder="Usuario" autocomplete="off">
    <label>Contraseña</label><input name="clave" type="password" placeholder="••••••••">
    <button class="btn" type="submit">Entrar</button>
  </form>
  {err}
  <div class="demo">Cuenta de acceso → usuario <b>zeta</b> · contraseña <b>Zeta123</b></div>
</div>"""


def _mov_html(m):
    concepto, v, fecha, ic = m
    return (f'<div class="mov"><div class="ic">{ic}</div>'
            f'<div class="t"><b>{html.escape(concepto)}</b><small>{fecha}</small></div>'
            f'<div class="v {"pos" if v >= 0 else "neg"}">{eur(v, True)}</div></div>')


def cuenta_body(usuario):
    iban = IBAN_DE[usuario]
    c = CUENTAS[iban]
    recientes = "".join(_mov_html(m) for m in reversed(c["movs"][-4:]))
    todos = "".join(_mov_html(m) for m in reversed(c["movs"]))
    flag = (f'<div class="flag">🏆 ¡Eres millonario! Reto completado<b>{FLAG}</b></div>'
            if c["saldo"] >= OBJETIVO else "")
    contactos = "".join(
        f'<button type="button" class="ct" data-iban="{i}"><div class="avatar" style="background:{CUENTAS[i]["color"]}">'
        f'{iniciales(CUENTAS[i]["nombre"])}</div><small>{html.escape(CUENTAS[i]["nombre"].split()[0])}</small></button>'
        for i in CONTACTOS)
    return f"""<div class="app">
  <!--
     TODO (Dani): quitar esto antes de salir a producción.
     Ruta para desarrolladores: /admin
  -->
  <div class="top">
    <div class="logo"><i>Z</i> ZetaBank</div>
    <a href="/logout" style="text-decoration:none"><div class="avatar" style="background:{c["color"]}">{iniciales(c["nombre"])}</div></a>
  </div>

  <!-- ============ INICIO ============ -->
  <section class="view on" id="v-inicio">
    {flag}
    <div class="hello">Hola, {html.escape(c["nombre"])} 👋</div>
    <div class="bal">
      <small>Saldo total</small>
      <h1>{eur(c["saldo"])}</h1>
      <div class="iban">{fmt_iban(iban)}</div>
      <span class="pill">Cuenta corriente · EUR</span>
    </div>
    <div class="actions">
      <button class="act" data-go="enviar"><span>↗</span><em>Enviar</em></button>
      <button class="act" data-go="enviar"><span>＋</span><em>Añadir</em></button>
      <button class="act" data-go="movs"><span>☰</span><em>Detalles</em></button>
      <button class="act" data-go="tarjeta"><span>▭</span><em>Tarjeta</em></button>
    </div>
    <div class="card"><h3>Movimientos recientes <a data-go="movs">Ver todos</a></h3>{recientes}</div>
  </section>

  <!-- ============ ENVIAR ============ -->
  <section class="view" id="v-enviar">
    <h2 style="margin:8px 0 14px">Enviar dinero</h2>
    <div class="card">
      <h3>Contactos frecuentes</h3>
      <div class="contacts">{contactos}</div>
      <form id="tf">
        <label>IBAN de destino</label>
        <input name="destino" id="destino" placeholder="ES00 0000 0000 0000 0000 0000">
        <label>Importe</label>
        <input class="big" name="importe" placeholder="0,00 €" inputmode="decimal" autocomplete="off">
        <button class="btn" type="submit">Enviar ahora</button>
      </form>
      <div id="res" class="msg"></div>
    </div>
  </section>

  <!-- ============ MOVIMIENTOS ============ -->
  <section class="view" id="v-movs">
    <h2 style="margin:8px 0 14px">Movimientos</h2>
    <div class="card">{todos}</div>
  </section>

  <!-- ============ TARJETA ============ -->
  <section class="view" id="v-tarjeta">
    <h2 style="margin:8px 0 14px">Mi tarjeta</h2>
    <div class="card visa">
      <b>ZetaBank</b> <span style="float:right">VISA</span>
      <div class="chip"></div>
      <div class="num">4532 •••• •••• 6464</div>
      <div class="row"><span>{html.escape(c["nombre"]).upper()}</span><span>12/29</span></div>
    </div>
    <div class="card"><h3>Tu cuenta</h3>
      <div class="mov"><div class="ic">🏦</div><div class="t"><b>IBAN</b><small>{fmt_iban(iban)}</small></div></div>
      <div class="mov"><div class="ic">🔒</div><div class="t"><b>Pagos online</b><small>Activados</small></div></div>
    </div>
  </section>

  <nav class="tabbar">
    <button class="tab on" data-go="inicio"><span>🏠</span>Inicio</button>
    <button class="tab" data-go="enviar"><span>💸</span>Enviar</button>
    <button class="tab" data-go="movs"><span>📊</span>Movimientos</button>
    <button class="tab" data-go="tarjeta"><span>💳</span>Tarjeta</button>
  </nav>
</div>"""


CUENTA_JS = """
function ir(n) {
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + n));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.go === n));
  window.scrollTo({top: 0, behavior: 'smooth'});
}
document.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => ir(b.dataset.go)));
document.querySelectorAll('.ct').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.ct').forEach(x => x.classList.remove('sel'));
  b.classList.add('sel');
  document.getElementById('destino').value = b.dataset.iban;
}));
document.getElementById('tf').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const f = new FormData(ev.target);
  const r = await fetch('/api/transfer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(Object.fromEntries(f))
  }).then(r => r.json());
  const res = document.getElementById('res');
  res.className = 'msg ' + (r.ok ? 'pos' : 'err');
  res.textContent = (r.ok ? '✓ ' : '') + r.msg;
  if (r.ok) setTimeout(() => location.reload(), 1100);
});
"""


# ---------------------------------------------------------------------------
# LÓGICA DE TRANSFERENCIAS
# ---------------------------------------------------------------------------
def _mover(origen, destino, importe):
    hoy = datetime.now().strftime("%d %b")
    CUENTAS[origen]["saldo"] -= importe
    CUENTAS[destino]["saldo"] += importe
    CUENTAS[origen]["movs"].append((f"Transferencia a {CUENTAS[destino]['nombre']}", -importe, hoy, "↗️"))
    CUENTAS[destino]["movs"].append((f"Transferencia de {CUENTAS[origen]['nombre']}", importe, hoy, "↙️"))


def _importe(valor):
    try:
        return round(float(str(valor).replace("€", "").replace(",", ".")), 2)
    except ValueError:
        return None


def hacer_transferencia(usuario, datos):
    origen = IBAN_DE[usuario]
    destino = norm_iban(datos.get("destino", ""))
    importe = _importe(datos.get("importe", ""))
    if importe is None or importe <= 0:
        return False, "Importe no válido."
    if destino not in CUENTAS:
        return False, "Cuenta de destino no encontrada."
    if origen == destino:
        return False, "Origen y destino son la misma cuenta."
    if CUENTAS[origen]["saldo"] < importe:
        return False, "Saldo insuficiente."
    _mover(origen, destino, importe)
    return True, f"Enviados {eur(importe)} correctamente."


RESERVA_IBAN = "ES7700494500123456789012"


def admin_transferencia(datos):
    destino = norm_iban(datos.get("destino", ""))
    importe = _importe(datos.get("importe", ""))
    if importe is None or importe <= 0:
        return False, "Importe no válido."
    if destino not in CUENTAS or destino == RESERVA_IBAN:
        return False, "Cuenta de destino no encontrada."
    if CUENTAS[RESERVA_IBAN]["saldo"] < importe:
        return False, "El fondo de reserva no tiene saldo suficiente."
    _mover(RESERVA_IBAN, destino, importe)
    return True, f"Transferencia ejecutada: {eur(importe)} enviados."


# ---------------------------------------------------------------------------
# PANEL DE ADMINISTRACIÓN
# ---------------------------------------------------------------------------
def admin_login_body(error=""):
    err = f'<div class="msg err">{html.escape(error)}</div>' if error else ""
    return f"""<div class="app login">
  <div class="logo"><i>Z</i> ZetaBank · Admin</div>
  <h1>Panel de administración</h1>
  <p>Acceso restringido al personal del banco.</p>
  <form method="POST" action="/admin/login">
    <label>Usuario</label><input name="usuario" autocomplete="off">
    <label>Contraseña</label><input name="clave" type="password">
    <button class="btn" type="submit">Acceder</button>
  </form>
  {err}
</div>"""


def admin_body():
    r = CUENTAS[RESERVA_IBAN]
    filas = "".join(
        f'<div class="mov"><div class="avatar" style="background:{c["color"]}">{iniciales(c["nombre"])}</div>'
        f'<div class="t"><b>{html.escape(c["nombre"])}</b><small>{fmt_iban(i)}</small></div>'
        f'<div class="v">{eur(c["saldo"])}</div></div>'
        for i, c in CUENTAS.items() if i != RESERVA_IBAN)
    return f"""<div class="app">
  <div class="top"><div class="logo"><i>Z</i> Admin</div><a href="/admin/logout" style="color:#2dd4bf;text-decoration:none;font-size:14px">Salir</a></div>
  <div class="card balance" style="background:linear-gradient(135deg,#b45309,#f59e0b);border:0">
    <div class="label" style="opacity:.85;font-size:13px">Fondo de reserva del banco</div>
    <div class="amount" style="font-size:2.4rem;font-weight:800">{eur(r["saldo"])}</div>
    <div class="iban" style="font-family:monospace;opacity:.9;font-size:12.5px">{fmt_iban(RESERVA_IBAN)}</div>
  </div>
  <div class="card">
    <h3>Transferir desde el fondo</h3>
    <form id="af">
      <label>IBAN de destino</label>
      <input name="destino" id="destino" placeholder="ES00 0000 0000 0000 0000 0000">
      <label>Importe</label>
      <input name="importe" value="1000000" inputmode="decimal">
      <button class="btn" type="submit">Ejecutar transferencia</button>
    </form>
    <div id="res" class="msg"></div>
  </div>
  <div class="card"><h3>Clientes</h3>{filas}</div>
</div>"""


ADMIN_JS = """
document.getElementById('af').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const f = new FormData(ev.target);
  const r = await fetch('/api/admin/transfer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(Object.fromEntries(f))
  }).then(r => r.json());
  const res = document.getElementById('res');
  res.className = 'msg ' + (r.ok ? 'pos' : 'err');
  res.textContent = (r.ok ? '✓ ' : '') + r.msg;
  if (r.ok) setTimeout(() => location.reload(), 1200);
});
"""


# ---------------------------------------------------------------------------
# SERVIDOR HTTP
# ---------------------------------------------------------------------------
class LabHandler(BaseHTTPRequestHandler):
    server_version = "ZetaBankLab/1.0"

    # --- Utilidades de respuesta -----------------------------------------
    def _send(self, status, content_type, body_bytes, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body_bytes)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body_bytes)

    def _send_html(self, status, html_str, headers=None):
        self._send(status, "text/html; charset=utf-8", html_str.encode("utf-8"), headers)

    def _send_json(self, status, data):
        self._send(status, "application/json", json.dumps(data).encode("utf-8"))

    def _redirect(self, to, headers=None):
        h = {"Location": to}
        h.update(headers or {})
        self._send(302, "text/plain", b"", h)

    def _es_admin(self):
        c = SimpleCookie(self.headers.get("Cookie", ""))
        return ("asid" in c) and c["asid"].value in SESIONES_ADMIN

    def _usuario(self):
        c = SimpleCookie(self.headers.get("Cookie", ""))
        tok = c["sid"].value if "sid" in c else ""
        return SESIONES.get(tok)

    # --- Enrutado GET ------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        user = self._usuario()

        if path == "/health":
            self._send_json(200, {"status": "ok", "scope": "localhost-only"})
            return

        if path == "/":
            self._redirect("/cuenta" if user else "/login")
            return

        if path == "/login":
            self._send_html(200, page_shell("ZetaBank · Acceso", login_body()))
            return

        if path == "/cuenta":
            if not user:
                self._redirect("/login")
                return
            self._send_html(200, page_shell("ZetaBank", cuenta_body(user), CUENTA_JS))
            return

        if path == "/admin":
            if self._es_admin():
                self._send_html(200, page_shell("ZetaBank · Admin", admin_body(), ADMIN_JS))
            else:
                self._send_html(200, page_shell("ZetaBank · Admin", admin_login_body()))
            return

        if path == "/admin/logout":
            self._redirect("/admin", {"Set-Cookie": "asid=; Max-Age=0; Path=/"})
            return

        if path == "/logout":
            self._redirect("/login", {"Set-Cookie": "sid=; Max-Age=0; Path=/"})
            return

        self._send_html(404, page_shell("ZetaBank · No encontrado",
                        "<div class='app login'><h1>404</h1><p>Recurso no encontrado.</p></div>"))

    # --- Enrutado POST -------------------------------------------------
    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""

        if path == "/login":
            d = parse_qs(raw.decode("utf-8", "replace"))
            u = d.get("usuario", [""])[0].strip()
            p = d.get("clave", [""])[0]
            if USUARIOS.get(u) == p and p:
                tok = secrets.token_hex(16)
                SESIONES[tok] = u
                self._redirect("/cuenta", {"Set-Cookie": f"sid={tok}; Path=/; HttpOnly"})
            else:
                self._send_html(401, page_shell("ZetaBank · Acceso", login_body("Usuario o contraseña incorrectos.")))
            return

        if path == "/api/transfer":
            user = self._usuario()
            if not user:
                self._send_json(401, {"ok": False, "msg": "Sesión no válida."})
                return
            try:
                datos = json.loads(raw or b"{}")
            except ValueError:
                datos = {}
            ok, msg = hacer_transferencia(user, datos)
            self._send_json(200 if ok else 400, {"ok": ok, "msg": msg})
            return

        if path == "/admin/login":
            d = parse_qs(raw.decode("utf-8", "replace"))
            if d.get("usuario", [""])[0] == ADMIN_USER and d.get("clave", [""])[0] == ADMIN_PASS:
                tok = secrets.token_hex(16)
                SESIONES_ADMIN.add(tok)
                self._redirect("/admin", {"Set-Cookie": f"asid={tok}; Path=/; HttpOnly"})
            else:
                self._send_html(401, page_shell("ZetaBank · Admin", admin_login_body("Credenciales incorrectas.")))
            return

        if path == "/api/admin/transfer":
            if not self._es_admin():
                self._send_json(401, {"ok": False, "msg": "Acceso denegado."})
                return
            try:
                datos = json.loads(raw or b"{}")
            except ValueError:
                datos = {}
            ok, msg = admin_transferencia(datos)
            self._send_json(200 if ok else 400, {"ok": ok, "msg": msg})
            return

        self._send_json(404, {"ok": False, "msg": "No encontrado."})

    # Log mínimo: sin verbosidad adicional.
    def log_message(self, fmt, *args):
        pass


def main():
    server = ThreadingHTTPServer((HOST, PORT), LabHandler)
    print("=" * 60)
    print(" ZetaBank Lab — Easy / Web")
    print(f" http://localhost:{PORT}/")
    print(" Usuario: zeta  ·  Contraseña: Zeta123")
    print(" Objetivo: conseguir la flag.")
    print("Hint: no te quedes solo con lo que se ve en pantalla.")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Deteniendo servidor.")
        server.shutdown()


if __name__ == "__main__":
    main()
