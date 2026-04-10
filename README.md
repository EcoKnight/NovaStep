
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0a0d14;
    --surface: #111520;
    --surface2: #181d2e;
    --border: #1e2840;
    --accent: #00c8ff;
    --accent2: #7b61ff;
    --accent3: #00ffa3;
    --warn: #ffaa00;
    --text: #e4eaf8;
    --muted: #7a8aaa;
    --mono: 'Space Mono', monospace;
    --sans: 'Syne', sans-serif;
  }

  body { background: var(--bg); color: var(--text); font-family: var(--sans); line-height: 1.7; }

  .readme { max-width: 860px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }

  /* HERO */
  .hero { text-align: center; padding: 3rem 0 2rem; border-bottom: 1px solid var(--border); margin-bottom: 2.5rem; position: relative; overflow: hidden; }
  .hero::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse 70% 60% at 50% 0%, rgba(0,200,255,0.07) 0%, transparent 70%); pointer-events: none; }
  .hero-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(0,200,255,0.08); border: 1px solid rgba(0,200,255,0.25); border-radius: 999px; padding: 4px 14px; font-family: var(--mono); font-size: 11px; color: var(--accent); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 1.2rem; }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent3); animation: pulse 1.8s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.3; } }
  .hero h1 { font-size: clamp(2.8rem, 7vw, 4.5rem); font-weight: 800; letter-spacing: -1px; line-height: 1.05; margin-bottom: 0.5rem; background: linear-gradient(135deg, #e4eaf8 30%, var(--accent) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
  .hero-sub { font-family: var(--mono); font-size: 13px; color: var(--muted); letter-spacing: 1px; margin-bottom: 1.8rem; }
  .badges { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
  .badge { font-family: var(--mono); font-size: 11px; padding: 4px 12px; border-radius: 4px; border: 1px solid; }
  .b-cyan { color: var(--accent); border-color: rgba(0,200,255,0.35); background: rgba(0,200,255,0.06); }
  .b-purple { color: #a78bfa; border-color: rgba(123,97,255,0.35); background: rgba(123,97,255,0.06); }
  .b-green { color: var(--accent3); border-color: rgba(0,255,163,0.3); background: rgba(0,255,163,0.05); }
  .b-amber { color: var(--warn); border-color: rgba(255,170,0,0.3); background: rgba(255,170,0,0.05); }

  /* SECTIONS */
  .section { margin-bottom: 2.8rem; }
  .section-title { display: flex; align-items: center; gap: 10px; font-size: 0.8rem; font-family: var(--mono); color: var(--accent); letter-spacing: 3px; text-transform: uppercase; margin-bottom: 1.2rem; }
  .section-title::after { content: ''; flex: 1; height: 1px; background: linear-gradient(to right, var(--border), transparent); }
  .section-title span { white-space: nowrap; }

  /* DESCRIPTION */
  .desc-card { background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 8px; padding: 1.2rem 1.5rem; font-size: 15px; color: var(--muted); line-height: 1.8; }
  .desc-card strong { color: var(--text); }

  /* ARCHITECTURE DIAGRAM */
  .arch-diagram { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }
  .arch-row { display: flex; align-items: center; justify-content: center; gap: 0; margin-bottom: 0; }
  .arch-cols { display: grid; grid-template-columns: 1fr 40px 1fr; gap: 0; align-items: start; margin-top: 0; }

  .node { border-radius: 8px; padding: 0.75rem 1rem; text-align: center; }
  .node-title { font-family: var(--mono); font-size: 11px; font-weight: 700; letter-spacing: 1px; display: block; margin-bottom: 3px; }
  .node-sub { font-size: 11px; color: var(--muted); }

  .node-main { background: rgba(0,200,255,0.08); border: 1px solid rgba(0,200,255,0.3); text-align: center; padding: 1rem; border-radius: 10px; }
  .node-main .node-title { color: var(--accent); font-size: 13px; }

  .core-box { border-radius: 10px; padding: 1rem; }
  .core0 { background: rgba(123,97,255,0.08); border: 1px solid rgba(123,97,255,0.3); }
  .core0 .node-title { color: #a78bfa; }
  .core1 { background: rgba(0,255,163,0.06); border: 1px solid rgba(0,255,163,0.25); }
  .core1 .node-title { color: var(--accent3); }

  .sub-nodes { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
  .sub-node { background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; font-family: var(--mono); font-size: 10px; }
  .sub-node .label { font-size: 10px; color: var(--muted); display: block; }
  .sub-node .val { color: var(--text); }

  .arrow-v { display: flex; flex-direction: column; align-items: center; gap: 0; padding: 6px 0; }
  .arrow-v .line { width: 1px; height: 24px; background: var(--accent); opacity: 0.5; }
  .arrow-v .tip { width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 7px solid var(--accent); opacity: 0.5; }
  .arrow-h { display: flex; align-items: center; height: 100%; justify-content: center; flex-direction: column; }
  .arrow-h .line { height: 1px; width: 28px; background: var(--border); }
  .arrow-h-both { display: flex; align-items: center; gap: 4px; }
  .arrow-h-both .line { height: 1px; flex: 1; background: rgba(0,200,255,0.3); }
  .arrow-h-both .lbl { font-family: var(--mono); font-size: 9px; color: var(--accent); white-space: nowrap; }

  .tcp-row { display: flex; align-items: center; gap: 12px; margin-top: 1.2rem; }
  .tcp-node { flex: 1; background: rgba(255,170,0,0.06); border: 1px solid rgba(255,170,0,0.25); border-radius: 8px; padding: 0.7rem 1rem; }
  .tcp-node .node-title { color: var(--warn); }
  .tcp-line { flex: 0 0 auto; display: flex; flex-direction: column; align-items: center; gap: 2px; }
  .tcp-line .lbl { font-family: var(--mono); font-size: 9px; color: var(--muted); }
  .tcp-dbl { display: flex; align-items: center; gap: 2px; }
  .tcp-dbl .arr { font-size: 14px; color: var(--accent); }

  /* FILTER STACK */
  .filter-stack { display: flex; flex-direction: column; gap: 10px; }
  .filter-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.2rem; display: flex; align-items: flex-start; gap: 12px; }
  .filter-icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 11px; font-weight: 700; flex-shrink: 0; }
  .fi-comp { background: rgba(0,200,255,0.1); color: var(--accent); border: 1px solid rgba(0,200,255,0.2); }
  .fi-ekf { background: rgba(123,97,255,0.1); color: #a78bfa; border: 1px solid rgba(123,97,255,0.2); }
  .filter-body .ftitle { font-size: 14px; font-weight: 700; color: var(--text); }
  .filter-body .fdesc { font-size: 13px; color: var(--muted); margin-top: 3px; }
  .filter-body code { font-family: var(--mono); font-size: 11px; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 1px 6px; color: var(--accent3); }

  /* CONTROL */
  .control-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .ctrl-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1rem; }
  .ctrl-card .ctitle { font-family: var(--mono); font-size: 11px; color: var(--warn); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }
  .ctrl-card p { font-size: 13px; color: var(--muted); }

  /* TELEMETRY */
  .tele-box { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
  .tele-header { background: var(--surface2); border-bottom: 1px solid var(--border); padding: 8px 14px; font-family: var(--mono); font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 8px; }
  .tele-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent3); animation: pulse 1.8s ease-in-out infinite; }
  .tele-body { padding: 1rem 1.2rem; display: flex; flex-direction: column; gap: 8px; }
  .tele-row { display: flex; align-items: center; gap: 10px; }
  .tele-key { font-family: var(--mono); font-size: 12px; color: var(--accent); min-width: 130px; }
  .tele-sep { color: var(--border); font-family: var(--mono); }
  .tele-val { font-size: 12px; color: var(--muted); }

  /* HARDWARE TABLE */
  .hw-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .hw-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1rem; display: flex; align-items: flex-start; gap: 12px; }
  .hw-icon { width: 32px; height: 32px; border-radius: 6px; background: rgba(0,200,255,0.08); border: 1px solid rgba(0,200,255,0.2); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .hw-icon svg { width: 16px; height: 16px; stroke: var(--accent); fill: none; stroke-width: 1.5; }
  .hw-info .hname { font-size: 13px; font-weight: 700; color: var(--text); }
  .hw-info .hdesc { font-size: 12px; color: var(--muted); margin-top: 2px; }

  @media (max-width: 580px) {
    .control-grid, .hw-grid { grid-template-columns: 1fr; }
    .arch-cols { grid-template-columns: 1fr 30px 1fr; }
  }
</style>

<div class="readme">

  <!-- HERO -->
  <div class="hero">
    <div class="hero-badge"><div class="dot"></div> SISTEMA ACTIVO · v2.0</div>
    <h1>NovaStep</h1>
    <div class="hero-sub">ROBÓTICA MÓVIL · SENSOR FUSION · CONTROL DISTRIBUIDO</div>
    <div class="badges">
      <span class="badge b-cyan">FreeRTOS</span>
      <span class="badge b-purple">EKF · Kalman</span>
      <span class="badge b-green">ESP32 Dual-Core</span>
      <span class="badge b-amber">TCP/IP Telemetría</span>
      <span class="badge b-cyan">PD Control</span>
      <span class="badge b-purple">AS5600 · MPU6050</span>
    </div>
  </div>

  <!-- DESCRIPCIÓN -->
  <div class="section">
    <div class="section-title"><span>// descripción</span></div>
    <div class="desc-card">
      <strong>NovaBot</strong> es un robot diferencial avanzado que integra técnicas de <strong>Sensor Fusion</strong> y <strong>Sistemas de Tiempo Real (RTOS)</strong> para lograr una navegación precisa. El sistema separa las tareas críticas — control de motores y lectura de sensores — en el microcontrolador <strong>ESP32</strong>, mientras que el procesamiento de datos y la interfaz de usuario se gestionan de forma remota vía <strong>TCP/IP</strong>.
    </div>
  </div>

  <!-- ARQUITECTURA -->
  <div class="section">
    <div class="section-title"><span>// arquitectura de software</span></div>
    <div class="arch-diagram">

      <!-- ESP32 label -->
      <div style="text-align:center; margin-bottom:12px;">
        <span style="font-family:var(--mono);font-size:10px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;">ESP32 · FreeRTOS</span>
      </div>

      <!-- Two cores -->
      <div class="arch-cols">
        <div class="core-box core0">
          <div class="node-title">CORE 0</div>
          <div class="node-sub" style="margin-bottom:10px;">NetworkTask</div>
          <div class="sub-nodes">
            <div class="sub-node"><span class="label">Protocolo</span><span class="val">Servidor TCP</span></div>
            <div class="sub-node"><span class="label">Tarea</span><span class="val">Parseo de comandos</span></div>
            <div class="sub-node"><span class="label">Link</span><span class="val">Wi-Fi inalámbrico</span></div>
          </div>
        </div>

        <div class="arrow-h" style="padding-top:12px;">
          <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
            <div style="font-family:var(--mono);font-size:8px;color:var(--muted);">IPC</div>
            <div style="font-size:16px;color:var(--border);">⇄</div>
          </div>
        </div>

        <div class="core-box core1">
          <div class="node-title">CORE 1</div>
          <div class="node-sub" style="margin-bottom:10px;">Main Loop · 50 Hz</div>
          <div class="sub-nodes">
            <div class="sub-node"><span class="label">Control</span><span class="val">Ciclo PD motores</span></div>
            <div class="sub-node"><span class="label">Sensor</span><span class="val">UltrasonicTask</span></div>
            <div class="sub-node"><span class="label">Filtro</span><span class="val">EKF → odometría</span></div>
          </div>
        </div>
      </div>

      <!-- Arrow down -->
      <div style="display:flex;justify-content:center;margin:14px 0;">
        <div class="arrow-v"><div class="line"></div><div class="tip"></div></div>
      </div>

      <!-- TCP/IP remote -->
      <div class="tcp-row">
        <div class="tcp-node">
          <div class="node-title">INTERFAZ REMOTA</div>
          <div class="node-sub">Dashboard · Telemetría · Comandos</div>
        </div>
        <div class="tcp-line">
          <div class="lbl">TCP/IP</div>
          <div class="tcp-dbl"><span class="arr">⇆</span></div>
          <div class="lbl">100 ms</div>
        </div>
        <div class="tcp-node" style="text-align:right;">
          <div class="node-title">WATCHDOG</div>
          <div class="node-sub">Timeout > 1s → STOP</div>
        </div>
      </div>

    </div>
  </div>

  <!-- ESTIMACIÓN DE ESTADO -->
  <div class="section">
    <div class="section-title"><span>// estimación de estado · sensor fusion</span></div>
    <div class="filter-stack">
      <div class="filter-card">
        <div class="filter-icon fi-comp">FC</div>
        <div class="filter-body">
          <div class="ftitle">Filtro Complementario</div>
          <div class="fdesc">Fusiona <code>AS5600</code> (encoders magnéticos) con el giroscopio <code>MPU6050</code> para obtener un yaw (θ) estable y libre de drift a largo plazo.</div>
        </div>
      </div>
      <div style="display:flex;justify-content:center;">
        <div class="arrow-v"><div class="line"></div><div class="tip"></div></div>
      </div>
      <div class="filter-card">
        <div class="filter-icon fi-ekf">EKF</div>
        <div class="filter-body">
          <div class="ftitle">Filtro de Kalman Extendido</div>
          <div class="fdesc">Calcula posición <code>(x, y)</code> y orientación mediante predicción cinemática + corrección por observación del sensor. Implementado con <code>BasicLinearAlgebra</code>.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- CONTROL -->
  <div class="section">
    <div class="section-title"><span>// control de movimiento</span></div>
    <div class="control-grid">
      <div class="ctrl-card">
        <div class="ctitle">Control PD · Velocidad</div>
        <p>Controlador Proporcional-Derivativo independiente por rueda. Ajusta el PWM para igualar la velocidad de los encoders con la referencia del usuario.</p>
      </div>
      <div class="ctrl-card">
        <div class="ctitle">Zona Muerta</div>
        <p>Algoritmo de compensación de fricción estática para garantizar movimientos suaves y precisos a baja velocidad sin oscilaciones.</p>
      </div>
      <div class="ctrl-card">
        <div class="ctitle">Software Watchdog</div>
        <p>Detención automática del robot ante pérdida de conexión TCP superior a <strong style="color:var(--text);">1 segundo</strong>. Seguridad por hardware en capa de firmware.</p>
      </div>
      <div class="ctrl-card">
        <div class="ctitle">Drivers · PWM</div>
        <p>Puente H para motores DC con señal PWM a <strong style="color:var(--text);">20 kHz</strong> para operar fuera del rango audible y reducir ruido al mínimo.</p>
      </div>
    </div>
  </div>

  <!-- TELEMETRÍA -->
  <div class="section">
    <div class="section-title"><span>// protocolo de telemetría · 10 Hz</span></div>
    <div class="tele-box">
      <div class="tele-header"><div class="tele-dot"></div> stream uart · tcp/ip · cada 100ms</div>
      <div class="tele-body">
        <div class="tele-row">
          <span class="tele-key">POS_X, POS_Y, THETA</span>
          <span class="tele-sep">→</span>
          <span class="tele-val">Odometría pura vs. estimación EKF</span>
        </div>
        <div class="tele-row">
          <span class="tele-key">ROLL, PITCH, YAW</span>
          <span class="tele-sep">→</span>
          <span class="tele-val">Orientación absoluta IMU fusionada</span>
        </div>
        <div class="tele-row">
          <span class="tele-key">US_DIST</span>
          <span class="tele-sep">→</span>
          <span class="tele-val">Distancia a obstáculos (filtrada)</span>
        </div>
        <div class="tele-row">
          <span class="tele-key">CMD_L, CMD_R</span>
          <span class="tele-sep">→</span>
          <span class="tele-val">Comandos enviados vs. PWM aplicado</span>
        </div>
      </div>
    </div>
  </div>

  <!-- HARDWARE -->
  <div class="section">
    <div class="section-title"><span>// conexiones y hardware</span></div>
    <div class="hw-grid">
      <div class="hw-card">
        <div class="hw-icon">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>
        </div>
        <div class="hw-info">
          <div class="hname">AS5600 × 2</div>
          <div class="hdesc">Encoders magnéticos · Dual I²C (Wire + Wire1) para evitar colisión de direcciones</div>
        </div>
      </div>
      <div class="hw-card">
        <div class="hw-icon">
          <svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="10" rx="1"/><path d="M7 7V5M12 7V5M17 7V5M7 17v2M12 17v2M17 17v2"/></svg>
        </div>
        <div class="hw-info">
          <div class="hname">MPU6050</div>
          <div class="hdesc">IMU 6-DOF · Giroscopio + Acelerómetro · I²C · Fusión con FC + EKF</div>
        </div>
      </div>
      <div class="hw-card">
        <div class="hw-icon">
          <svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        </div>
        <div class="hw-info">
          <div class="hname">HC-SR04</div>
          <div class="hdesc">Sensor ultrasónico · Lib NewPing · Filtrado por media móvil</div>
        </div>
      </div>
      <div class="hw-card">
        <div class="hw-icon">
          <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="hw-info">
          <div class="hname">Puente H</div>
          <div class="hdesc">Driver motores DC · PWM @ 20 kHz · Sin ruido auditivo</div>
        </div>
      </div>
    </div>
  </div>

</div>
