import pygame
import socket
import sys
import math
import time
import threading
import os

# ─── CONFIGURACIÓN TCP ────────────────────────────────────────────────────────
IP_ROBOT = "192.168.4.1"
PORT     = 8080
PWM_MAX  = 50

# ─── COLORES ──────────────────────────────────────────────────────────────────
BG          = (10,  12,  20)
PANEL_BG    = (18,  22,  35)
PANEL_BG2   = (22,  28,  44)
ACCENT      = (0,  200, 120)
ACCENT_DIM  = (0,   80,  50)
ACCENT2     = (60, 140, 255)
ACCENT2_DIM = (20,  50, 100)
WARN        = (255, 180,   0)
DANGER      = (220,  50,  50)
TEXT_PRI    = (220, 230, 255)
TEXT_SEC    = (100, 120, 160)
TEXT_DIM    = (50,  60,  90)
BORDER      = (35,  45,  70)
BORDER_ACT  = (0,  200, 120)
WHITE       = (255, 255, 255)
TAB_BG      = (14,  17,  28)
TAB_ACT_BG  = (18,  22,  35)
GRID_COL    = (25,  30,  50)

pygame.init()
pygame.joystick.init()

joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Control detectado: {joystick.get_name()}")
else:
    print("Sin control — modo teclado (WASD / flechas)")

W, H = 1100, 660
screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption("NovaStep · Dashboard de Nova")

font_xl    = pygame.font.SysFont("Consolas", 32, bold=True)
font_big   = pygame.font.SysFont("Consolas", 22, bold=True)
font_med   = pygame.font.SysFont("Consolas", 16)
font_small = pygame.font.SysFont("Consolas", 13)
font_xs    = pygame.font.SysFont("Consolas", 11)
clock      = pygame.time.Clock()

try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(0.04)
    client_socket.connect((IP_ROBOT, PORT))
    print("Conectado al robot")
    conectado = True
except Exception as e:
    print(f"Sin conexión: {e}  —  modo offline")
    conectado = False

sock_lock = threading.Lock()

# ─── TELEMETRÍA ───────────────────────────────────────────────────────────────
telem = {
    "POS_X": 0.0, "POS_Y": 0.0, "THETA": 0.0,
    "VEL_X": 0.0, "VEL_O": 0.0,
    "US_DIST": 200.0,
    "PULSOS_I": 0, "PULSOS_D": 0,
    "ROLL": 0.0, "PITCH": 0.0, "YAW": 0.0,
    "EKF_X": 0.0, "EKF_Y": 0.0, "EKF_THETA": 0.0,
}

telem_lock      = threading.Lock()
recv_buffer     = ""
last_telem_time = time.time()

tray_lock = threading.Lock()
tray_odom = []
tray_ekf  = []
MAX_HIST  = 600

# ─── OFFSET VISUAL DE ENCODERS (solo para display, no afecta robot) ───────────
encoder_offset_i = 0
encoder_offset_d = 0
encoder_lock     = threading.Lock()

def parse_telemetry(raw: str):
    with telem_lock:
        for line in raw.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                if key in telem:
                    try:
                        telem[key] = float(val)
                    except ValueError:
                        pass

def get_telem(key):
    with telem_lock:
        return telem[key]

def get_telem_snapshot():
    with telem_lock:
        return dict(telem)

def read_socket():
    global recv_buffer, last_telem_time
    if not conectado:
        return
    try:
        chunk = client_socket.recv(2048).decode("utf-8", errors="ignore")
        if chunk:
            recv_buffer += chunk
            last_telem_time = time.time()
            if "\n" in recv_buffer:
                complete, _, recv_buffer = recv_buffer.rpartition("\n")
                parse_telemetry(complete)
    except socket.timeout:
        pass
    except Exception:
        pass

def send_cmd(cmd: str):
    if not conectado:
        return
    try:
        with sock_lock:
            client_socket.sendall(cmd.encode())
    except socket.error:
        pass

def clear_trajectories():
    """Limpia trayectorias Y resetea visualmente los encoders a cero."""
    global encoder_offset_i, encoder_offset_d
    with tray_lock:
        tray_odom.clear()
        tray_ekf.clear()
    # Capturar valor actual de encoders para usarlo como offset visual
    with telem_lock:
        raw_i = telem["PULSOS_I"]
        raw_d = telem["PULSOS_D"]
    with encoder_lock:
        encoder_offset_i = raw_i
        encoder_offset_d = raw_d

def get_encoder_display(snap):
    """Devuelve los valores de encoder ajustados por el offset visual."""
    with encoder_lock:
        oi = encoder_offset_i
        od = encoder_offset_d
    return int(snap["PULSOS_I"] - oi), int(snap["PULSOS_D"] - od)

# ─── GUARDAR MAPA ─────────────────────────────────────────────────────────────
save_map_feedback      = ""
save_map_feedback_time = 0.0

