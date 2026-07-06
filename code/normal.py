"""
TPE331-10 Brayton Cycle Python Validation Model — v2
=====================================================
목적  : VHDL-AMS Twin Builder 모델을 연구 파라미터 기준으로 검증
기준  : TPE331-10_Research_Parameters_v2.xlsx

[v2 파라미터 변경]
  PR   : 10.55 (VHDL 역산) -> 9.6   Garrett TPE331-10; Saravanamuttoo 2017 부록A
  eta_c: 0.85  (VHDL)      -> 0.80  Saravanamuttoo 2017 Ch.5
  eta_b: 0.96  (VHDL)      -> 0.990 JSSG-2007A 3.2.2.6
  FAR  : 0.019 (VHDL)      -> 0.018 Mattingly 2006 Ch.9
  TIT  : 1250K 고정         -> 연소기 에너지 평형 계산 (~1364 K)
  eta_t: 0.87  (VHDL)      -> 0.88  Saravanamuttoo 2017 Ch.7

작성  : Se-eun Park (박세은), APISAT 2026

[2026-07-06 Issue #7 추가] 5절: 방안 B(Combustor 기존 faultFactor_fuel 포트에 η_b
대입, Issue #6 architecture 그대로) 검증 섹션 추가. Combustor entity/architecture는
수정하지 않고, ramp4(Fuel Factor 입력) 소스의 출력값만 시나리오별로 바뀐다.
"""

import math

print("=" * 70)
print("  TPE331-10 브레이턴 사이클 - 연구 파라미터 기준 (v2)")
print("  기준: TPE331-10_Research_Parameters_v2.xlsx")
print("=" * 70)

# ─────────────────────────────────────────────────────────────
# 1. 연구 기준 파라미터 (TPE331-10_Research_Parameters_v2)
# ─────────────────────────────────────────────────────────────
R       = 287.04
gamma_c = 1.4            # 공기 비열비 (Anderson 2016)
gamma_t = 1.31           # 연소가스 비열비
CP_AIR  = gamma_c * R / (gamma_c - 1)   # ~1004.6 J/(kg*K)
CP_GAS  = gamma_t * R / (gamma_t - 1)   # ~1212.7 J/(kg*K)

T_amb   = 288.15         # K   (ISO 2533 ISA)
P_amb   = 101_325        # Pa

PR      = 9.6            # 압력비   - Garrett TPE331-10; Saravanamuttoo (2017) 부록A
eta_c   = 0.80           # 압축기 eff - Saravanamuttoo (2017) Ch.5
FAR     = 0.018          # 연료-공기비 - Mattingly (2006) Ch.9
eta_b   = 0.990          # 연소 eff - JSSG-2007A 3.2.2.6 신규 엔진
LHV     = 43_000_000     # J/kg  (ASTM D1655 Jet-A)
eta_t   = 0.88           # 가스터빈 eff - Saravanamuttoo (2017) Ch.7
eta_pt  = 0.87           # 파워터빈 eff - Park et al. (2023), Energy 305
eta_m   = 0.98           # 기계 eff (VHDL 유지)
dp_b    = 0.04           # 연소실 압력 손실 (Mattingly 2006 Ch.9)
m_dot   = 3.493          # kg/s  (Honeywell: 7.7 lb/s)

# VHDL 시뮬레이션 참조값 (비교용)
VHDL = dict(T2=613.75, T3=1250.0, T4=924.87,
             W_comp=1_150_260, W_turb=1_386_910, W_net=236_650)

# ─────────────────────────────────────────────────────────────
# 2. 브레이턴 사이클 계산
# ─────────────────────────────────────────────────────────────

# 1->2: 압축기
T1  = T_amb
P1  = P_amb
T2s = T1 * (PR ** ((gamma_c - 1) / gamma_c))
T2  = T1 + (T2s - T1) / eta_c
P2  = P1 * PR

print(f"\n[Station 2] 압축기 출구")
print(f"  T2s = {T2s:.2f} K")
print(f"  T2  = {T2:.2f} K  (VHDL: {VHDL['T2']:.2f} K,  delta = {T2 - VHDL['T2']:+.2f} K)")

# 2->3: 연소기 - TIT 에너지 평형 계산 (VHDL은 1250K 고정)
# T3 = T2 + eta_b * FAR * LHV / [CP_AIR * (1 + FAR)]
T3  = T2 + eta_b * FAR * LHV / (CP_AIR * (1 + FAR))
P3  = P2 * (1 - dp_b)

