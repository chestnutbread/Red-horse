"""
06_vhdl_comparison.py
Python 브레이턴 모델 vs VHDL Twin Builder 결과 비교

비교 시나리오:
  A) 기존 Plan A 파라미터 (π_c=9.6, η_c=0.80, FAR=0.018, η_b=0.990)
  B) VHDL 파라미터 적용 (π_c=10.55, η_c=0.85, FAR=0.019, "η_b"=0.96)
     ⚠ 아래 Issue #6 검토 결과 참조 — 이 "0.96"은 실제로는 η_b(연소효율)가 아니다.
  C) VHDL 시뮬레이션 실측값 (GitHub README 기준)

목적: 파라미터 불일치가 출력값에 미치는 영향 정량화

⚠ Issue #6 검토 결과 반영 (2026-07-04):
  1. [명칭 혼동] 시나리오 B/B2에서 브레이턴 에너지식의 η_b 자리에 대입해 온 "0.96"은
     실제로는 VHDL Combustor entity의 eff(압력손실계수, p_out = eff * p_in — 압력에만
     작용하고 온도/에너지 계산에는 관여하지 않음)이다. Plan A의 η_b(0.990, JSSG-2007A
     연소효율)와는 물리적 정의가 전혀 다른 값이므로, 이 스크립트의 브레이턴 에너지식에
     그대로 대입해 얻은 B/B2의 T3 계산은 "eff를 η_b로 오인"한 근사치에 불과하다.
     실제 VHDL 아키텍처(comb_ref 명령 기반 FAR 역산, 07_fuel_fault_generator.py의
     combustor() 참조)에는 이런 에너지-효율 항이 아예 없다.
  2. [시나리오1 이식 불가 → 방안 B(2026-07-06, Issue #7) → 독립 포트로 정식 해결
     (2026-07-08, Issue #9)] VHDL Combustor entity에는 원래 η_b(연소효율) 파라미터가
     없어 "방안 A"(연소기 계산식에 η_b 직접 추가)는 한때 적용 불가능했다. 2026-07-06
     랩미팅에서 임시로 "방안 B"(연료 주입량을 η_b만큼 미리 줄여서 주입하는 입력단
     우회 보정, faultFactor_fuel과 동일 자리 재사용)를 채택했으나, 이는 시나리오1·2를
     결과 데이터로 구분할 수 없게 만드는 부작용이 있어(Issue #6 코멘트) Issue #8로
     entity 자체에 독립 eta_b 포트 추가를 요청했고, 팀원이 Issue #9에서 실제로 반영함.
     이제 eta_b는 faultFactor_fuel과 완전히 독립된 입력이라 방안 A가 원래 의도했던
     물리(연료공급 정상 + 열발생만 감소)가 실제 entity 레벨에서 재현된다.
     아래 "시나리오 D" 절 및 10_combustion_efficiency_fault_generator.py 참조.
     04_jssg_fault_generator.py(Plan A)는 계속 병행 보관한다(비교 기준용).
"""

import numpy as np

# ─────────────────────────────────────────────────────────────
# 공통 설정
# ─────────────────────────────────────────────────────────────
T1    = 288.15   # K (ISA 해수면)
P1    = 101.325  # kPa
gamma_air = 1.4
gamma_gas = 1.31  # VHDL 연소가스 기준
CP_air = 1.005   # kJ/(kg·K)
CP_gas = gamma_gas * 0.28704 / (gamma_gas - 1)  # = 1.2127 kJ/(kg·K)
LHV   = 43000    # kJ/kg (ASTM D1655 Jet-A)
m_dot = 3.493    # kg/s (Honeywell 공식: 7.7 lb/s)