def save_map_to_png():
    """
    Genera una imagen PNG del mapa 2D (trayectorias Odom y EKF)
    y la guarda en el escritorio o carpeta del script.
    """
    global save_map_feedback, save_map_feedback_time

    with tray_lock:
        odom_data = list(tray_odom)
        ekf_data  = list(tray_ekf)

    if len(odom_data) < 2 and len(ekf_data) < 2:
        save_map_feedback      = "SIN DATOS PARA GUARDAR"
        save_map_feedback_time = time.time()
        return

    IMG_W, IMG_H = 800, 800
    PAD = 50

    surf = pygame.Surface((IMG_W, IMG_H))
    surf.fill((8, 10, 18))

    # Grid de fondo
    for i in range(1, 5):
        gx = PAD + i * (IMG_W - 2 * PAD) // 5
        gy = PAD + i * (IMG_H - 2 * PAD) // 5
        pygame.draw.line(surf, (25, 30, 50), (gx, PAD), (gx, IMG_H - PAD))
        pygame.draw.line(surf, (25, 30, 50), (PAD, gy), (IMG_W - PAD, gy))

    cx2, cy2 = IMG_W // 2, IMG_H // 2
    pygame.draw.line(surf, (40, 50, 80), (PAD, cy2), (IMG_W - PAD, cy2))
    pygame.draw.line(surf, (40, 50, 80), (cx2, PAD), (cx2, IMG_H - PAD))

    # Calcular escala
    all_pts = odom_data + ekf_data
    xs   = [p[0] for p in all_pts]
    ys   = [p[1] for p in all_pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 0.4)
    xmin, ymin = min(xs), min(ys)

    def to_screen(px, py):
        sx = PAD + (px - xmin) / span * (IMG_W - 2 * PAD)
        sy = IMG_H - PAD - (py - ymin) / span * (IMG_H - 2 * PAD)
        return (int(sx), int(sy))

    if len(odom_data) > 1:
        pts = [to_screen(p[0], p[1]) for p in odom_data]
        pygame.draw.lines(surf, ACCENT, False, pts, 2)
        pygame.draw.circle(surf, ACCENT, pts[-1], 6)
        pygame.draw.circle(surf, WHITE,  pts[0],  4)

    if len(ekf_data) > 1:
        pts = [to_screen(p[0], p[1]) for p in ekf_data]
        pygame.draw.lines(surf, ACCENT2, False, pts, 2)
        pygame.draw.circle(surf, ACCENT2, pts[-1], 6)
        pygame.draw.circle(surf, WHITE,   pts[0],  4)

    # Leyenda
    legend_font = pygame.font.SysFont("Consolas", 14)
    surf.blit(legend_font.render("■ Odom", True, ACCENT),  (PAD, IMG_H - PAD + 8))
    surf.blit(legend_font.render("■ EKF",  True, ACCENT2), (PAD + 80, IMG_H - PAD + 8))

    # Timestamp
    ts    = time.strftime("%Y%m%d_%H%M%S")
    fname = f"nova_mapa_{ts}.png"

    # Guardar en carpeta del script o escritorio
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path   = os.path.join(script_dir, fname)
    try:
        pygame.image.save(surf, out_path)
        save_map_feedback      = f"GUARDADO: {fname}"
        save_map_feedback_time = time.time()
        print(f"Mapa guardado en: {out_path}")
    except Exception as e:
        save_map_feedback      = f"ERROR: {e}"
        save_map_feedback_time = time.time()
        print(f"Error al guardar mapa: {e}")

# ─── PARÁMETROS DE CONTROL / UI ───────────────────────────────────────────────
routine_lock     = threading.Lock()
routine_active   = False
routine_name     = "SIN RUTINA"
routine_progress = 0.0
routine_cancel   = False

base_speed      = 20
BASE_SPEED_MIN  = 5
BASE_SPEED_MAX  = PWM_MAX
BASE_SPEED_STEP = 5

cmd_feedback      = "LISTO"
cmd_feedback_time = 0.0


def set_feedback(msg: str):
    global cmd_feedback, cmd_feedback_time
    cmd_feedback = msg
    cmd_feedback_time = time.time()


def _set_routine_state(active, name="", progress=0.0):
    global routine_active, routine_name, routine_progress
    with routine_lock:
        routine_active   = active
        routine_name     = name
        routine_progress = progress


def _send_motors(left, right):
    left  = int(max(-PWM_MAX, min(PWM_MAX, left)))
    right = int(max(-PWM_MAX, min(PWM_MAX, right)))
    send_cmd(f"PWM:{right},{left}\n")


def _stop_motors():
    send_cmd("GOAL:stop\n")
    set_feedback("STOP")


def launch_routine(*_args, **_kwargs):
    set_feedback("RUTINA: AÚN EN FIRMWARE")


def cancel_routine():
    _stop_motors()

# ─── MAPEO DE BOTONES ─────────────────────────────────────────────────────────
BTN_X          = 0
BTN_CIRCLE     = 1
BTN_SQUARE     = 2
BTN_TRI        = 3
BTN_SHARE      = 4
BTN_PS         = 5
BTN_OPTIONS    = 6
BTN_L1         = 9
BTN_R1         = 10
BTN_DPAD_UP    = 11
BTN_DPAD_DOWN  = 12
BTN_DPAD_LEFT  = 13
BTN_DPAD_RIGHT = 14

USE_HAT = (joystick is not None and joystick.get_numhats() > 0)
if joystick:
    print(f"D-Pad via {'HAT' if USE_HAT else 'botones'}")

ADVANCE_DIST = 1.0

# ─── HELPERS DE DIBUJO ────────────────────────────────────────────────────────
def panel(surf, rect, title="", accent_line=True):
    x, y, w, h = rect
    pygame.draw.rect(surf, PANEL_BG, rect, border_radius=8)
    pygame.draw.rect(surf, BORDER,   rect, 1, border_radius=8)
    if title:
        lbl = font_xs.render(title.upper(), True, TEXT_DIM)
        surf.blit(lbl, (x + 10, y + 9))
        if accent_line:
            pygame.draw.line(surf, BORDER, (x + 10, y + 24), (x + w - 10, y + 24))