print(f"\n[Station 3] 연소기 출구 TIT")
print(f"  T3  = {T3:.2f} K  (VHDL 고정값: {VHDL['T3']:.2f} K,  delta = {T3 - VHDL['T3']:+.2f} K)")
print(f"  FAR=0.018, eta_b=0.990 기준 열역학적 TIT = {T3:.1f} K")
print(f"  VHDL TIT=1250 K 대비 {T3 - VHDL['T3']:+.1f} K (모델 구조 차이)")

# 3->4: 가스터빈 (VHDL 수식 적용)
# VHDL: t_out = t_in + temp_diff_comp * eta_m * (1 + FAR)
temp_diff_comp = -(T2 - T1)
T4 = T3 + temp_diff_comp * eta_m * (1 + FAR)

W_comp = m_dot * CP_AIR * (T2 - T1)
W_turb = m_dot * CP_GAS * (T3 - T4)

print(f"\n[Station 4] 가스터빈 출구")
print(f"  temp_diff_comp = {temp_diff_comp:.2f} K  (VHDL: -325.6 K)")
print(f"  T4  = {T4:.2f} K  (VHDL: {VHDL['T4']:.2f} K,  delta = {T4 - VHDL['T4']:+.2f} K)")
print(f"  W_comp = {W_comp:.0f} W  (VHDL: {VHDL['W_comp']:.0f} W)")
print(f"  W_turb = {W_turb:.0f} W  (VHDL: {VHDL['W_turb']:.0f} W)")

W_net = W_turb - W_comp
ratio = W_turb / W_comp
print(f"\n[Energy Balance]")
print(f"  W_net = {W_net:.0f} W ({W_net/1000:.2f} kW)")
print(f"  W_turb / W_comp = {ratio:.4f}  (VHDL: 1.206)")

# 4->5: 파워터빈
T5s = T4 * ((P1 / P3) ** ((gamma_t - 1) / gamma_t))
T5  = T4 - eta_pt * (T4 - T5s)
print(f"\n[Station 5] 파워터빈 / EGT")
print(f"  T5  = {T5:.2f} K  (EGT = {T5 - 273.15:.1f} C)")

# ─────────────────────────────────────────────────────────────
# 3. 역산: VHDL TIT=1250K 대응 이론 FAR
# ─────────────────────────────────────────────────────────────
dT_comb  = 1250.0 - T2
FAR_1250 = dT_comb * CP_AIR / (eta_b * LHV - dT_comb * CP_AIR)
print(f"\n[역산] TIT=1250 K 대응 이론 FAR (eta_b={eta_b}):")
print(f"  FAR_1250 = {FAR_1250:.4f}  (연구기준 FAR=0.018 대비 {(0.018 - FAR_1250)/0.018*100:.1f}% 낮음)")
print(f"  VHDL FAR=0.019 + TIT=1250K 설정은 열역학적으로 불일치")

# ─────────────────────────────────────────────────────────────
# 4. 파라미터 비교 요약
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("파라미터 비교: 연구기준(v2) vs VHDL README")
print("=" * 70)
rows = [
    ("PR",          "9.6",            "8  (기재 오류)",  "Garrett; Saravanamuttoo 2017"),
    ("eta_c",       "0.80",           "0.85",            "Saravanamuttoo 2017 Ch.5"),
    ("eta_b",       "0.990",          "0.96",            "JSSG-2007A 3.2.2.6"),
    ("FAR",         "0.018",          "0.019",           "Mattingly 2006 Ch.9"),
    ("TIT [K]",     f"{T3:.0f} (계산)", "1250 (고정)",   "열역학 계산 vs 고정"),
    ("eta_t",       "0.88",           "0.87",            "Saravanamuttoo 2017 Ch.7"),
    ("eta_pt",      "0.87",           "—",               "Park et al. 2023"),
]
print(f"{'파라미터':<15} {'연구기준(v2)':>14} {'VHDL README':>14}  {'출처'}")
print("-" * 70)
for p, r, v, s in rows:
    print(f"{p:<15} {r:>14} {v:>14}  {s}")
print("=" * 70)

