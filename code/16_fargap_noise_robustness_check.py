"""
16_fargap_noise_robustness_check.py
Red-Horse APISAT 2026 논문 — FARgap 판별 신호의 센서 노이즈 강건성 몬테카를로 검증

[배경, 2026-08-01]
논문 Sec. 5.1/5.3은 FARgap = FARdemand - FARactual (Eq. 10, 11)을 결함 유형
판별(연소효율 저하 vs. 연료계통 결함)의 2차 지표로 제안한다. 이 판별은
S1(연소효율 저하)에서 FARgap이 정확히 0이고 S2(연료계통 결함)에서는 양수
플래토(~0.0070)로 갈라진다는 사실에 의존하는데, 본문에 보고된 수치는 전부
노이즈 없는(noiseless) 시계열 기준이다. 실제 계측 환경에서는 센서 노이즈가
섞이므로, Eq.(10)/(11)의 역산이 노이즈에 얼마나 민감한지 검증할 필요가 있다
(Sec. 6 "quantifying this sensitivity... is a prerequisite for future work"의
근거 자료).

[방법]
Supabase에서 다운샘플링한 S1(ENGINE_EFF, 연소효율 저하)·S2(ENGINE_FUELFAULT,
연료계통 결함) 실측 T3(t), T4(t) 쌍에 σ=0.3%(프로젝트 기존 결함 생성기 관례,
07_fuel_fault_generator.py 등과 동일 기준) 곱셈형 가우시안 노이즈를 N=500회
독립 시행으로 주입하고, 매 시행마다 Eq.(10)/(11)을 그대로 역산해 FARgap을
재계산한다. 노이즈 없는 기준값과 몬테카를로 분포(평균/표준편차/5-95th
백분위수)를 비교한다.

[핵심 결과 요약 — 2026-08-01 실행 기준]
- S1(연소효율저하): FARgap은 노이즈 유무와 무관하게 항상 정확히 0
  (구성상 ffuel≡1이므로 FARactual=FARdemand가 항등식으로 성립 — T3/T4 노이즈가
  Eq.(10)에 들어갈 여지 자체가 없음).
- S2(연료계통결함): 정상상태 플래토(t>=440s 근방)에서는 노이즈 하에서도
  FARgap이 뚜렷하게 양수로 유지되어 강건함 (5-95th 백분위수가 0 위에 있음).
- 다만 결함 개시 직후(t=300s, 온셋 전이 구간 초입)에는 노이즈-없는 FARgap
  자체가 아직 0.00004로 작아서, N=500 몬테카를로 시행 중 38%가 gap<=0으로
  떨어짐 — 결함 발생 "직후 순간"에는 FARgap 부호만으로 오분류(연소효율 저하로
  오판)할 위험이 있다는 뜻. 정상상태 플래토 이후에는 이 위험이 사라진다.

[결론 / 논문 반영 상태]
이 정량적 결과는 이번 제출본(Sec. 6)에는 페이지 상한(10p)으로 인해 별도
Figure로는 반영하지 못했고, 요약 문장으로만 한계점에 언급되어 있다. 전체
해상도 데이터 기반 공식 검증 및 신규 Figure 추가는 후속 과제로 남겨둔다.

[사용법]
    python 16_fargap_noise_robustness_check.py
"""

import numpy as np

# 논문 Table 3 상수와 동일 (Sec. 2.2, tit_limiter1 setpt. = 1373 K)
Qfuel = 43.0e6      # J/kg, LHV
cp_g = 1212.66      # J/(kg*K), combustion-gas cp,g
Tref = 1373.0       # K, tit_limiter1 setpoint (Sec. 2.1)

NOISE_LEVEL = 0.003   # ±0.3%, 프로젝트 기존 결함 생성기 관례와 동일 기준
N_TRIALS = 500


def far_demand(T3):
    """Eq. (4): FARdemand = (Tref/T3 - 1) / (Qfuel/(cp_g*T3) - Tref/T3)"""
    return (Tref / T3 - 1.0) / (Qfuel / (cp_g * T3) - Tref / T3)


def far_actual_S2(T3, T4):
    """Eq. (10): FARactual = (T3-T4)/(T4 - Qfuel/cp_g), ηb=1 가정 (S2, 연료계통결함)"""
    return (T3 - T4) / (T4 - Qfuel / cp_g)


def eta_b_S1(T3, T4, fard):
    """Eq. (11): ηb = [T4(1+FARdemand)-T3]*cp_g/(FARdemand*Qfuel), FARactual=FARdemand 가정 (S1)"""
    return (T4 * (1 + fard) - T3) * cp_g / (fard * Qfuel)


# 다운샘플링된 실측 T3(t), T4(t) — Supabase ENGINE_EFF(S1)/ENGINE_FUELFAULT(S2)에서
# 결함 개시(t~300s) 이후 구간을 저해상도로 추출한 값 (전체 해상도 데이터는
# Supabase 원본 테이블 참조; 이 스크립트는 경량 검증용)
S1_DATA = [  # (t, T3, T4) — 연소효율 저하
    (300, 569.309005231857, 1371.08456721371), (320, 567.470646918455, 1351.1854691084),
    (340, 565.701944357174, 1306.74553469871), (360, 563.927334083974, 1259.95639799772),
    (380, 562.156848988722, 1212.63080880668), (400, 560.412428497588, 1168.32536806425),
    (420, 558.686840063845, 1164.93447776942), (440, 556.974929885078, 1164.4677283417),
    (460, 555.278413977986, 1144.76817291189), (480, 553.597638986174, 1105.58831673847),
    (500, 551.931026217078, 1066.23441341549), (520, 550.277632367926, 1026.69125427736),
    (540, 548.645577155885, 987.163802768351), (560, 547.024275067302, 966.828078104439),
    (580, 545.415482049858, 966.03107692636), (600, 543.821046317696, 961.97528374437),
    (620, 542.245563615222, 912.281217026216), (640, 540.676567429265, 858.935510763913),
    (660, 539.128313927681, 805.671467022194), (680, 537.588249694878, 752.070583880491),
    (700, 536.065979135625, 701.658181471169), (720, 534.921966199774, 697.334800800614),
    (800, 534.921966199773, 697.334798308407), (900, 534.921966199773, 697.334803154005),
    (1000, 534.921966199776, 697.334778477386),
]

