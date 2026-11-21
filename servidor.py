import machine
import time
import network
import socket
import json
from machine import Pin
from neopixel import NeoPixel

from Barra1 import Barra16
from Motores import Motores

machine.freq(240000000)

# --- HARDWARE ---
neo = NeoPixel(Pin(21, Pin.OUT), 1)
sb = Barra16(5, 4, 3, 2, 1)
drv = Motores(8, 9, 10, 13, 12, 11)
drv.setVelocidad(0, 0)

btn_calibrar = Pin(6, Pin.IN, Pin.PULL_UP)
btn_inicio = Pin(7, Pin.IN, Pin.PULL_UP)

# --- CONSTANTES PID ---
SENSOR_RANGE = 255
U_MAX = 1023.0
I_MAX = 200.0
E_I_ON = 80.0
FC_D = 25.0
TAU_D = 1.0 / (6.2831853 * FC_D)
DEBOUNCE_MS = 50
CONFIG_FILE = "config.json"

# Valores por defecto
cfg = {
    "kp": 2.4,
    "ki": 0.4,
    "kd": 0.08,
    "vm": 300,
    "kf": 0.6,
    "kb": 0.8
}


def cargar_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            for k in cfg:
                if k in data:
                    cfg[k] = data[k]
    except Exception:
        pass


def guardar_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
        return True
    except Exception:
        return False


class Boton:
    def __init__(self, pin):
        self.pin = pin
        self._raw_anterior = pin.value()
        self._estado_estable = self._raw_anterior
        self._cambio_ms = time.ticks_ms()

    def presionado(self):
        raw = self.pin.value()
        ahora = time.ticks_ms()
        if raw != self._raw_anterior:
            self._raw_anterior = raw
            self._cambio_ms = ahora
        if (raw != self._estado_estable and
                time.ticks_diff(ahora, self._cambio_ms) >= DEBOUNCE_MS):
            self._estado_estable = raw
            return self._estado_estable == 1
        return False


def indicar_color(color):
    neo.fill(color)
    neo.write()