def hbar(surf, x, y, w, h, value, vmin, vmax, color=ACCENT):
    pygame.draw.rect(surf, PANEL_BG2, (x, y, w, h), border_radius=3)
    r  = max(0.0, min(1.0, (value - vmin) / max(vmax - vmin, 1e-6)))
    fw = int(w * r)
    if fw > 2:
        pygame.draw.rect(surf, color, (x, y, fw, h), border_radius=3)

def compass(surf, cx, cy, r, angle_deg):
    pygame.draw.circle(surf, PANEL_BG2, (cx, cy), r)
    pygame.draw.circle(surf, BORDER,    (cx, cy), r, 1)
    for deg, lbl in [(0, "N"), (90, "E"), (180, "S"), (270, "O")]:
        a  = math.radians(deg - 90)
        tx = cx + (r - 11) * math.cos(a)
        ty = cy + (r - 11) * math.sin(a)
        c  = ACCENT if lbl == "N" else TEXT_DIM
        t  = font_xs.render(lbl, True, c)
        surf.blit(t, t.get_rect(center=(int(tx), int(ty))))
    a    = math.radians(angle_deg - 90)
    tip  = (cx + (r - 18) * math.cos(a), cy + (r - 18) * math.sin(a))
    tail = (cx - (r - 22) * math.cos(a), cy - (r - 22) * math.sin(a))
    pygame.draw.line(surf, ACCENT,
                     (int(tail[0]), int(tail[1])),
                     (int(tip[0]),  int(tip[1])), 2)
    pygame.draw.circle(surf, ACCENT, (int(tip[0]), int(tip[1])), 3)

def draw_label_value(surf, x, y, label, value, vcolor=TEXT_PRI, gap=90):
    surf.blit(font_small.render(label, True, TEXT_SEC), (x, y))
    surf.blit(font_med.render(value, True, vcolor), (x + gap, y - 1))