# ─────────────────────────────────────────────────────────────
# 브레이턴 사이클 함수 (단일 터빈 + 열역학 TIT 계산)
# ─────────────────────────────────────────────────────────────
def brayton_thermo(pi_c, eta_c, FAR, eta_b, eta_t, eta_m=0.98,
                   gamma=1.4, CP=1.005, T1=288.15, P1=101.325, m_dot=3.493):
    """
    열역학 기반 TIT 계산 방식 (Python Plan A 방식)
    - T3: 연소기 에너지 평형으로 계산
    - 단일 터빈 (압축기 구동 + 잉여출력)

    eta_b: Plan A 개념의 연소효율(η_b). 시나리오 A에서만 실제 η_b(0.990, JSSG-2007A)를
           의미한다. 시나리오 B/B2 호출에서 넘기는 0.96은 VHDL Combustor entity의
           eff(압력손실계수)를 편의상 이 자리에 대입한 근사값일 뿐, 실제 연소효율이
           아니다 — VHDL 모델에는 η_b 개념 자체가 없다 (Issue #6 검토 결과, 상단 주석 참조).
    """
    # 1→2: 압축기
    T2s = T1 * (pi_c ** ((gamma - 1) / gamma))
    T2  = T1 + (T2s - T1) / eta_c
    P2  = P1 * pi_c

    # 2→3: 연소기
    T3  = T2 + eta_b * FAR * LHV / (CP * (1 + FAR))

    # 3→4: 터빈 (압축기 구동 에너지 우선 공급)
    W_comp_spec = CP * (T2 - T1)                          # kJ/kg_air
    dT_turb = W_comp_spec / (eta_t * CP_gas * (1 + FAR))  # 터빈 온도 강하
    T4 = T3 - dT_turb

    # 동력 계산
    W_comp = m_dot * CP_air * (T2 - T1)
    W_turb = m_dot * (1 + FAR) * CP_gas * (T3 - T4)
    W_net  = W_turb - W_comp

    return dict(T2=T2, T3=T3, T4=T4,
                W_comp_kW=W_comp, W_turb_kW=W_turb, W_net_kW=W_net,
                turb_comp_ratio=W_turb/W_comp)


def brayton_fixed_TIT(pi_c, eta_c, TIT, eta_t, eta_m=0.98,
                      FAR=0.019, gamma_c=1.4, CP_c=1.005,
                      gamma_t=1.31, CP_t=1.2127,
                      T1=288.15, m_dot=3.493):
    """
    고정 TIT 방식 (VHDL Twin Builder 방식)
    - T3 = TIT (설계점 고정값)
    - 터빈 출구온도: VHDL 코드 수식 기반
    """
    # 1→2: 압축기
    T2s = T1 * (pi_c ** ((gamma_c - 1) / gamma_c))
    T2  = T1 + (T2s - T1) / eta_c
    P2  = P1 * pi_c

    # T3 = TIT (고정)
    T3  = TIT

    # 3→4: VHDL 수식 (코드 20번 줄 기반)
    # t_out = t_in + temp_diff_comp * eta_m * (1 + FAR)
    # temp_diff_comp = -(T2 - T1) = 압축기 온도상승의 음수
    temp_diff_comp = -(T2 - T1)
    T4 = T3 + temp_diff_comp * eta_m * (1 + FAR)

    # 동력 계산
    W_comp = m_dot * CP_c * (T2 - T1)
    W_turb = m_dot * CP_t * (T3 - T4)  # ṁ_air 기준 (VHDL 방식)
    W_turb_FAR = m_dot * (1 + FAR) * CP_t * (T3 - T4)  # ṁ_gas 기준 (수정 방식)

    return dict(T2=T2, T3=T3, T4=T4,
                W_comp_kW=W_comp, W_turb_kW=W_turb,
                W_turb_FAR_kW=W_turb_FAR,
                turb_comp_ratio=W_turb/W_comp)


# ─────────────────────────────────────────────────────────────
# 시나리오 A: 기존 Plan A 파라미터
# ─────────────────────────────────────────────────────────────
A = brayton_thermo(
    pi_c=9.6, eta_c=0.80, FAR=0.018, eta_b=0.990, eta_t=0.88
)

# ─────────────────────────────────────────────────────────────
# 시나리오 B: VHDL 파라미터 적용 (열역학 TIT 계산)
# ⚠ eta_b=0.96은 VHDL Combustor entity의 eff(압력손실계수)를 η_b 자리에 대입한
#   근사값이며 실제 연소효율이 아니다 (Issue #6 검토 결과, 파일 상단 주석 참조).
# ─────────────────────────────────────────────────────────────
B = brayton_thermo(
    pi_c=10.55, eta_c=0.85, FAR=0.019, eta_b=0.96, eta_t=0.87
)

