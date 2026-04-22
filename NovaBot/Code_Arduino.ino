#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <NewPing.h>
#include <math.h>
#include <AS5600.h>
#include <BasicLinearAlgebra.h>
 
// I. RED / RTOS 
const int TCP_PORT = 8080;
WiFiServer server(TCP_PORT);
WiFiClient activeClient;
SemaphoreHandle_t lock;

// II. HARDWARE 
Adafruit_MPU6050 mpu;

// ---------------- Motores ----------------
const int MI_PWM_PIN = 32;
const int MI_IN1     = 25;
const int MI_IN2     = 33;

const int MD_PWM_PIN = 26;
const int MD_IN3     = 27;
const int MD_IN4     = 14;

const int FRECUENCIA_PWM = 20000;

// ---------------- Encoders AS5600 ----------------
AS5600 encoderIzq(&Wire1);
AS5600 encoderDer(&Wire);

// ---------------- Ultrasonido ----------------
const int US_TRIG = 18;
const int US_ECHO = 19;
const int MAX_DISTANCE = 200;
NewPing sonar(US_TRIG, US_ECHO, MAX_DISTANCE);
volatile float distancia_us_filtrada = 200.0f;

// ---------------- Buzzer ----------------
const int PIN_BUZZER = 4;

// III. PARÁMETROS GLOBALES DEL ROBOT 
const int   TICKS_POR_VUELTA = 4096;
const float RADIO_RUEDA      = 0.0656f;   // m
const float DISTANCIA_RUEDAS = 0.163f;    // m
const unsigned long DT_CONTROL_MS = 20;   // 50 Hz
const unsigned long WATCHDOG_TIMEOUT_MS = 1000;

const int ENC_SIGN_LEFT  = 1;
const int ENC_SIGN_RIGHT = 1;

const int CMD_PWM_MAX = 50;
const float MAX_WHEEL_SPEED_MPS = 0.80f;
const int MIN_EFFECTIVE_PWM = 10;

// Si al corregir yaw el robot corrige al lado equivocado, cambiar a -1
const int YAW_CORR_SIGN = 1;

volatile int cmd_pwm_left  = 0;
volatile int cmd_pwm_right = 0;
volatile int applied_pwm_left  = 0;
volatile int applied_pwm_right = 0;

long pulsos_izq = 0;
long pulsos_der = 0;
long offset_izq = 0;
long offset_der = 0;

volatile bool flag_buzzer = false;
volatile bool flag_reset  = false;
volatile unsigned long last_cmd_time = 0;
 
// IV. CONTROL POR RUEDA (PD) 
const float KP_MOTOR_LEFT  = 2.5f;
const float KD_MOTOR_LEFT  = 0.1f;
const float KP_MOTOR_RIGHT = 2.5f;
const float KD_MOTOR_RIGHT = 0.1f;

class MotorPDController {
public:
    float kp;
    float kd;
    float prev_error;

    MotorPDController(float _kp = 0.0f, float _kd = 0.0f) {
        kp = _kp;
        kd = _kd;
        prev_error = 0.0f;
    }

    void reset() {
        prev_error = 0.0f;
    }

    int update(int cmd_base, float v_ref, float v_meas, float dt) {
        float error = v_ref - v_meas;
        float derror = (error - prev_error) / max(dt, 1e-6f);

        float control = (float)cmd_base + kp * error + kd * derror;
        prev_error = error;

        int pwm = (int)round(control);
        pwm = constrain(pwm, -CMD_PWM_MAX, CMD_PWM_MAX);

        if (cmd_base != 0 && pwm != 0 && abs(pwm) < MIN_EFFECTIVE_PWM) {
            pwm = (pwm > 0) ? MIN_EFFECTIVE_PWM : -MIN_EFFECTIVE_PWM;
        }
        return pwm;
    }
};

MotorPDController pdLeft(KP_MOTOR_LEFT, KD_MOTOR_LEFT);
MotorPDController pdRight(KP_MOTOR_RIGHT, KD_MOTOR_RIGHT);

// V. ODOMETRÍA + EKF 
class FusedOdometry {
public:
    float wheel_radius, wheel_base, meters_per_tick;
    float x = 0, y = 0, theta = 0;
    float roll = 0, pitch = 0, yaw = 0;
    float vx = 0, omega = 0;
    long prev_left_ticks = 0, prev_right_ticks = 0;
    float alpha_imu = 0.98f, alpha_yaw = 0.95f;

