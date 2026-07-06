"""
turboprop_simulator_utils.py
공통 브레이턴 사이클 함수 (Plan A 파라미터 기준)

Plan A 파라미터 (TPE331 계열):
  π_c = 9.6   (Garrett TPE331-10 실측, Saravanamuttoo 2017 부록A)
  η_c = 0.80  (Saravanamuttoo 2017, 2단 원심 0.78~0.82 중간값)
  FAR = 0.018 (Mattingly 2006 Ch.9, 역류 환형연소실 기준)
  η_b = 0.990 (JSSG-2007A §3.2.2.6 신규 엔진 기준)
  η_t = 0.85~0.92 → 균등 샘플링 (Saravanamuttoo 2017 Ch.7)
  η_pt= 0.84~0.90 → 균등 샘플링 (Park et al. 2023, Energy 305)
  ΔP_b= 0.03~0.05 → 균등 샘플링 (Mattingly 2006 Ch.9)
"""

import numpy as np

# ─────────────────────────────────────────────
# Plan A 기본 파라미터 (대표값)
# ─────────────────────────────────────────────
DEFAULTS = dict(
    T1    = 288.15,   # K  (ISO 2533 ISA 해수면)
    P1    = 101.325,  # kPa
    pi_c  = 9.6,      # 압력비 (Garrett TPE331-10 실측)
    eta_c = 0.80,     # 압축기 효율 (Saravanamuttoo 2017 Ch.5)
    FAR   = 0.018,    # 연료-공기 비 (Mattingly 2006 Ch.9)
    eta_b = 0.990,    # 연소 효율 (JSSG-2007A §3.2.2.6)
    eta_t = 0.88,     # 가스터빈 효율 (대표값; 샘플링은 RANGES 사용)
    eta_pt= 0.87,     # 파워터빈 효율 (대표값; 샘플링은 RANGES 사용)
    dp_b  = 0.04,     # 연소실 압력 손실률 (대표값; 샘플링은 RANGES 사용)
    LHV   = 43000,    # kJ/kg  (ASTM D1655 Jet-A)
    CP    = 1.005,    # kJ/(kg·K) (Anderson 2016)
    gamma = 1.4,      # 비열비 (Anderson 2016)
)

# ─────────────────────────────────────────────
# 문헌 기반 운전 범위 (샘플링용)
# ─────────────────────────────────────────────
RANGES = dict(
    T1     = (273.15, 313.15),  # K       ISO 2533 -15°C ~ +40°C
    pi_c   = (9.2,   10.0),     # —       Plan A ±4%
    FAR    = (0.016,  0.020),   # —       Mattingly 2006 Ch.9
    eta_b  = (0.975,  0.995),   # —       JSSG-2007A §3.2.2.6 정상 범위
    eta_t  = (0.85,   0.92),    # —       Saravanamuttoo 2017 Ch.7
    eta_pt = (0.84,   0.90),    # —       Park et al. 2023, Energy 305 (DOI:10.1016/j.energy.2023.129697)
    dp_b   = (0.03,   0.05),    # —       Mattingly 2006 Ch.9 환형연소실 설계 기준
)


def brayton_cycle(
    T1=288.15, P1=101.325, pi_c=9.6, eta_c=0.80, FAR=0.018,
    eta_b=0.990, eta_t=0.88, eta_pt=0.87, dp_b=0.04,
    LHV=43000, CP=1.005, gamma=1.4,
) -> dict:
    """
    터보프롭 브레이턴 사이클 단계별 계산.

    Returns: dict (T1~T5, P1~P5, W_net, EGT, SFC, eta_thermal)
    """
    # 1→2: 압축기
    T2s = T1 * (pi_c ** ((gamma - 1) / gamma))
    T2  = T1 + (T2s - T1) / eta_c
    P2  = P1 * pi_c

    # 2→3: 연소실 (η_b, dp_b 적용)
    T3 = T2 + eta_b * FAR * LHV / (CP * (1 + FAR))
    P3 = P2 * (1 - dp_b)

    # 3→4: 가스터빈 (압축기 구동)
    W_comp = CP * (T2 - T1)
    T4 = T3 - W_comp / (eta_t * CP * (1 + FAR))
    P4 = P3 * ((T4 / T3) ** (gamma / (gamma - 1)))

    # 4→5: 파워터빈 (프로펠러 구동)
    T5s = T4 * ((P1 / P4) ** ((gamma - 1) / gamma))
    T5  = T4 - eta_pt * (T4 - T5s)
    P5  = P1

    W_net = CP * (1 + FAR) * (T4 - T5)   # 파워터빈 순출력
    EGT   = T5
    SFC   = FAR / max(W_net, 1e-6)
    eta_thermal = W_net / (FAR * LHV)

    return dict(T1=T1, T2=T2, T3=T3, T4=T4, T5=T5,
                P1=P1, P2=P2, P3=P3, P4=P4, P5=P5,
                W_net=W_net, EGT=EGT, SFC=SFC, eta_thermal=eta_thermal)


def add_sensor_noise(result: dict, noise_level: float = 0.005, rng=None) -> dict:
    """센서 노이즈 추가 (±noise_level 기준 가우시안, Collins Aerospace ±2°C 기준 참조)"""
    if rng is None:
        rng = np.random.default_rng()
    noisy = dict(result)
    for key in ['T1','T2','T3','T4','T5','P1','P2','P3','P4','P5','W_net','EGT']:
        noisy[key] = result[key] * (1 + rng.normal(0, noise_level))
    return noisy