# ─────────────────────────────────────────────────────────────
# 시나리오 B2: VHDL 파라미터 + 고정 TIT (VHDL 수식 그대로)
# ⚠ eta_m=0.98은 아래 C(VHDL 실측값, README 기준)가 캡처된 시점의 값을 그대로 둔
#   과거 비교용 고정값이다. Issue #9(2026-07-08)에서 팀원이 "0.98은 표기 오류,
#   실제는 0.9"라고 정정했으므로, C가 그 정정 이후 재측정된 값이 아니라면 이
#   B2 vs C 비교는 구버전 eta_m 기준 그대로 유지한다 — real_engine_model_utils.py
#   (07/10이 쓰는 공통 모델)는 이미 ETA_M=0.9로 갱신됨. C를 재측정하면 이 상수도
#   함께 갱신 필요.
# ─────────────────────────────────────────────────────────────
B2 = brayton_fixed_TIT(
    pi_c=10.55, eta_c=0.85, TIT=1250.0, eta_t=0.87, eta_m=0.98, FAR=0.019
)

# ─────────────────────────────────────────────────────────────
# 시나리오 C: VHDL 시뮬레이션 실측값 (GitHub README)
# ─────────────────────────────────────────────────────────────
C = dict(
    T2=613.75, T3=1250.0, T4=924.87,
    W_comp_kW=1150.26, W_turb_kW=1386.91,
    W_net_kW=236.65,
    turb_comp_ratio=1.206
)

# ─────────────────────────────────────────────────────────────
# 시나리오 D: 독립 eta_b 포트 검증 (Issue #9, 2026-07-08 — 방안 B 대체)
# ─────────────────────────────────────────────────────────────
# real_engine_model_utils.combustor()가 이제 faultFactor_fuel과 eta_b를 독립
# 인자로 받는다(Issue #9). 시나리오1은 faultFactor_fuel=1.0 고정 + eta_b만 변화.
from real_engine_model_utils import (
    inlet as _inlet, compressor as _compressor,
    combustor as _combustor, turbine as _turbine, COMB_REF0 as _COMB_REF0,
)


def eta_b_case(eta_b):
    T1_, P1_ = _inlet(altitude=0.0, mach=0.0)
    T2_, P2_, comp_power = _compressor(T1_, P1_)
    T3_, P3_, far_demand, far_actual, wf_ = _combustor(T2_, P2_, _COMB_REF0, faultFactor_fuel=1.0, eta_b=eta_b)
    T4_, P4_, turb_power = _turbine(T3_, P3_, T1_ - T2_, far_actual)
    return dict(T2=T2_, T3=T3_, T4=T4_,
                W_comp_kW=comp_power / 1000.0, W_turb_kW=turb_power / 1000.0,
                turb_comp_ratio=turb_power / max(comp_power, 1e-6),
                far_demand=far_demand, far_actual=far_actual, wf=wf_)


# ─────────────────────────────────────────────────────────────
# 출력
# ─────────────────────────────────────────────────────────────
print("=" * 70)
print("Python 브레이턴 모델 vs VHDL Twin Builder 비교")
print("=" * 70)

header = f"{'항목':<22} {'A: Plan A':>12} {'B: VHDL파라미터':>15} {'B2: VHDL+fixTIT':>16} {'C: VHDL실측':>12}"
print(header)
print("-" * 70)

rows = [
    ("T₂ 압축기출구 [K]",    A['T2'],         B['T2'],         B2['T2'],         C['T2']),
    ("T₃ TIT [K]",           A['T3'],         B['T3'],         B2['T3'],         C['T3']),
    ("T₄ 터빈출구 [K]",      A['T4'],         B['T4'],         B2['T4'],         C['T4']),
    ("W_comp [kW]",           A['W_comp_kW'],  B['W_comp_kW'],  B2['W_comp_kW'],  C['W_comp_kW']),
    ("W_turb [kW]",           A['W_turb_kW'],  B['W_turb_kW'],  B2['W_turb_kW'],  C['W_turb_kW']),
    ("터빈/압축기 비율",      A['turb_comp_ratio'], B['turb_comp_ratio'], B2['turb_comp_ratio'], C['turb_comp_ratio']),
]