    FusedOdometry(float r, float b, int ticks) {
        wheel_radius    = r;
        wheel_base      = b;
        meters_per_tick = (2.0f * PI * wheel_radius) / ticks;
    }

    void reset() {
        x = 0; y = 0; theta = 0;
        roll = 0; pitch = 0; yaw = 0;
        vx = 0; omega = 0;
        prev_left_ticks = 0;
        prev_right_ticks = 0;
    }

    void update(long left_ticks, long right_ticks,
                float ax, float ay, float az,
                float gx, float gy, float gz, float dt) {

        float delta_left  = (left_ticks  - prev_left_ticks)  * meters_per_tick;
        float delta_right = (right_ticks - prev_right_ticks) * meters_per_tick;

        prev_left_ticks  = left_ticks;
        prev_right_ticks = right_ticks;

        float delta_theta_encoders = (delta_right - delta_left) / wheel_base;
        float delta_theta_gyro     = gz * dt;

        float delta_theta = alpha_yaw * delta_theta_gyro +
                            (1.0f - alpha_yaw) * delta_theta_encoders;

        theta += delta_theta;
        theta  = atan2(sin(theta), cos(theta));

        yaw += delta_theta_gyro;
        yaw  = atan2(sin(yaw), cos(yaw));

        float delta_distance = (delta_left + delta_right) / 2.0f;

        vx    = (dt > 0) ? delta_distance / dt : 0.0f;
        omega = (dt > 0) ? delta_theta / dt    : 0.0f;

        x += delta_distance * cos(theta);
        y += delta_distance * sin(theta);

        float roll_accel  = atan2(ay, az) * 180.0f / PI;
        float pitch_accel = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0f / PI;

        roll  = alpha_imu * (roll  + (gx * 180.0f / PI) * dt) + (1.0f - alpha_imu) * roll_accel;
        pitch = alpha_imu * (pitch + (gy * 180.0f / PI) * dt) + (1.0f - alpha_imu) * pitch_accel;
    }
};

class EKFOdometry {
private:
    BLA::Matrix<3, 1> X_est;
    BLA::Matrix<3, 3> P;
    BLA::Matrix<3, 3> Q;
    BLA::Matrix<1, 1> R;
    BLA::Matrix<1, 3> H;
    BLA::Matrix<3, 3> I_mat;
    float distancia_ruedas;

    float saved_var_q_x, saved_var_q_y, saved_var_q_theta, saved_var_r_imu;

public:
    EKFOdometry(float dist_ruedas,
                float var_q_x, float var_q_y, float var_q_theta,
                float var_r_imu) {
        distancia_ruedas   = dist_ruedas;
        saved_var_q_x      = var_q_x;
        saved_var_q_y      = var_q_y;
        saved_var_q_theta  = var_q_theta;
        saved_var_r_imu    = var_r_imu;
        _init(var_q_x, var_q_y, var_q_theta, var_r_imu);
    }

    void reset() {
        _init(saved_var_q_x, saved_var_q_y, saved_var_q_theta, saved_var_r_imu);
    }

    void update(float v_izq, float v_der, float dt, float sensor_yaw) {
        float Vel_Lineal  = (v_der + v_izq) / 2.0f;
        float Vel_Angular = (v_der - v_izq) / distancia_ruedas;
        float theta_prev  = X_est(2);

        X_est(0) += Vel_Lineal * cos(theta_prev) * dt;
        X_est(1) += Vel_Lineal * sin(theta_prev) * dt;
        X_est(2) += Vel_Angular * dt;
        X_est(2) = atan2(sin(X_est(2)), cos(X_est(2)));

        BLA::Matrix<3, 3> F = {
            1.0f, 0.0f, -Vel_Lineal * sin(theta_prev) * dt,
            0.0f, 1.0f,  Vel_Lineal * cos(theta_prev) * dt,
            0.0f, 0.0f,  1.0f
        };

        P = F * P * ~F + Q;

        BLA::Matrix<1, 1> Z = {sensor_yaw};
        BLA::Matrix<1, 1> Y = Z - H * X_est;
        Y(0) = atan2(sin(Y(0)), cos(Y(0)));

        BLA::Matrix<1, 1> S = H * P * ~H + R;
        BLA::Matrix<3, 1> K = P * ~H * BLA::Inverse(S);

        X_est = X_est + K * Y;
        P = (I_mat - K * H) * P;
    }