# ─────────────────────────────────────────────────────────────
# 5. Issue #9 검증: Combustor 독립 eta_b 포트(실제모델) vs 위 2절의 연소
#    에너지식(η_b 직접곱셈)
# ─────────────────────────────────────────────────────────────
# [2026-07-08 갱신] Issue #6에서 "η_b 파라미터가 없다"고 확인된 뒤 Issue #7이
# 임시로 faultFactor_fuel 자리에 η_b를 대신 대입하는 방안 B를 썼으나, 그러면
# 시나리오1·2가 결과 데이터로 구분이 안 되는 부작용이 있어(Issue #6 코멘트)
# Issue #8로 정식 eta_b 포트 추가를 요청했고 Issue #9에서 팀원이 실제로 반영함.
# 지금 Combustor architecture(요청사항 그대로 far_demand/far_actual 계산식은 불변):
#   fuel_air_ratio_demand = ((comb_ref/t_in) - 1) / (fuel_calorific/(cp*t_in) - comb_ref/t_in)
#   fuel_air_ratio_actual = fuel_air_ratio_demand * faultFactor_fuel   -- 시나리오2 전용
#   t_out = t_in * (1 + far_actual*(fuel_calorific*eta_b)/(cp*t_in)) / (1 + far_actual)  -- eta_b 독립 반영
print("\n" + "=" * 70)
print("Issue #9 검증: Combustor 독립 eta_b 포트(실제모델) vs 위 연소식(직접곱셈)")
print("=" * 70)

COMB_REF_D = 1365.0   # K, Issue #3 faultFactor_fuel 검증 런과 동일 comb_ref (07_fuel_fault_generator.py 기준)


def combustor_eta_b(t_in, comb_ref, eta_b, fault_factor_fuel=1.0):
    """Issue #9 Combustor architecture 그대로: far_demand 역산 -> far_actual = far_demand * fault_factor_fuel
    (eta_b와 무관) -> t_out은 eta_b가 열발생 항에만 곱해짐. 시나리오1 검증이므로
    fault_factor_fuel은 기본 1.0(연료공급 정상)으로 둔다."""
    far_demand = ((comb_ref / t_in) - 1.0) / (LHV / (CP_GAS * t_in) - comb_ref / t_in)
    far_actual = far_demand * fault_factor_fuel
    t_out = t_in * (1.0 + far_actual * (LHV * eta_b) / (CP_GAS * t_in)) / (1.0 + far_actual)
    return t_out, far_demand, far_actual


# ① eta_b=1.0(정상) 수렴 확인 — comb_ref(명령 TIT)와 정확히 일치해야 함
t_out_1, far_d_1, far_a_1 = combustor_eta_b(T2, COMB_REF_D, 1.0)
print(f"① η_b=1.0(정상) 수렴 확인: T3={t_out_1:.2f} K  "
      f"(comb_ref={COMB_REF_D:.1f} K와 일치해야 함, "
      f"오차={abs(t_out_1 - COMB_REF_D) / COMB_REF_D * 100:.4f}%)")

# ② η_b 저하 단계별 추세 비교 (2절 직접곱셈 방식 vs 독립 eta_b 포트)
print(f"\n② η_b 저하에 따른 추세 비교 (JSSG §3.2.2.3.5/§3.2.2.6 단계 중앙값):")
print(f"{'stage':<9} {'η_b':>6} {'T3 직접곱셈[K]':>15} {'T3 독립eta_b[K]':>16} {'FARgap':>10}")
for stage_name, lo, hi in [('onset', 0.65, 0.80), ('partial', 0.35, 0.65), ('full', 0.05, 0.35)]:
    eta_b_mid = (lo + hi) / 2
    T3_direct = T2 + eta_b_mid * FAR * LHV / (CP_AIR * (1 + FAR))   # 2절 Station 3 식에 eta_b_mid만 대입
    T3_new, far_d, far_a = combustor_eta_b(T2, COMB_REF_D, eta_b_mid)
    print(f"{stage_name:<9} {eta_b_mid:>6.3f} {T3_direct:>15.1f} {T3_new:>16.1f} {abs(far_d - far_a):>10.6f}")

print("\n▶ 원인 구분 확인: 위 FARgap이 항상 0이어야 시나리오1(연료공급 정상, 열발생만 저하)이")
print("  제대로 재현되는 것이다 — 07(연료계통고장, faultFactor_fuel<1.0)에서는 이 값이 0이 아니게")
print("  되어 두 시나리오가 FAR_demand-actual 격차만으로 구분 가능해진다(Issue #6/#8 원래 요구사항).")

print("\n⚠ 두 계산은 물리 구조가 다르다 — 직접곱셈(2절, T3 = T2 + η_b·FAR·LHV/[CP(1+FAR)])은")
print("  고정 FAR에 η_b를 에너지식에 바로 곱하고, 독립eta_b모델은 comb_ref(명령 TIT)를 고정한 채")
print("  열발생 항에만 η_b를 곱한다(Issue #9 Combustor architecture 그대로). 따라서 절대값이 아니라")
print("  (a) η_b=1.0에서 comb_ref에 정확히 수렴하는지, (b) η_b 저하 → T3 감소라는 정성적 추세가")
print("  같은 방향인지를 검증 기준으로 삼는다.")