for label, a, b, b2, c in rows:
    print(f"{label:<22} {a:>12.2f} {b:>15.2f} {b2:>16.2f} {c:>12.2f}")

print("=" * 70)

# B2 vs C 오차 분석
print("\n▶ B2 (VHDL파라미터+fixTIT) vs C (VHDL실측) 오차:")
items = [("T₂", B2['T2'], C['T2']),
         ("T₄", B2['T4'], C['T4']),
         ("W_comp", B2['W_comp_kW'], C['W_comp_kW']),
         ("W_turb", B2['W_turb_kW'], C['W_turb_kW'])]
for name, b2v, cv in items:
    err = abs(b2v - cv) / cv * 100
    print(f"  {name}: Python={b2v:.2f}, VHDL={cv:.2f}, 오차={err:.2f}%")

# B vs C TIT 불일치 강조
print(f"\n⚠️  B (VHDL파라미터, 열역학 TIT): TIT = {B['T3']:.1f} K  ← VHDL 고정값 1250 K와 {B['T3']-1250:.1f} K 차이")
print(f"    → FAR=0.019, "η_b"=0.96(실제로는 eff, 위 Issue #6 검토 결과 참조) 기준 열역학적 TIT는 {B['T3']:.1f} K이나")
print(f"       VHDL 모델은 TIT=1250 K로 고정하여 FAR와 불일치 발생")

# TIT=1250K에 대응하는 이론 FAR 계산
# ⚠ 아래 eff_as_etab_approx(=0.96)는 VHDL의 eff(압력손실계수)를 편의상 η_b 자리에
#   대입한 근사치다. 실제 VHDL Combustor entity는 이런 에너지-효율 항 없이
#   comb_ref 명령 기반으로 FAR를 역산하므로(07_fuel_fault_generator.py 참조),
#   아래 계산은 어디까지나 "eff=0.96을 η_b라 가정했을 때"의 가상 비교치다.
T2_vhdl = B2['T2']
TIT_target = 1250.0
eff_as_etab_approx = 0.96
# T3 = T2 + eff_as_etab_approx * FAR * LHV / (CP * (1+FAR))
# (TIT - T2) * CP * (1+FAR) = eff_as_etab_approx * FAR * LHV
# (TIT - T2) * CP + (TIT - T2) * CP * FAR = eff_as_etab_approx * LHV * FAR
# (TIT - T2) * CP = FAR * (eff_as_etab_approx * LHV - (TIT - T2) * CP)
dT = TIT_target - T2_vhdl
FAR_theory = dT * CP_air / (eff_as_etab_approx * LHV - dT * CP_air)
print(f"\n▶ TIT=1250K 대응 이론 FAR (eff→η_b 가정 근사치 0.96, LHV=43000): FAR = {FAR_theory:.4f}")
print(f"   ⚠ 이 근사치는 VHDL의 eff(압력손실계수)를 η_b로 가정했을 때의 가상값이며,")
print(f"      실제 VHDL 아키텍처는 comb_ref 명령 기반 FAR 역산 구조로 이와 다르다.")
print(f"   VHDL README의 FAR=0.019 vs 이론값 FAR={FAR_theory:.4f} → {abs(0.019-FAR_theory)/FAR_theory*100:.1f}% 불일치")

print("\n▶ 파라미터별 Python↔VHDL 불일치 요약:")
params_diff = [
    ("π_c (압력비)",        "9.6 (Garrett실측)",  "8 (README) / 10.55 (실제코드)"),
    ("η_c (압축기효율)",    "0.80 (Saravanamuttoo)", "0.85 (README)"),
    ("η_b (연소효율)",      "0.990 (JSSG-2007A)",  "⚠ 해당 파라미터 없음 — VHDL Combustor entity는 η_b 개념 자체가 없음"),
    ("eff (압력손실계수)",  "⚠ 해당 파라미터 없음 — Plan A는 압력손실을 별도 모델링하지 않음", "0.96 (README) — p_out=eff*p_in, 온도/에너지 계산과는 무관"),
    ("FAR",                 "0.018 (Mattingly)",   "0.019 (README)"),
    ("TIT 결정 방식",       "연소식으로 계산",      "1250 K 고정"),
    ("γ (터빈측)",          "1.4 (단일값)",         "1.31 (연소가스 별도)"),
]
for param, python_val, vhdl_val in params_diff:
    print(f"  {param:<20} Python: {python_val:<28} VHDL: {vhdl_val}")