    float getX()     { return X_est(0); }
    float getY()     { return X_est(1); }
    float getTheta() { return X_est(2); }

private:
    void _init(float var_q_x, float var_q_y, float var_q_theta, float var_r_imu) {
        X_est = {0.0f, 0.0f, 0.0f};

        P = {0.1f, 0.0f, 0.0f,
             0.0f, 0.1f, 0.0f,
             0.0f, 0.0f, 0.1f};

        Q = {var_q_x,    0.0f,      0.0f,
             0.0f,       var_q_y,   0.0f,
             0.0f,       0.0f,      var_q_theta};

        R = {var_r_imu};
        H = {0.0f, 0.0f, 1.0f};

        I_mat = {1.0f, 0.0f, 0.0f,
                 0.0f, 1.0f, 0.0f,
                 0.0f, 0.0f, 1.0f};
    }
};

FusedOdometry odom(RADIO_RUEDA, DISTANCIA_RUEDAS, TICKS_POR_VUELTA);
EKFOdometry   mi_ekf(DISTANCIA_RUEDAS, 0.01f, 0.01f, 0.05f, 0.002f);

// VI. MODO DE CONTROL / OBJETIVOS DE ALTO NIVEL 
enum ControlMode {
    MODE_MANUAL_PWM = 0,
    MODE_GOAL_DIST  = 1,
    MODE_GOAL_TURN  = 2,
    MODE_GOAL_SPIN  = 3
};

volatile ControlMode control_mode = MODE_MANUAL_PWM;

struct AutoGoalState {
    bool active = false;

    // meta de distancia
    float start_x = 0.0f;
    float start_y = 0.0f;
    float target_dist_m = 0.0f;
    int   dist_base_pwm = 22;
    float dist_yaw_ref = 0.0f;
    float dist_prev_yaw_err = 0.0f;

    // meta de giro
    float turn_target_yaw = 0.0f;
    float turn_prev_err = 0.0f;

    // meta de spin 360 acumulado
    float spin_accum_deg = 0.0f;
    float spin_prev_yaw_deg = 0.0f;
    int   spin_dir = 1; // +1 CCW, -1 CW
};

AutoGoalState autoGoal;

// Control de recta (yaw hold / distancia)
const int   MANUAL_YAW_HOLD_CMD_MIN      = 8;
const int   MANUAL_YAW_HOLD_DIFF_CMD_MAX = 4;
const float MANUAL_YAW_KP = 14.0f;   // PWM/rad
const float MANUAL_YAW_KD = 1.8f;    // PWM*s/rad
bool  manual_yaw_hold_active = false;
float manual_yaw_ref_rad = 0.0f;
float manual_yaw_prev_err = 0.0f;

const float GOAL_DIST_TOL_M = 0.03f;
const float GOAL_DIST_YAW_KP = 16.0f;
const float GOAL_DIST_YAW_KD = 2.0f;
const float GOAL_DIST_APPROACH_GAIN = 35.0f; // PWM por metro restante
const int   GOAL_DIST_MIN_PWM = 14;
const int   GOAL_DIST_MAX_PWM = 28;
const float GOAL_OBSTACLE_STOP_CM = 18.0f;

const float GOAL_TURN_TOL_DEG = 3.0f;
const float GOAL_TURN_KP = 1.15f;  // PWM/deg
const float GOAL_TURN_KD = 0.10f;  // PWM*s/deg
const int   GOAL_TURN_MIN_PWM = 12;
const int   GOAL_TURN_MAX_PWM = 30;

// VII. UTILIDADES
void hacer_beep(int duracion_ms, int freq = 1000) {
    ledcAttach(PIN_BUZZER, freq, 8);
    ledcWrite(PIN_BUZZER, 128);
    delay(duracion_ms);
    ledcWrite(PIN_BUZZER, 0);
}

int calcular_duty(int velocidad_abs) {
    velocidad_abs = constrain(velocidad_abs, 0, CMD_PWM_MAX);
    return map(velocidad_abs, 0, CMD_PWM_MAX, 0, 255);
}
void apply_motors(int pwm_izq, int pwm_der) {
    ledcWrite(MI_PWM_PIN, calcular_duty(abs(pwm_izq)));
    if      (pwm_izq > 0) { digitalWrite(MI_IN1, HIGH); digitalWrite(MI_IN2, LOW);  }
    else if (pwm_izq < 0) { digitalWrite(MI_IN1, LOW);  digitalWrite(MI_IN2, HIGH); }
    else                  { digitalWrite(MI_IN1, LOW);  digitalWrite(MI_IN2, LOW);  }

    ledcWrite(MD_PWM_PIN, calcular_duty(abs(pwm_der)));
    if      (pwm_der > 0) { digitalWrite(MD_IN3, HIGH); digitalWrite(MD_IN4, LOW);  }
    else if (pwm_der < 0) { digitalWrite(MD_IN3, LOW);  digitalWrite(MD_IN4, HIGH); }
    else                  { digitalWrite(MD_IN3, LOW);  digitalWrite(MD_IN4, LOW);  }
}