S2_DATA = [  # (t, T3, T4) — 연료계통 결함
    (300, 569.304662888738, 1371.61353684239), (320, 567.509969833175, 1360.35101817517),
    (340, 565.702959727978, 1334.75016719895), (360, 563.919917955848, 1301.7515696806),
    (380, 562.155031569639, 1268.57295778676), (400, 560.408998010382, 1235.23478385355),
    (420, 558.688480304837, 1201.87585819378), (440, 556.971111782726, 1168.06652040603),
    (460, 555.263971463316, 1150.90520382788), (480, 553.597671890847, 1150.42224316237),
    (500, 551.929239136645, 1149.93871187562), (520, 550.279293037904, 1149.46056820988),
    (540, 548.641190013269, 1148.98588487549), (560, 547.018196568424, 1148.51561630417),
    (580, 545.415002580522, 1148.05110732818), (600, 543.825526931916, 1147.59060628907),
    (620, 542.245235127026, 1147.13279936103), (640, 540.674956770595, 1146.67792677047),
    (660, 539.118135906129, 1146.22697098533), (680, 537.589574552342, 1145.78422359599),
    (700, 536.057479309569, 1145.34049282664), (720, 534.921966199774, 1145.0116315202),
    (800, 534.921966199773, 1145.01163363442), (900, 534.921966199773, 1145.01163804607),
    (1000, 534.921966199778, 1145.01158304971),
]


def gap_series(data, noise_pct, rng, is_s1):
    """주어진 (t,T3,T4) 시계열에 노이즈를 주입하고 FARgap = FARdemand - FARactual을 반환."""
    t3 = np.array([d[1] for d in data])
    t4 = np.array([d[2] for d in data])
    if noise_pct > 0:
        t3 = t3 * (1 + rng.normal(0, noise_pct, size=t3.shape))
        t4 = t4 * (1 + rng.normal(0, noise_pct, size=t4.shape))
    fard = far_demand(t3)
    if is_s1:
        # S1: ffuel=1 by construction -> FARactual = FARdemand 항등식 (T3/T4 노이즈가
        # 이 판별식에 들어갈 여지가 없음). gap은 항상 0.
        far_a = fard
    else:
        far_a = far_actual_S2(t3, t4)
    return fard - far_a


def run_monte_carlo():
    rng = np.random.default_rng(2026)
    results = {}
    for label, data, is_s1 in [("S1 (comb-eff)", S1_DATA, True), ("S2 (fuel-sys)", S2_DATA, False)]:
        gap0 = gap_series(data, 0.0, rng, is_s1)
        gaps = np.array([gap_series(data, NOISE_LEVEL, rng, is_s1) for _ in range(N_TRIALS)])
        print(f"--- {label} ---")
        print(f"  noise-free FARgap: mean={gap0.mean():.5f}, max|.|={np.abs(gap0).max():.5f}")
        print(f"  noisy FARgap ({NOISE_LEVEL*100:.1f}%): mean={gaps.mean():.5f}, "
              f"std={gaps.std():.5f}, 5-95pct=[{np.percentile(gaps, 5):.5f}, "
              f"{np.percentile(gaps, 95):.5f}]")
        results[label] = {"gap0": gap0, "gaps_mc": gaps}

    # 결함 개시 직후 순간의 오분류 위험 정량화 (S2, per-timestep worst case)
    t = np.array([d[0] for d in S2_DATA])
    t3 = np.array([d[1] for d in S2_DATA])
    t4 = np.array([d[2] for d in S2_DATA])
    gap0 = far_demand(t3) - far_actual_S2(t3, t4)
    gaps_mc = np.zeros((N_TRIALS, len(S2_DATA)))
    for i in range(N_TRIALS):
        t3n = t3 * (1 + rng.normal(0, NOISE_LEVEL, size=t3.shape))
        t4n = t4 * (1 + rng.normal(0, NOISE_LEVEL, size=t4.shape))
        gaps_mc[i] = far_demand(t3n) - far_actual_S2(t3n, t4n)
    p5 = np.percentile(gaps_mc, 5, axis=0)
    worst_idx = int(np.argmin(p5))
    print()
    print("=== per-timestep worst case (S2, noisy) ===")
    print(f"noise-free gap range over trajectory: min={gap0.min():.5f} at "
          f"t={t[np.argmin(gap0)]:.0f}s, max={gap0.max():.5f}")
    print(f"worst-case (5th pct, per-timestep) gap: {p5[worst_idx]:.5f} at "
          f"t={t[worst_idx]:.0f}s (noise-free there was {gap0[worst_idx]:.5f})")
    misclass_rate = (gaps_mc[:, worst_idx] <= 0).mean() * 100
    print(f"fraction of {N_TRIALS} trials at that worst timestep with gap<=0: "
          f"{misclass_rate:.1f}%")
    return results


if __name__ == "__main__":
    run_monte_carlo()