# --- INTERFAZ WEB MÓVIL ---
HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>PID Seguidor ESP32</title>
<style>
  *{box-sizing:border-box;font-family:system-ui,-apple-system,sans-serif}
  body{margin:0;padding:14px;background:#0f172a;color:#f8fafc}
  h2{margin:0 0 10px;font-size:1.2rem;text-align:center;color:#38bdf8}
  .status{text-align:center;padding:8px;border-radius:8px;margin-bottom:12px;font-weight:700;background:#1e293b}
  .card{background:#1e293b;padding:12px;border-radius:12px;margin-bottom:10px}
  .row{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
  label{font-weight:700;font-size:0.95rem}
  span.desc{font-size:0.75rem;color:#94a3b8;display:block}
  input[type=number]{width:82px;padding:6px;border-radius:6px;border:1px solid #475569;background:#0f172a;color:#38bdf8;font-weight:700;font-size:1rem;text-align:right}
  input[type=range]{width:100%;accent-color:#38bdf8;height:28px}
  .btns{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
  button{padding:12px;border:none;border-radius:10px;font-weight:700;font-size:0.95rem;cursor:pointer;color:#fff}
  .b-cal{background:#d97706}
  .b-run{background:#16a34a}
  .b-stop{background:#dc2626}
  .b-save{background:#2563eb;grid-column:span 2}
  button:active{opacity:0.8}
</style>
</head>
<body>
<h2>Control PID - Seguidor 3000 RPM</h2>
<div id="st" class="status">Conectando...</div>

<div class="card">
  <div class="row"><div><label>VM (Velocidad Base)</label><span class="desc">Acelerador en recta (0 - 1023)</span></div>
  <input type="number" id="n_vm" step="10" min="0" max="1023" onchange="sync('vm',this.value)"></div>
  <input type="range" id="r_vm" step="10" min="0" max="1023" oninput="sync('vm',this.value)">
</div>

<div class="card">
  <div class="row"><div><label>KP (Proporcional)</label><span class="desc">Fuerza de giro / volante</span></div>
  <input type="number" id="n_kp" step="0.05" min="0" max="20" onchange="sync('kp',this.value)"></div>
  <input type="range" id="r_kp" step="0.05" min="0" max="15" oninput="sync('kp',this.value)">
</div>

<div class="card">
  <div class="row"><div><label>KD (Derivativo)</label><span class="desc">Estabilidad / quita zigzagueo</span></div>
  <input type="number" id="n_kd" step="0.005" min="0" max="5" onchange="sync('kd',this.value)"></div>
  <input type="range" id="r_kd" step="0.005" min="0" max="2" oninput="sync('kd',this.value)">
</div>

<div class="card">
  <div class="row"><div><label>KI (Integral)</label><span class="desc">Ajuste fino en recta</span></div>
  <input type="number" id="n_ki" step="0.05" min="0" max="10" onchange="sync('ki',this.value)"></div>
  <input type="range" id="r_ki" step="0.05" min="0" max="5" oninput="sync('ki',this.value)">
</div>

<div class="card">
  <div class="row"><div><label>KF (Freno por curva)</label><span class="desc">Frena según qué tan lejos está de la línea</span></div>
  <input type="number" id="n_kf" step="0.05" min="0" max="10" onchange="sync('kf',this.value)"></div>
  <input type="range" id="r_kf" step="0.05" min="0" max="5" oninput="sync('kf',this.value)">
</div>

<div class="card">
  <div class="row"><div><label>KB (Freno anticipado)</label><span class="desc">Frena de golpe al entrar a curva</span></div>
  <input type="number" id="n_kb" step="0.05" min="0" max="10" onchange="sync('kb',this.value)"></div>
  <input type="range" id="r_kb" step="0.05" min="0" max="5" oninput="sync('kb',this.value)">
</div>

<div class="btns">
  <button class="b-cal" onclick="cmd('calibrar')">Calibrar Sensores</button>
  <button id="btnRun" class="b-run" onclick="toggleRun()">Iniciar</button>
  <button class="b-save" onclick="cmd('guardar')">Guardar en Memoria (Flash)</button>
</div>

<script>
let running = false, timer = null;
const keys = ['vm','kp','kd','ki','kf','kb'];

function sync(k, v) {
  document.getElementById('n_'+k).value = v;
  document.getElementById('r_'+k).value = v;
  clearTimeout(timer);
  timer = setTimeout(() => {
    fetch('/set?' + k + '=' + encodeURIComponent(v)).catch(()=>{});
  }, 60);
}

function cmd(c) {
  if(c === 'calibrar') document.getElementById('st').innerText = 'Calibrando... mueve el robot sobre la línea';
  fetch('/cmd?accion=' + c).then(r => r.json()).then(actualizarUI).catch(()=>{});
}

function toggleRun() {
  cmd(running ? 'detener' : 'iniciar');
}

function actualizarUI(d) {
  keys.forEach(k => {
    if(d[k] !== undefined) {
      document.getElementById('n_'+k).value = d[k];
      document.getElementById('r_'+k).value = d[k];
    }
  });
  running = d.ejecutando;
  const st = document.getElementById('st');
  const btn = document.getElementById('btnRun');
  if(!d.calibrada) {
    st.innerText = 'Estado: Esperando Calibración (Ámbar)';
    st.style.color = '#fbbf24';
  } else if(running) {
    st.innerText = 'Estado: CORRIENDO (Azul)';
    st.style.color = '#38bdf8';
  } else {
    st.innerText = 'Estado: Listo / Detenido (Verde)';
    st.style.color = '#4ade80';
  }
  btn.innerText = running ? 'DETENER' : 'INICIAR';
  btn.className = running ? 'b-stop' : 'b-run';
  if(d.msg) alert(d.msg);
}

fetch('/state').then(r => r.json()).then(actualizarUI);
</script>
</body>
</html>"""


def iniciar_wifi_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="Seguidor_ESP32", password="12345678")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 80))
    srv.listen(3)
    srv.setblocking(False)
    return srv


def parse_params(path):
    params = {}
    if "?" in path:
        qs = path.split("?", 1)[1]
        for pair in qs.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
    return params


def enviar_respuesta(conn, body, content_type="application/json"):
    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: " + content_type + "\r\n"
        "Connection: close\r\n\r\n"
    )
    conn.sendall(header.encode("utf-8"))
    if isinstance(body, str):
        conn.sendall(body.encode("utf-8"))
    else:
        conn.sendall(body)


def main():
    cargar_config()
    srv = iniciar_wifi_ap()

    Iacc = 0.0
    d_filt = 0.0
    e_prev = 0.0
    t_prev_us = time.ticks_us()

    boton_calibrar = Boton(btn_calibrar)
    boton_inicio = Boton(btn_inicio)
    calibrada = False
    ejecutando = False
    ciclos_web = 0

    # Ámbar: esperando calibración.
    indicar_color((20, 10, 0))

    while True:
        # 1. Revisar botones físicos
        if boton_calibrar.presionado():
            drv.setVelocidad(0, 0)
            ejecutando = False
            indicar_color((15, 35, 0))
            sb.calibrar(veces=5000)
            calibrada = True
            indicar_color((0, 30, 0))

        if boton_inicio.presionado():
            if ejecutando:
                ejecutando = False
                drv.setVelocidad(0, 0)
                indicar_color((0, 30, 0))
            elif calibrada:
                ejecutando = True
                Iacc = 0.0
                d_filt = 0.0
                e_prev = 0.0
                t_prev_us = time.ticks_us()
                indicar_color((0, 0, 30))
            else:
                indicar_color((20, 10, 0))

        # 2. Atender peticiones web sin frenar el PID (cada 16 ciclos si corre)
        ciclos_web += 1
        if (not ejecutando) or (ciclos_web & 15) == 0:
            try:
                conn, _ = srv.accept()
                conn.settimeout(0.05)
                try:
                    req = conn.recv(512).decode("utf-8", "ignore")
                    if req:
                        first_line = req.split("\r\n", 1)[0]
                        parts = first_line.split(" ")
                        path = parts[1] if len(parts) > 1 else "/"

                        if path == "/" or path.startswith("/index"):
                            enviar_respuesta(conn, HTML_PAGE, "text/html; charset=utf-8")

                        elif path.startswith("/set"):
                            p = parse_params(path)
                            for k in ("kp", "ki", "kd", "kf", "kb"):
                                if k in p:
                                    cfg[k] = float(p[k])
                            if "vm" in p:
                                cfg["vm"] = int(float(p["vm"]))
                            enviar_respuesta(conn, '{"ok":true}')

                        elif path.startswith("/cmd"):
                            p = parse_params(path)
                            accion = p.get("accion", "")
                            msg = ""
                            if accion == "calibrar":
                                drv.setVelocidad(0, 0)
                                ejecutando = False
                                indicar_color((15, 35, 0))
                                sb.calibrar(veces=5000)
                                calibrada = True
                                indicar_color((0, 30, 0))
                            elif accion == "iniciar":
                                if calibrada:
                                    ejecutando = True
                                    Iacc = 0.0
                                    d_filt = 0.0
                                    e_prev = 0.0
                                    t_prev_us = time.ticks_us()
                                    indicar_color((0, 0, 30))
                                else:
                                    msg = "Primero calibra los sensores."
                            elif accion == "detener":
                                ejecutando = False
                                drv.setVelocidad(0, 0)
                                indicar_color((0, 30, 0) if calibrada else (20, 10, 0))
                            elif accion == "guardar":
                                ok = guardar_config()
                                msg = "Valores guardados en el ESP32." if ok else "Error al guardar."

                            estado = dict(cfg)
                            estado["ejecutando"] = ejecutando
                            estado["calibrada"] = calibrada
                            if msg:
                                estado["msg"] = msg
                            enviar_respuesta(conn, json.dumps(estado))

                        elif path.startswith("/state"):
                            estado = dict(cfg)
                            estado["ejecutando"] = ejecutando
                            estado["calibrada"] = calibrada
                            enviar_respuesta(conn, json.dumps(estado))
                except Exception:
                    pass
                finally:
                    conn.close()
            except OSError:
                pass

        # 3. Lazo de control PID + Freno dinámico
        if ejecutando:
            t_now = time.ticks_us()
            dt = time.ticks_diff(t_now, t_prev_us) * 1e-6
            t_prev_us = t_now

            if dt < 0.0005:
                dt = 0.0005
            elif dt > 0.02:
                dt = 0.02

            pos = sb.getPos(SENSOR_RANGE)
            pos = max(-255, min(pos, 255))
            e = float(pos)

            d_raw = (e - e_prev) / dt
            alpha_d = dt / (TAU_D + dt)
            d_filt += alpha_d * (d_raw - d_filt)
            e_prev = e

            enable_I = abs(e) < E_I_ON
            if enable_I:
                Iacc = Iacc + (e * dt)
                if Iacc > I_MAX:
                    Iacc = I_MAX
                elif Iacc < -I_MAX:
                    Iacc = -I_MAX
            else:
                Iacc = Iacc * 0.995

            u = cfg["kp"] * e + cfg["ki"] * Iacc + cfg["kd"] * d_filt
            if u > U_MAX:
                u = U_MAX
            elif u < -U_MAX:
                u = -U_MAX

            pot = e / 10.0
            pot = pot * pot
            base = cfg["vm"] - abs(cfg["kf"] * pot) - abs(cfg["kb"] * 0.1 * d_filt)

            pid_val = int(round(u))
            velFin = int(round(base))

            mot_izq = velFin - pid_val
            mot_der = velFin + pid_val

            drv.setVelocidad(mot_izq, mot_der)
        else:
            time.sleep_ms(5)


if __name__ == "__main__":
    main()