float pwmCmdToSpeedRef(int cmd_pwm) {
    float norm = (float)cmd_pwm / (float)CMD_PWM_MAX;
    norm = constrain(norm, -1.0f, 1.0f);
    return norm * MAX_WHEEL_SPEED_MPS;
}

float angleDiffRad(float a, float b) {
    float d = a - b;
    while (d >  PI) d -= 2.0f * PI;
    while (d < -PI) d += 2.0f * PI;
    return d;
}

float angleDiffDeg(float a, float b) {
    float d = a - b;
    while (d >  180.0f) d -= 360.0f;
    while (d < -180.0f) d += 360.0f;
    return d;
}

void reset_all_control_states() {
    pdLeft.reset();
    pdRight.reset();

    manual_yaw_hold_active = false;
    manual_yaw_ref_rad = 0.0f;
    manual_yaw_prev_err = 0.0f;

    autoGoal = AutoGoalState();
    control_mode = MODE_MANUAL_PWM;
}

void motor_parar() {
    cmd_pwm_left = 0;
    cmd_pwm_right = 0;
    applied_pwm_left = 0;
    applied_pwm_right = 0;

    reset_all_control_states();
    apply_motors(0, 0);
}

void start_distance_goal(float dist_m) {
    autoGoal = AutoGoalState();
    autoGoal.active = true;
    autoGoal.start_x = odom.x;
    autoGoal.start_y = odom.y;
    autoGoal.target_dist_m = fabs(dist_m);
    autoGoal.dist_base_pwm = (dist_m >= 0.0f) ? 22 : -22;
    autoGoal.dist_yaw_ref = odom.yaw;
    autoGoal.dist_prev_yaw_err = 0.0f;
    control_mode = MODE_GOAL_DIST;
}

void start_turn_goal_deg(float delta_deg) {
    autoGoal = AutoGoalState();
    autoGoal.active = true;
    float yaw_now_deg = odom.yaw * 180.0f / PI;
    float target_deg = yaw_now_deg + delta_deg;
    while (target_deg > 180.0f) target_deg -= 360.0f;
    while (target_deg < -180.0f) target_deg += 360.0f;

    autoGoal.turn_target_yaw = target_deg;
    autoGoal.turn_prev_err = 0.0f;
    control_mode = MODE_GOAL_TURN;
}

void start_spin_goal_deg(float degrees) {
    autoGoal = AutoGoalState();
    autoGoal.active = true;
    autoGoal.spin_accum_deg = 0.0f;
    autoGoal.spin_prev_yaw_deg = odom.yaw * 180.0f / PI;
    autoGoal.spin_dir = (degrees >= 0.0f) ? 1 : -1;
    autoGoal.turn_target_yaw = fabs(degrees);
    control_mode = MODE_GOAL_SPIN;
}