def draw_grid_2d(surf, rect):
    x, y, w, h = rect
    pygame.draw.rect(surf, (8, 10, 18), rect, border_radius=6)
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=6)
    for i in range(1, 5):
        gx = x + i * w // 5
        gy = y + i * h // 5
        pygame.draw.line(surf, GRID_COL, (gx, y + 2),     (gx, y + h - 2))
        pygame.draw.line(surf, GRID_COL, (x + 2, gy), (x + w - 2, gy))
    cx2, cy2 = x + w // 2, y + h // 2
    pygame.draw.line(surf, (40, 50, 80), (x + 4,    cy2), (x + w - 4, cy2))
    pygame.draw.line(surf, (40, 50, 80), (cx2, y + 4),    (cx2, y + h - 4))

    with tray_lock:
        odom_data = list(tray_odom)
        ekf_data  = list(tray_ekf)

    if len(odom_data) < 2 and len(ekf_data) < 2:
        t = font_xs.render("sin datos de trayectoria", True, TEXT_DIM)
        surf.blit(t, t.get_rect(center=(x + w // 2, y + h // 2)))
        return

    all_pts = odom_data + ekf_data
    xs   = [p[0] for p in all_pts]
    ys   = [p[1] for p in all_pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 0.4)
    xmin, ymin = min(xs), min(ys)
    pad = 18

    def to_screen(px, py):
        sx = x + pad + (px - xmin) / span * (w - 2 * pad)
        sy = y + h - pad - (py - ymin) / span * (h - 2 * pad)
        return (int(sx), int(sy))

    if len(odom_data) > 1:
        pts = [to_screen(p[0], p[1]) for p in odom_data]
        pygame.draw.lines(surf, ACCENT, False, pts, 1)
        pygame.draw.circle(surf, ACCENT, pts[-1], 4)
    if len(ekf_data) > 1:
        pts = [to_screen(p[0], p[1]) for p in ekf_data]
        pygame.draw.lines(surf, ACCENT2, False, pts, 1)
        pygame.draw.circle(surf, ACCENT2, pts[-1], 4)

    surf.blit(font_xs.render("■ Odom", True, ACCENT),  (x + 6, y + h - 26))
    surf.blit(font_xs.render("■ EKF",  True, ACCENT2), (x + 6, y + h - 14))
    surf.blit(font_xs.render("OPTIONS: limpiar", True, TEXT_DIM),
              (x + w - 100, y + h - 14))

def draw_joystick_visual(surf, cx, cy, r, ax, ay):
    pygame.draw.circle(surf, PANEL_BG2, (cx, cy), r)
    pygame.draw.circle(surf, BORDER,    (cx, cy), r, 1)
    pygame.draw.circle(surf, BORDER,    (cx, cy), r // 2, 1)
    pygame.draw.line(surf, BORDER, (cx - r, cy),  (cx + r, cy))
    pygame.draw.line(surf, BORDER, (cx, cy - r),  (cx, cy + r))
    dot_x = cx + int(ax * (r - 10))
    dot_y = cy - int(ay * (r - 10))
    pygame.draw.circle(surf, ACCENT, (dot_x, dot_y), 11)
    pygame.draw.circle(surf, WHITE,  (dot_x, dot_y), 4)

def draw_motor_arrow(surf, x, y, w, h, pwm, max_pwm, label):
    panel(surf, (x, y, w, h), label, accent_line=False)
    cx    = x + w // 2
    cy    = y + h // 2 + 6
    ratio = pwm / max(max_pwm, 1)
    bar_h = int(abs(ratio) * (h // 2 - 20))
    color = ACCENT if pwm >= 0 else WARN
    if ratio > 0:
        pygame.draw.rect(surf, color, (cx - 10, cy - bar_h, 20, bar_h), border_radius=3)
        pygame.draw.polygon(surf, color,
            [(cx, cy - bar_h - 8), (cx - 7, cy - bar_h), (cx + 7, cy - bar_h)])
    elif ratio < 0:
        pygame.draw.rect(surf, color, (cx - 10, cy, 20, bar_h), border_radius=3)
        pygame.draw.polygon(surf, color,
            [(cx, cy + bar_h + 8), (cx - 7, cy + bar_h), (cx + 7, cy + bar_h)])
    else:
        pygame.draw.line(surf, BORDER, (cx - 10, cy), (cx + 10, cy), 2)
    val = font_small.render(f"{pwm:+d}", True, color)
    surf.blit(val, val.get_rect(center=(cx, y + h - 14)))

def draw_sensor_panel(surf, rect, t):
    x, y, w, h = rect
    panel(surf, rect, "SENSORES CRÍTICOS")

    us       = t["US_DIST"]
    us_color = DANGER if us < 20 else (WARN if us < 50 else ACCENT)
    surf.blit(font_xs.render("Ultrasonido", True, TEXT_SEC),       (x + 12, y + 28))
    surf.blit(font_med.render(f"{us:.1f} cm", True, us_color),     (x + 12, y + 42))
    hbar(surf, x + 10, y + 60, w - 20, 8, us, 0, 200, us_color)

    surf.blit(font_xs.render("Orientación", True, TEXT_SEC),       (x + 12, y + 80))
    pose_rows = [
        ("Roll",  f"{t['ROLL']:+.1f}°"),
        ("Pitch", f"{t['PITCH']:+.1f}°"),
        ("Yaw",   f"{t['YAW']:+.1f}°"),
    ]
    for i, (lbl, val) in enumerate(pose_rows):
        surf.blit(font_xs.render(lbl,    True, TEXT_SEC), (x + 12, y + 96 + i * 16))
        surf.blit(font_small.render(val, True, TEXT_PRI), (x + 60, y + 96 + i * 16))

    surf.blit(font_xs.render("Encoders", True, TEXT_SEC),          (x + 12, y + 152))
    surf.blit(font_xs.render("IZQ",      True, TEXT_DIM),          (x + 12, y + 168))
    surf.blit(font_xs.render("DER",      True, TEXT_DIM),          (x + 12, y + 184))
    # ── Usar valores con offset visual aplicado ───────────────────────────────
    enc_i, enc_d = get_encoder_display(t)
    surf.blit(font_small.render(str(enc_i), True, TEXT_PRI), (x + 60, y + 168))
    surf.blit(font_small.render(str(enc_d), True, TEXT_PRI), (x + 60, y + 184))

def draw_compact_pose_panel(surf, rect, t):
    x, y, w, h = rect
    panel(surf, rect, "ESTADO DE POSE (fusionado)")
    header_y = y + 28
    surf.blit(font_xs.render("CAMPO", True, TEXT_DIM), (x + 14, header_y))
    surf.blit(font_xs.render("ODOM",  True, ACCENT),   (x + 80, header_y))
    surf.blit(font_xs.render("EKF",   True, ACCENT2),  (x + 140, header_y))
    surf.blit(font_xs.render("DELTA", True, TEXT_DIM), (x + 200, header_y))
    pygame.draw.line(surf, BORDER,
                     (x + 10, header_y + 18), (x + w - 10, header_y + 18))
    cmp_rows = [
        ("X (m)", t["POS_X"], t["EKF_X"]),
        ("Y (m)", t["POS_Y"], t["EKF_Y"]),
        ("θ (°)", t["THETA"], t["EKF_THETA"]),
    ]
    for i, (lbl, vo, ve) in enumerate(cmp_rows):
        ry = header_y + 24 + i * 32
        pygame.draw.rect(surf, (20, 25, 42), (x + 8, ry, w - 16, 28), border_radius=5)
        surf.blit(font_xs.render(lbl,              True, TEXT_SEC), (x + 16,  ry + 6))
        surf.blit(font_small.render(f"{vo:+.3f}",  True, ACCENT),  (x + 80,  ry + 6))
        surf.blit(font_small.render(f"{ve:+.3f}",  True, ACCENT2), (x + 140, ry + 6))
        delta = vo - ve
        dc = WARN if abs(delta) > 0.05 else TEXT_DIM
        surf.blit(font_xs.render(f"{delta:+.3f}", True, dc),       (x + 200, ry + 6))

def draw_compact_routine_panel(surf, rect):
    x, y, w, h = rect
    panel(surf, rect, "COMANDOS & VEL. BASE")

    fb_active = (time.time() - cmd_feedback_time) < 2.0
    fb_color  = ACCENT if fb_active else TEXT_DIM
    fb_bg     = (20, 35, 26) if fb_active else (20, 25, 42)

    pygame.draw.rect(surf, fb_bg, (x + 6, y + 30, w - 12, 28), border_radius=5)
    pygame.draw.rect(surf, BORDER if not fb_active else ACCENT,
                     (x + 6, y + 30, w - 12, 28), 1, border_radius=5)
    surf.blit(font_xs.render(f"CMD: {cmd_feedback}", True, fb_color), (x + 12, y + 38))

    surf.blit(font_xs.render("Rutinas automáticas: pendientes en firmware", True, TEXT_DIM),
              (x + 10, y + 64))

    hbar(surf, x + 10, y + h - 18, w - 20, 8,
         base_speed, BASE_SPEED_MIN, BASE_SPEED_MAX, ACCENT2)
    surf.blit(font_xs.render(f"VELOCIDAD BASE: {base_speed} PWM (L1/R1)",
                             True, TEXT_DIM), (x + 10, y + h - 30))

def draw_control_help_panel(surf, rect):
    x, y, w, h = rect
    panel(surf, rect, "AYUDA DE CONTROL CONSOLIDADA")
    ref = [
        ("Stick izq / der",         "Avance y giro manual simple"),
        ("R1 / L1",                 "Aumentar/Disminuir Vel. Base"),
        ("× (Cruz)",                "STOP inmediato"),
        ("OPTIONS",                 "Limpiar trazo + reset encoders"),
        ("△ (Triángulo)",           "Tocar Buzzer"),
        ("D-Pad / □ / ○",           "Reservado para rutinas en firmware"),
        ("Python",                  "Solo manda comandos y muestra datos"),
        ("ESP32",                   "Hará el control real en la siguiente fase"),
    ]
    for i, (btn, desc) in enumerate(ref):
        ry = y + 28 + i * 20
        surf.blit(font_xs.render(btn,  True, ACCENT2), (x + 12,  ry + 2))
        surf.blit(font_xs.render(desc, True, TEXT_SEC), (x + 130, ry + 2))

# ─── BOTÓN HELPER ─────────────────────────────────────────────────────────────
def draw_button(surf, rect, label, color_bg, color_border, color_text, hover=False):
    """Dibuja un botón con estilo dashboard y devuelve el rect para hit-test."""
    x, y, w, h = rect
    bg = tuple(min(255, c + 20) for c in color_bg) if hover else color_bg
    pygame.draw.rect(surf, bg,           rect, border_radius=6)
    pygame.draw.rect(surf, color_border, rect, 1, border_radius=6)
    lbl = font_small.render(label, True, color_text)
    surf.blit(lbl, lbl.get_rect(center=(x + w // 2, y + h // 2)))
    return pygame.Rect(rect)

# ─── TABS ─────────────────────────────────────────────────────────────────────
TABS      = ["CONTROL", "DIAGNÓSTICO"]
active_tab = 0
TAB_H     = 38
TAB_W     = 160

# ─── ESTADO GLOBAL DE INPUT ───────────────────────────────────────────────────
buzzer_prev     = False
axis_x = axis_y = 0.0
axis_rx = axis_ry = 0.0
pwm_l = pwm_r   = 0
last_ping        = time.time()
running          = True
btn_prev         = {}
clear_signal_time = 0.0

# Rects de botones Diagnóstico (se recalculan cada frame)
btn_rect_save_map   = pygame.Rect(0, 0, 0, 0)
btn_rect_clear_diag = pygame.Rect(0, 0, 0, 0)

def btn_just_pressed(idx):
    if joystick is None:
        return False
    cur  = joystick.get_button(idx)
    prev = btn_prev.get(idx, 0)
    btn_prev[idx] = cur
    return bool(cur and not prev)

hat_prev      = (0, 0)
dpad_btn_prev = {
    BTN_DPAD_UP: 0, BTN_DPAD_DOWN: 0,
    BTN_DPAD_LEFT: 0, BTN_DPAD_RIGHT: 0,
}

# ─── LOOP PRINCIPAL ───────────────────────────────────────────────────────────
while running:
    W, H = screen.get_size()
    screen.fill(BG)
    read_socket()

    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_1:
                active_tab = 0
            if event.key == pygame.K_2:
                active_tab = 1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Cambio de tab
            for i in range(len(TABS)):
                tx = 10 + i * (TAB_W + 4)
                if tx <= mx <= tx + TAB_W and 6 <= my <= 6 + TAB_H - 2:
                    active_tab = i
            # Botones de Diagnóstico
            if active_tab == 1:
                if btn_rect_save_map.collidepoint(mx, my):
                    threading.Thread(target=save_map_to_png, daemon=True).start()
                if btn_rect_clear_diag.collidepoint(mx, my):
                    clear_trajectories()
                    clear_signal_time = time.time()

    # ── Snapshot de telemetría ────────────────────────────────────────────────
    snap = get_telem_snapshot()

    buzzer_on = False

    if joystick:
        pygame.event.pump()

        ax = joystick.get_axis(0)
        ay = -joystick.get_axis(1)

        num_axes = joystick.get_numaxes()
        if num_axes >= 5:
            arx =  joystick.get_axis(3)
            ary = -joystick.get_axis(4)
        elif num_axes >= 4:
            arx =  joystick.get_axis(2)
            ary = -joystick.get_axis(3)
        else:
            arx = ary = 0.0

        if abs(ax)  < 0.15: ax  = 0.0
        if abs(ay)  < 0.15: ay  = 0.0
        if abs(arx) < 0.15: arx = 0.0
        if abs(ary) < 0.15: ary = 0.0

        axis_x,  axis_y  = ax,  ay
        axis_rx, axis_ry = arx, ary
        buzzer_on = bool(joystick.get_button(BTN_TRI))

        if USE_HAT:
            hat_cur    = joystick.get_hat(0)
            dpad_up    = hat_cur != hat_prev and hat_cur == (0,  1)
            dpad_down  = hat_cur != hat_prev and hat_cur == (0, -1)
            dpad_left  = hat_cur != hat_prev and hat_cur == (-1, 0)
            dpad_right = hat_cur != hat_prev and hat_cur == (1,  0)
            hat_prev   = hat_cur
        else:
            def _dpad_just(idx):
                cur  = joystick.get_button(idx)
                prev = dpad_btn_prev.get(idx, 0)
                dpad_btn_prev[idx] = cur
                return bool(cur and not prev)
            dpad_up    = _dpad_just(BTN_DPAD_UP)
            dpad_down  = _dpad_just(BTN_DPAD_DOWN)
            dpad_left  = _dpad_just(BTN_DPAD_LEFT)
            dpad_right = _dpad_just(BTN_DPAD_RIGHT)

        if dpad_up:
            set_feedback("D-PAD ↑: RESERVADO PARA FIRMWARE")
        elif dpad_down:
            set_feedback("D-PAD ↓: RESERVADO PARA FIRMWARE")
        elif dpad_left:
            set_feedback("D-PAD ←: RESERVADO PARA FIRMWARE")
        elif dpad_right:
            set_feedback("D-PAD →: RESERVADO PARA FIRMWARE")

        if btn_just_pressed(BTN_SQUARE):
            set_feedback("□: GIRO 360° PASARÁ A FIRMWARE")
        if btn_just_pressed(BTN_CIRCLE):
            set_feedback("○: GIRO 360° PASARÁ A FIRMWARE")
        if btn_just_pressed(BTN_R1):
            base_speed = min(base_speed + BASE_SPEED_STEP, BASE_SPEED_MAX)
        if btn_just_pressed(BTN_L1):
            base_speed = max(base_speed - BASE_SPEED_STEP, BASE_SPEED_MIN)
        if btn_just_pressed(BTN_X):
            _stop_motors()

        if btn_just_pressed(BTN_OPTIONS):
            clear_trajectories()
            send_cmd("RESET_ENCODERS\n")
            send_cmd("BUZZER:PLAY\n")
            set_feedback("TRAZO + ENCODERS REINICIADOS")
            clear_signal_time = time.time()

    else:
        keys   = pygame.key.get_pressed()
        axis_y = ((1 if keys[pygame.K_w] or keys[pygame.K_UP]    else 0)
                - (1 if keys[pygame.K_s] or keys[pygame.K_DOWN]  else 0))
        axis_x = ((1 if keys[pygame.K_a] or keys[pygame.K_LEFT]  else 0)
                - (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0))
        axis_rx = axis_ry = 0.0
        buzzer_on = bool(keys[pygame.K_SPACE])

    # ── Control manual SIMPLE: Python solo envía mando, no corrige yaw ───────
    with routine_lock:
        busy = routine_active

    if not busy:
        fwd_cmd  = axis_y
        turn_cmd = axis_rx if abs(axis_rx) > 0.01 else axis_x

        left_speed  = fwd_cmd + turn_cmd
        right_speed = fwd_cmd - turn_cmd

        left_speed  = max(-1.0, min(1.0, left_speed))
        right_speed = max(-1.0, min(1.0, right_speed))

        pwm_l = int(left_speed  * base_speed)
        pwm_r = int(right_speed * base_speed)

        _send_motors(pwm_l, pwm_r)
    else:
        pwm_l = pwm_r = 0
        axis_x = axis_y = axis_rx = axis_ry = 0.0

    if buzzer_on and not buzzer_prev:
        send_cmd("BUZZER:PLAY\n")
    buzzer_prev = buzzer_on

    if time.time() - last_ping > 0.4:
        send_cmd("PING\n")
        last_ping = time.time()

    # ── Actualizar historiales ────────────────────────────────────────────────
    with tray_lock:
        p_odom = (snap["POS_X"], snap["POS_Y"])
        p_ekf  = (snap["EKF_X"], snap["EKF_Y"])
        if not tray_odom or tray_odom[-1] != p_odom:
            tray_odom.append(p_odom)
            if len(tray_odom) > MAX_HIST:
                tray_odom.pop(0)
        if not tray_ekf or tray_ekf[-1] != p_ekf:
            tray_ekf.append(p_ekf)
            if len(tray_ekf) > MAX_HIST:
                tray_ekf.pop(0)

    # ── Renderizado ───────────────────────────────────────────────────────────
    pygame.draw.rect(screen, TAB_BG, (0, 0, W, TAB_H + 8))
    pygame.draw.line(screen, BORDER, (0, TAB_H + 8), (W, TAB_H + 8))
    for i, name in enumerate(TABS):
        tx        = 10 + i * (TAB_W + 4)
        is_active = (i == active_tab)
        bg        = TAB_ACT_BG if is_active else TAB_BG
        pygame.draw.rect(screen, bg, (tx, 6, TAB_W, TAB_H - 2), border_radius=6)
        if is_active:
            pygame.draw.rect(screen, BORDER_ACT,
                             (tx, 6, TAB_W, TAB_H - 2), 1, border_radius=6)
            pygame.draw.line(screen, ACCENT,
                             (tx + 12, TAB_H + 5), (tx + TAB_W - 12, TAB_H + 5), 2)
        tab_color = TEXT_PRI if is_active else TEXT_DIM
        t_surf = font_med.render(f"[{i+1}] {name}", True, tab_color)
        screen.blit(t_surf, t_surf.get_rect(
            center=(tx + TAB_W // 2, 6 + (TAB_H - 2) // 2)))

    staleness  = time.time() - last_telem_time
    conn_color = ACCENT if (conectado and staleness < 1.5) else (WARN if conectado else DANGER)
    conn_txt   = ("CONECTADO" if (conectado and staleness < 1.5)
                  else ("SIN DATOS" if conectado else "OFFLINE"))
    pygame.draw.circle(screen, conn_color, (W - 130, TAB_H // 2 + 6), 5)
    screen.blit(font_small.render(conn_txt, True, conn_color),
                (W - 120, TAB_H // 2 - 1))
    screen.blit(font_xs.render(f"{clock.get_fps():.0f} fps", True, TEXT_DIM),
                (W - 55, TAB_H // 2 - 1))

    CONTENT_Y = TAB_H + 14

    # ── TAB 0 — CONTROL ───────────────────────────────────────────────────────
    if active_tab == 0:
        C1_W = (W // 4) - 20
        C3_W = (W // 4)
        C2_W = W - C1_W - C3_W - 30
        C1X  = 10
        C2X  = C1X + C1_W + 5
        C3X  = C2X + C2_W + 5

        entrada_h = 290
        panel(screen, (C1X, CONTENT_Y, C1_W, entrada_h), "ENTRADA & MOTORES")

        r_joy = 32
        j1_cx = C1X + (C1_W // 4)
        j2_cx = C1X + (3 * C1_W // 4)
        joy_y = CONTENT_Y + 70

        draw_joystick_visual(screen, j1_cx, joy_y, r_joy, axis_x, axis_y)
        draw_joystick_visual(screen, j2_cx, joy_y, r_joy, axis_rx, axis_ry)

        screen.blit(font_xs.render("IZQ", True, TEXT_DIM), (j1_cx - 10, joy_y + r_joy + 8))
        screen.blit(font_xs.render("DER", True, TEXT_DIM), (j2_cx - 10, joy_y + r_joy + 8))

        if busy:
            t_s = font_xs.render("COMANDO AUTOMÁTICO ACTIVO", True, WARN)
            screen.blit(t_s, t_s.get_rect(
                center=(C1X + C1_W // 2, joy_y + r_joy + 30)))
        else:
            t_s = font_xs.render("CONTROL MANUAL SIMPLE", True, TEXT_DIM)
            screen.blit(t_s, t_s.get_rect(
                center=(C1X + C1_W // 2, joy_y + r_joy + 30)))

        mot_y = CONTENT_Y + 145
        mw    = 40
        draw_motor_arrow(screen, C1X + (C1_W // 2) - mw - 10,
                         mot_y, mw, 105, pwm_l, PWM_MAX, "M-IZQ")
        draw_motor_arrow(screen, C1X + (C1_W // 2) + 10,
                         mot_y, mw, 105, pwm_r, PWM_MAX, "M-DER")

        b_col = DANGER if buzzer_on else TEXT_DIM
        pygame.draw.circle(screen, b_col,
                           (C1X + 20, CONTENT_Y + entrada_h - 20), 5)
        screen.blit(font_xs.render("△ BUZZER", True, b_col),
                    (C1X + 30, CONTENT_Y + entrada_h - 25))

        is_clearing = (time.time() - clear_signal_time) < 0.3
        c_col = WARN if is_clearing else TEXT_DIM
        pygame.draw.polygon(screen, c_col, [
            (C1X + 115, CONTENT_Y + entrada_h - 25),
            (C1X + 120, CONTENT_Y + entrada_h - 20),
            (C1X + 115, CONTENT_Y + entrada_h - 15),
            (C1X + 110, CONTENT_Y + entrada_h - 20),
        ])
        screen.blit(font_xs.render("OPTIONS: CLEAR", True, c_col),
                    (C1X + 125, CONTENT_Y + entrada_h - 25))

        map_h = H - CONTENT_Y - 10
        draw_grid_2d(screen, (C2X, CONTENT_Y, C2_W, map_h))
        panel(screen, (C2X, CONTENT_Y, C2_W, 30),
              "MAPA DE TRAYECTORIA 2D — ODOM vs EKF", accent_line=False)

        pose_fusion_h = 130
        draw_compact_pose_panel(screen, (C3X, CONTENT_Y, C3_W, pose_fusion_h), snap)

        sensor_h = 210
        draw_sensor_panel(screen,
            (C3X, CONTENT_Y + pose_fusion_h + 5, C3_W, sensor_h), snap)

        routine_h = 90
        draw_compact_routine_panel(screen,
            (C3X, CONTENT_Y + pose_fusion_h + sensor_h + 10, C3_W, routine_h))

        help_h = H - CONTENT_Y - (pose_fusion_h + sensor_h + routine_h) - 20
        draw_control_help_panel(screen,
            (C3X, CONTENT_Y + pose_fusion_h + sensor_h + routine_h + 15,
             C3_W, help_h))

    # ── TAB 1 — DIAGNÓSTICO ───────────────────────────────────────────────────
    elif active_tab == 1:
        C1_W = (W // 3) - 10
        C1X  = 10
        C2X  = C1X + C1_W + 5
        C3X  = C2X + C1_W + 5

        # ── Columna 1: telemetría raw ─────────────────────────────────────────
        panel(screen, (C1X, CONTENT_Y, C1_W, H - CONTENT_Y - 10), "TELEMETRÍA RAW")
        enc_i_disp, enc_d_disp = get_encoder_display(snap)
        raw_items = [
            ("POS_X",     f"{snap['POS_X']:+.4f} m"),
            ("POS_Y",     f"{snap['POS_Y']:+.4f} m"),
            ("THETA",     f"{snap['THETA']:+.3f} °"),
            ("VEL_X",     f"{snap['VEL_X']:.4f} m/s"),
            ("VEL_O",     f"{snap['VEL_O']:+.3f} °/s"),
            ("US_DIST",   f"{snap['US_DIST']:.1f} cm"),
            ("PULSOS_I",  str(enc_i_disp)),   # ← valor con offset visual
            ("PULSOS_D",  str(enc_d_disp)),   # ← valor con offset visual
            ("ROLL",      f"{snap['ROLL']:+.3f} °"),
            ("PITCH",     f"{snap['PITCH']:+.3f} °"),
            ("YAW",       f"{snap['YAW']:+.3f} °"),
            ("EKF_X",     f"{snap['EKF_X']:+.4f} m"),
            ("EKF_Y",     f"{snap['EKF_Y']:+.4f} m"),
            ("EKF_THETA", f"{snap['EKF_THETA']:+.3f} °"),
        ]
        for i, (key, val) in enumerate(raw_items):
            ry = CONTENT_Y + 32 + i * 34
            pygame.draw.rect(screen, (20, 25, 40),
                             (C1X + 6, ry - 2, C1_W - 12, 28), border_radius=4)
            screen.blit(font_small.render(key, True, TEXT_SEC), (C1X + 14, ry + 4))
            vt = font_small.render(val, True, ACCENT)
            screen.blit(vt, vt.get_rect(right=C1X + C1_W - 14, top=ry + 4))
            pygame.draw.line(screen, BORDER,
                             (C1X + 6, ry + 26), (C1X + C1_W - 6, ry + 26))

        # ── Columna 2: gauges ────────────────────────────────────────────────
        gauge_w = C1_W - 10
        screen.blit(font_med.render("ROLL", True, TEXT_DIM),  (C2X, CONTENT_Y + 10))
        hbar(screen, C2X, CONTENT_Y + 30, gauge_w, 10,
             snap["ROLL"] + 90, 0, 180,
             ACCENT if abs(snap["ROLL"]) < 15 else WARN)
        screen.blit(font_small.render(f"{snap['ROLL']:+.1f}°", True, TEXT_PRI),
                    (C2X + gauge_w - 50, CONTENT_Y + 10))

        screen.blit(font_med.render("PITCH", True, TEXT_DIM), (C2X, CONTENT_Y + 50))
        hbar(screen, C2X, CONTENT_Y + 70, gauge_w, 10,
             snap["PITCH"] + 90, 0, 180,
             ACCENT if abs(snap["PITCH"]) < 15 else WARN)
        screen.blit(font_small.render(f"{snap['PITCH']:+.1f}°", True, TEXT_PRI),
                    (C2X + gauge_w - 50, CONTENT_Y + 50))

        us       = snap["US_DIST"]
        us_color = DANGER if us < 20 else (WARN if us < 50 else ACCENT)
        screen.blit(font_med.render("Ultrasonido", True, TEXT_DIM), (C2X, CONTENT_Y + 100))
        hbar(screen, C2X, CONTENT_Y + 120, gauge_w, 10, us, 0, 200, us_color)
        screen.blit(font_small.render(f"{us:.1f} cm", True, us_color),
                    (C2X + gauge_w - 60, CONTENT_Y + 100))

        # ── Columna 3: estado del sistema + botones ───────────────────────────
        lat_ms = (time.time() - last_telem_time) * 1000
        lat_c  = ACCENT if lat_ms < 200 else (WARN if lat_ms < 1000 else DANGER)
        screen.blit(font_med.render("Estado del Sistema", True, TEXT_PRI),
                    (C3X, CONTENT_Y + 10))
        draw_label_value(screen, C3X, CONTENT_Y + 30,
                         "Latencia Telem.", f"{lat_ms:.0f} ms", lat_c)
        draw_label_value(screen, C3X, CONTENT_Y + 50,
                         "Conexión", conn_txt, conn_color)
        draw_label_value(screen, C3X, CONTENT_Y + 70,
                         "FPS", f"{clock.get_fps():.0f}", TEXT_DIM)
        draw_label_value(screen, C3X, CONTENT_Y + 90,
                         "Velocidad Base", f"{base_speed}", ACCENT2)

        # ── BOTONES ───────────────────────────────────────────────────────────
        BTN_W  = C1_W - 10
        BTN_H  = 32
        BTN_Y1 = CONTENT_Y + 130
        BTN_Y2 = BTN_Y1 + BTN_H + 8

        # Botón GUARDAR MAPA
        saving_active = (time.time() - save_map_feedback_time) < 2.0
        save_hover    = pygame.Rect(C3X, BTN_Y1, BTN_W, BTN_H).collidepoint(mouse_pos)
        save_bg       = (0, 60, 40) if not save_hover else (0, 80, 55)
        save_border   = ACCENT if saving_active else (ACCENT_DIM if not save_hover else ACCENT)
        save_label    = "✓ " + save_map_feedback[:24] if saving_active else "💾  GUARDAR MAPA  (PNG)"
        save_txt_col  = ACCENT if saving_active else TEXT_PRI
        btn_rect_save_map = draw_button(
            screen, (C3X, BTN_Y1, BTN_W, BTN_H),
            save_label, save_bg, save_border, save_txt_col, hover=save_hover
        )

        # Botón LIMPIAR DATOS
        clearing_active = (time.time() - clear_signal_time) < 0.4
        clear_hover     = pygame.Rect(C3X, BTN_Y2, BTN_W, BTN_H).collidepoint(mouse_pos)
        clear_bg        = (50, 30, 10) if not clear_hover else (70, 40, 10)
        clear_border    = WARN if clearing_active else ((60, 50, 20) if not clear_hover else WARN)
        clear_label     = "✓ LIMPIADO"  if clearing_active else "🗑  LIMPIAR DATOS + ENCODERS"
        clear_txt_col   = WARN if clearing_active else TEXT_PRI
        btn_rect_clear_diag = draw_button(
            screen, (C3X, BTN_Y2, BTN_W, BTN_H),
            clear_label, clear_bg, clear_border, clear_txt_col, hover=clear_hover
        )

        # Nota de encoders reseteados
        screen.blit(font_xs.render("Options también manda RESET_ENCODERS al robot",
                                   True, TEXT_DIM),
                    (C3X, BTN_Y2 + BTN_H + 4))

    pygame.display.flip()
    clock.tick(30)

# ─── CIERRE ───────────────────────────────────────────────────────────────────
_stop_motors()
if conectado:
    try:
        client_socket.sendall(b"PWM:0,0\n")
        client_socket.close()
    except Exception:
        pass
pygame.quit()
sys.exit()