print("\n▶ Issue #6 검토 결과 요약:")
print("  1) 명칭 혼동: 위 B/B2 시나리오의 \"eta_b=0.96\"은 VHDL Combustor entity의")
print("     eff(압력손실계수)이며 연소효율(η_b)이 아니다. 압력(P2→P3)에만 작용하고")
print("     온도/에너지 계산에는 관여하지 않는다 (07_fuel_fault_generator.py combustor() 참조).")
print("  2) VHDL 모델에는 η_b 파라미터 자체가 없어 방안 A(계산식 직접 추가)는 불가능하다.")
print("     → 2026-07-06 Issue #7에서 방안 B(입력단 보정)로 대체 결정, 아래 시나리오 D 참조.")

# ─────────────────────────────────────────────────────────────
# 시나리오 D 검증 출력 (Issue #9: 독립 eta_b 포트 반영 후 결과값 검증)
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("Issue #9 검증: 독립 eta_b 포트(실제모델) vs 기존 Plan A(직접곱셈)")
print("=" * 70)
d1 = eta_b_case(1.0)
print(f"① η_b=1.0(정상) 수렴 확인: T3={d1['T3']:.2f} K  (comb_ref={_COMB_REF0:.1f} K와 일치해야 함, "
      f"오차={abs(d1['T3']-_COMB_REF0)/_COMB_REF0*100:.4f}%)")
print(f"   FAR_demand={d1['far_demand']:.6f}, FAR_actual={d1['far_actual']:.6f} (일치해야 함)")

print(f"\n② η_b 저하에 따른 추세 비교 (JSSG §3.2.2.3.5/§3.2.2.6 단계 중앙값 기준):")
print(f"{'stage':<9} {'η_b':>6} {'T3 PlanA[K]':>13} {'T3 독립eta_b[K]':>16} "
      f"{'W_net PlanA[kW]':>17} {'W_net 독립eta_b[kW]':>20} {'FARgap':>10}")
for stage_name, lo, hi in [('onset', 0.65, 0.80), ('partial', 0.35, 0.65), ('full', 0.05, 0.35)]:
    eta_b_mid = (lo + hi) / 2
    a = brayton_thermo(pi_c=9.6, eta_c=0.80, FAR=0.018, eta_b=eta_b_mid, eta_t=0.88)
    d = eta_b_case(eta_b_mid)
    w_net_b = d['W_turb_kW'] - d['W_comp_kW']
    far_gap = abs(d['far_demand'] - d['far_actual'])
    print(f"{stage_name:<9} {eta_b_mid:>6.3f} {a['T3']:>13.1f} {d['T3']:>16.1f} "
          f"{a['W_net_kW']:>17.1f} {w_net_b:>20.1f} {far_gap:>10.6f}")

print("\n▶ 원인 구분 검증(Issue #6/#8 핵심 질문): 위 FARgap이 항상 0에 가까워야 시나리오1이")
print("  '연료공급 정상, 열발생만 저하'라는 물리를 제대로 재현하는 것 — 07_fuel_fault_generator.py")
print("  (연료계통고장, faultFactor_fuel<1.0)에서는 이 값이 0이 아니게 되어 두 시나리오가")
print("  FAR_demand-actual 격차만으로 구분 가능해진다(자세한 수치검증은 verify.py 결과 참조).")

print("\n⚠ 두 모델은 물리 구조가 다르다(Plan A: 고정 FAR + 연소 에너지식에 η_b 직접곱셈 /")
print("  독립eta_b모델: comb_ref 고정 + 열발생 항에만 η_b 곱셈). 따라서 절대값 일치가 아니라")
print("  (a) η_b=1.0에서 설계점(comb_ref)에 정확히 수렴하는지, (b) η_b 저하 → T3·W_net")
print("  감소라는 정성적 추세가 두 모델에서 같은 방향으로 나타나는지를 검증 기준으로 삼는다.")