// VIII. RED / PARSER DE COMANDOS
void parseCommandLine(const String &line) {
    if (line.length() == 0 || line == "PING") {
        last_cmd_time = millis();
        return;
    }

    last_cmd_time = millis();

    // PWM:R,L     
    if (line.startsWith("PWM:")) {
        int commaIdx = line.indexOf(',', 4);
        if (commaIdx != -1) {
            int rx_right = line.substring(4, commaIdx).toInt();
            int rx_left  = line.substring(commaIdx + 1).toInt();

            rx_left  = constrain(rx_left,  -CMD_PWM_MAX, CMD_PWM_MAX);
            rx_right = constrain(rx_right, -CMD_PWM_MAX, CMD_PWM_MAX);

            xSemaphoreTake(lock, portMAX_DELAY);
            control_mode = MODE_MANUAL_PWM;
            autoGoal.active = false;
            autoGoal.turn_prev_err = 0.0f;
            autoGoal.dist_prev_yaw_err = 0.0f;
            cmd_pwm_right = rx_right;
            cmd_pwm_left  = rx_left;
            xSemaphoreGive(lock);
        }
        return;
    }

    // STOP / GOAL:stop
    if (line == "GOAL:stop" || line == "STOP") {
        xSemaphoreTake(lock, portMAX_DELAY);
        motor_parar();
        xSemaphoreGive(lock);
        return;
    }

    // BUZZER / RESET
    if (line == "BUZZER:PLAY") {
        flag_buzzer = true;
        return;
    }
    if (line == "RESET_ENCODERS" || line == "RESET_ODOM") {
        flag_reset = true;
        return;
    }

    // AUTO:DIST:1.0    -> avanza 1m
    // AUTO:DIST:-1.0   -> retrocede 1m
    if (line.startsWith("AUTO:DIST:")) {
        float dist_m = line.substring(10).toFloat();
        xSemaphoreTake(lock, portMAX_DELAY);
        start_distance_goal(dist_m);
        xSemaphoreGive(lock);
        return;
    }

    // AUTO:TURN:90     -> gira 90°
    // AUTO:TURN:-90    -> gira -90°
    if (line.startsWith("AUTO:TURN:")) {
        float deg = line.substring(10).toFloat();
        xSemaphoreTake(lock, portMAX_DELAY);
        start_turn_goal_deg(deg);
        xSemaphoreGive(lock);
        return;
    }
    // AUTO:SPIN:360    -> giro acumulado 360°
    // AUTO:SPIN:-360   -> giro acumulado horario
    if (line.startsWith("AUTO:SPIN:")) {
        float deg = line.substring(10).toFloat();
        xSemaphoreTake(lock, portMAX_DELAY);
        start_spin_goal_deg(deg);
        xSemaphoreGive(lock);
        return;
    }
}

void networkTask(void *pvParameters) {
    String buffer = "";
    bool was_connected = false;
    while (true) {
        if (activeClient && !activeClient.connected()) {
            activeClient.stop();
            was_connected = false;

            xSemaphoreTake(lock, portMAX_DELAY);
            motor_parar();
            xSemaphoreGive(lock);
        }
        if (!activeClient) {
            activeClient = server.available();
        }
        if (activeClient && activeClient.connected()) {
            if (!was_connected) {
                hacer_beep(100, 2000);
                delay(50);
                hacer_beep(150, 2500);
                was_connected = true;
                buffer = "";
                last_cmd_time = millis();
            }
            while (activeClient.available()) {
                char c = activeClient.read();
                buffer += c;
                if (buffer.length() > 256) buffer = "";

                int newlineIdx = buffer.indexOf('\n');
                if (newlineIdx != -1) {
                    String line = buffer.substring(0, newlineIdx);
                    line.trim();
                    buffer = buffer.substring(newlineIdx + 1);
                    parseCommandLine(line);
                }
            }
        }
        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}

void ultrasonicTask(void *pvParameters) {
    while (true) {
        int ping_us = sonar.ping();
        float raw_cm = 200.0f;
        if (ping_us > 0) raw_cm = ping_us / (float)US_ROUNDTRIP_CM;
        distancia_us_filtrada = 0.45f * raw_cm + 0.55f * distancia_us_filtrada;
        vTaskDelay(50 / portTICK_PERIOD_MS);
    }
}

// IX. CONTROL DE ALTO NIVEL (genera cmdL/cmdR)
void computeManualCommands(float yaw_now_rad, float dt, int &cmdL, int &cmdR) {
    cmdL = cmd_pwm_left;
    cmdR = cmd_pwm_right;

    bool moving_enough  = (abs(cmdL) >= MANUAL_YAW_HOLD_CMD_MIN || abs(cmdR) >= MANUAL_YAW_HOLD_CMD_MIN);
    bool nearly_straight = (abs(cmdL - cmdR) <= MANUAL_YAW_HOLD_DIFF_CMD_MAX);

    if (moving_enough && nearly_straight) {
        if (!manual_yaw_hold_active) {
            manual_yaw_hold_active = true;
            manual_yaw_ref_rad = yaw_now_rad;
            manual_yaw_prev_err = 0.0f;
        }
        float err = angleDiffRad(manual_yaw_ref_rad, yaw_now_rad);
        float derr = (err - manual_yaw_prev_err) / max(dt, 1e-6f);
        manual_yaw_prev_err = err;

        int corr = (int)round((MANUAL_YAW_KP * err + MANUAL_YAW_KD * derr) * YAW_CORR_SIGN);

        int motion_sign = (cmdL + cmdR >= 0) ? 1 : -1;
        cmdL -= motion_sign * corr;
        cmdR += motion_sign * corr;
        cmdL = constrain(cmdL, -CMD_PWM_MAX, CMD_PWM_MAX);
        cmdR = constrain(cmdR, -CMD_PWM_MAX, CMD_PWM_MAX);
    } else {
        manual_yaw_hold_active = false;
        manual_yaw_prev_err = 0.0f;
    }
}

void computeDistanceGoalCommands(float yaw_now_rad, int &cmdL, int &cmdR, float dt) {
    float dx = odom.x - autoGoal.start_x;
    float dy = odom.y - autoGoal.start_y;
    float dist_done = sqrt(dx * dx + dy * dy);
    float remaining = autoGoal.target_dist_m - dist_done;

    if (distancia_us_filtrada < GOAL_OBSTACLE_STOP_CM && autoGoal.dist_base_pwm > 0) {
        motor_parar();
        return;
    }
    if (remaining <= GOAL_DIST_TOL_M) {
        motor_parar();
        return;
    }
    int motion_sign = (autoGoal.dist_base_pwm >= 0) ? 1 : -1;

    int base_pwm = (int)round(remaining * GOAL_DIST_APPROACH_GAIN);
    base_pwm = constrain(base_pwm, GOAL_DIST_MIN_PWM, GOAL_DIST_MAX_PWM);
    base_pwm *= motion_sign;

    float yaw_err = angleDiffRad(autoGoal.dist_yaw_ref, yaw_now_rad);
    float yaw_derr = (yaw_err - autoGoal.dist_prev_yaw_err) / max(dt, 1e-6f);
    autoGoal.dist_prev_yaw_err = yaw_err;

    int corr = (int)round((GOAL_DIST_YAW_KP * yaw_err + GOAL_DIST_YAW_KD * yaw_derr) * YAW_CORR_SIGN);

    cmdL = base_pwm - motion_sign * corr;
    cmdR = base_pwm + motion_sign * corr;

    cmdL = constrain(cmdL, -CMD_PWM_MAX, CMD_PWM_MAX);
    cmdR = constrain(cmdR, -CMD_PWM_MAX, CMD_PWM_MAX);
}

void computeTurnGoalCommands(float yaw_now_deg, int &cmdL, int &cmdR, float dt) {
    float err = angleDiffDeg(autoGoal.turn_target_yaw, yaw_now_deg);
    if (fabs(err) <= GOAL_TURN_TOL_DEG) {
        motor_parar();
        return;
    }
    float derr = (err - autoGoal.turn_prev_err) / max(dt, 1e-6f);
    autoGoal.turn_prev_err = err;

    int turn_pwm = (int)round(fabs(GOAL_TURN_KP * err + GOAL_TURN_KD * derr));
    turn_pwm = constrain(turn_pwm, GOAL_TURN_MIN_PWM, GOAL_TURN_MAX_PWM);
    if (err > 0.0f) {
        cmdL = -turn_pwm;
        cmdR = +turn_pwm;
    } else {
        cmdL = +turn_pwm;
        cmdR = -turn_pwm;
    }
}

void computeSpinGoalCommands(float yaw_now_deg, int &cmdL, int &cmdR, float dt) {
    (void)dt;
    float delta = angleDiffDeg(yaw_now_deg, autoGoal.spin_prev_yaw_deg);
    autoGoal.spin_prev_yaw_deg = yaw_now_deg;
    if (autoGoal.spin_dir > 0) {
        autoGoal.spin_accum_deg += delta;
    } else {
        autoGoal.spin_accum_deg -= delta;
    }
    if (autoGoal.spin_accum_deg < 0.0f) autoGoal.spin_accum_deg = 0.0f;

    float remaining = autoGoal.turn_target_yaw - autoGoal.spin_accum_deg;
    if (remaining <= GOAL_TURN_TOL_DEG) {
        motor_parar();
        return;
    }

    int turn_pwm = (int)round(remaining * 0.25f);
    turn_pwm = constrain(turn_pwm, GOAL_TURN_MIN_PWM, GOAL_TURN_MAX_PWM);
    if (autoGoal.spin_dir > 0) {
        cmdL = -turn_pwm;
        cmdR = +turn_pwm;
    } else {
        cmdL = +turn_pwm;
        cmdR = -turn_pwm;
    }
}

// X. SETUP
void setup() {
    Serial.begin(115200);

    Wire.begin(21, 22);
    Wire1.begin(16, 17);
    Wire.setClock(400000);
    Wire1.setClock(400000);

    encoderIzq.begin();
    encoderDer.begin();

    lock = xSemaphoreCreateMutex();

    pinMode(MD_IN3, OUTPUT);
    pinMode(MD_IN4, OUTPUT);
    pinMode(MI_IN1, OUTPUT);
    pinMode(MI_IN2, OUTPUT);

    ledcAttach(MD_PWM_PIN, FRECUENCIA_PWM, 8);
    ledcAttach(MI_PWM_PIN, FRECUENCIA_PWM, 8);

    if (!mpu.begin()) {
        Serial.println("¡Error al encontrar el MPU6050!");
    } else {
        mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
        mpu.setGyroRange(MPU6050_RANGE_250_DEG);
        mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
        Serial.println("MPU6050 inicializado");
    }

    WiFi.softAP("NovaBot ESP32", "novastep");
    server.begin();
    last_cmd_time = millis();

    xTaskCreatePinnedToCore(networkTask,    "RedTask", 8192, NULL, 1, NULL, 0);
    xTaskCreatePinnedToCore(ultrasonicTask, "USTask",  4096, NULL, 1, NULL, 0);

    hacer_beep(150, 1000);
    delay(100);
    hacer_beep(150, 1000);
}

// XI. LOOP PRINCIPAL
void loop() {
    static unsigned long last_control_time   = millis();
    static unsigned long last_telemetry_time = millis();
    static long prev_pulsos_izq = 0;
    static long prev_pulsos_der = 0;

    unsigned long current_time = millis();
    unsigned long dt_ms = current_time - last_control_time;

    if (flag_buzzer) {
        flag_buzzer = false;
        hacer_beep(500, 1000);
    }

    if (flag_reset) {
        flag_reset = false;
        xSemaphoreTake(lock, portMAX_DELAY);

        offset_izq = encoderIzq.getCumulativePosition();
        offset_der = encoderDer.getCumulativePosition();

        odom.reset();
        mi_ekf.reset();

        prev_pulsos_izq = 0;
        prev_pulsos_der = 0;

        reset_all_control_states();

        xSemaphoreGive(lock);
        Serial.println("Encoders, odometría y control reiniciados");
    }

    if (millis() - last_cmd_time > WATCHDOG_TIMEOUT_MS) {
        xSemaphoreTake(lock, portMAX_DELAY);
        if (cmd_pwm_left != 0 || cmd_pwm_right != 0 ||
            applied_pwm_left != 0 || applied_pwm_right != 0) {
            motor_parar();
            Serial.println("Watchdog: sin comandos, motores detenidos");
        }
        xSemaphoreGive(lock);
    }

    if (dt_ms >= DT_CONTROL_MS) {
        float dt_sec = dt_ms / 1000.0f;

        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);

        long raw_izq = encoderIzq.getCumulativePosition();
        long raw_der = encoderDer.getCumulativePosition();

        int snap_cmd_left = 0;
        int snap_cmd_right = 0;
        ControlMode snap_mode;

        xSemaphoreTake(lock, portMAX_DELAY);

        pulsos_izq = (raw_izq - offset_izq) * ENC_SIGN_LEFT;
        pulsos_der = (raw_der - offset_der) * ENC_SIGN_RIGHT;

        snap_cmd_left  = cmd_pwm_left;
        snap_cmd_right = cmd_pwm_right;
        snap_mode = control_mode;

        xSemaphoreGive(lock);

        float meters_per_tick = (2.0f * PI * RADIO_RUEDA) / TICKS_POR_VUELTA;
        float v_izq = ((pulsos_izq - prev_pulsos_izq) * meters_per_tick) / max(dt_sec, 1e-6f);
        float v_der = ((pulsos_der - prev_pulsos_der) * meters_per_tick) / max(dt_sec, 1e-6f);
        prev_pulsos_izq = pulsos_izq;
        prev_pulsos_der = pulsos_der;

        xSemaphoreTake(lock, portMAX_DELAY);
        odom.update(pulsos_izq, pulsos_der,
                    a.acceleration.x, a.acceleration.y, a.acceleration.z,
                    g.gyro.x, g.gyro.y, g.gyro.z, dt_sec);
        mi_ekf.update(v_izq, v_der, dt_sec, odom.yaw);
        float yaw_now_rad = odom.yaw;
        float yaw_now_deg = odom.yaw * 180.0f / PI;
        xSemaphoreGive(lock);

        int cmdL_for_control = 0;
        int cmdR_for_control = 0;

        xSemaphoreTake(lock, portMAX_DELAY);
        switch (control_mode) {
            case MODE_MANUAL_PWM:
                computeManualCommands(yaw_now_rad, dt_sec, cmdL_for_control, cmdR_for_control);
                break;

            case MODE_GOAL_DIST:
                computeDistanceGoalCommands(yaw_now_rad, cmdL_for_control, cmdR_for_control, dt_sec);
                break;

            case MODE_GOAL_TURN:
                computeTurnGoalCommands(yaw_now_deg, cmdL_for_control, cmdR_for_control, dt_sec);
                break;

            case MODE_GOAL_SPIN:
                computeSpinGoalCommands(yaw_now_deg, cmdL_for_control, cmdR_for_control, dt_sec);
                break;
        }
        xSemaphoreGive(lock);

        float v_ref_left  = pwmCmdToSpeedRef(cmdL_for_control);
        float v_ref_right = pwmCmdToSpeedRef(cmdR_for_control);

        int out_left  = pdLeft.update(cmdL_for_control,  v_ref_left,  v_izq, dt_sec);
        int out_right = pdRight.update(cmdR_for_control, v_ref_right, v_der, dt_sec);

        if (cmdL_for_control == 0) {
            pdLeft.reset();
            out_left = 0;
        }
        if (cmdR_for_control == 0) {
            pdRight.reset();
            out_right = 0;
        }

        xSemaphoreTake(lock, portMAX_DELAY);
        applied_pwm_left  = out_left;
        applied_pwm_right = out_right;
        apply_motors(applied_pwm_left, applied_pwm_right);
        xSemaphoreGive(lock);

        last_control_time = current_time;
    }

    if (current_time - last_telemetry_time >= 100) {
        if (activeClient && activeClient.connected()) {
            float snap_x, snap_y, snap_theta;
            float snap_vx, snap_omega;
            float snap_roll, snap_pitch, snap_yaw;
            long snap_pizq, snap_pder;
            float snap_ekf_x, snap_ekf_y, snap_ekf_theta;
            float snap_us;
            int snap_cmd_left, snap_cmd_right;
            int snap_out_left, snap_out_right;
            int snap_mode_int;

            xSemaphoreTake(lock, portMAX_DELAY);
            snap_x         = odom.x;
            snap_y         = odom.y;
            snap_theta     = odom.theta;
            snap_vx        = odom.vx;
            snap_omega     = odom.omega;
            snap_roll      = odom.roll;
            snap_pitch     = odom.pitch;
            snap_yaw       = odom.yaw;
            snap_pizq      = pulsos_izq;
            snap_pder      = pulsos_der;
            snap_ekf_x     = mi_ekf.getX();
            snap_ekf_y     = mi_ekf.getY();
            snap_ekf_theta = mi_ekf.getTheta();
            snap_us        = distancia_us_filtrada;
            snap_cmd_left  = cmd_pwm_left;
            snap_cmd_right = cmd_pwm_right;
            snap_out_left  = applied_pwm_left;
            snap_out_right = applied_pwm_right;
            snap_mode_int  = (int)control_mode;
            xSemaphoreGive(lock);

            String paquete =
                "POS_X:"     + String(snap_x, 3) + "\n" +
                "POS_Y:"     + String(snap_y, 3) + "\n" +
                "THETA:"     + String(snap_theta * 180.0f / PI, 2) + "\n" +
                "VEL_X:"     + String(snap_vx, 3) + "\n" +
                "VEL_O:"     + String(snap_omega * 180.0f / PI, 2) + "\n" +
                "US_DIST:"   + String(snap_us, 1) + "\n" +
                "PULSOS_I:"  + String(snap_pizq) + "\n" +
                "PULSOS_D:"  + String(snap_pder) + "\n" +
                "ROLL:"      + String(snap_roll, 2) + "\n" +
                "PITCH:"     + String(snap_pitch, 2) + "\n" +
                "YAW:"       + String(snap_yaw * 180.0f / PI, 2) + "\n" +
                "EKF_X:"     + String(snap_ekf_x, 3) + "\n" +
                "EKF_Y:"     + String(snap_ekf_y, 3) + "\n" +
                "EKF_THETA:" + String(snap_ekf_theta * 180.0f / PI, 2) + "\n" +
                "CMD_L:"     + String(snap_cmd_left) + "\n" +
                "CMD_R:"     + String(snap_cmd_right) + "\n" +
                "OUT_L:"     + String(snap_out_left) + "\n" +
                "OUT_R:"     + String(snap_out_right) + "\n" +
                "MODE:"      + String(snap_mode_int) + "\n";

            activeClient.print(paquete);
        }
        last_telemetry_time = current_time;
    }

    delay(1);
}