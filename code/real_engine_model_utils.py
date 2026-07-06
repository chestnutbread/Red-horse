"""
real_engine_model_utils.py
실제 Twin Builder VHDL-AMS 컴포넌트 코드 기반 엔진 열역학 공통 모델

[2026-07-06, GitHub Issue #7 반영] 07_fuel_fault_generator.py에 있던 엔진 코어
함수(inlet/compressor/combustor/turbine)를 공통 모듈로 분리했다.
시나리오1(연소효율 저하 실화)과 시나리오2(연료계통 고장)가 동일한 엔진 물리모델을
공유하고, 고장 주입 경로(입력단 보정계수)만 시나리오별로 분기하도록 하기 위함이다
(Issue #7 "모델링 수정 방향" 2, 3번 항목).

[2026-07-08, GitHub Issue #9 반영] 팀원(junslee02)이 Combustor entity에 독립
eta_b 포트 + fa_demand_out/wf_out 출력을 실제로 추가했다(Issue #8 요청 그대로
반영, "fuel_air_ratio_demand/actual 계산식은 절대 수정하지 않음" 원칙 준수 확인).
그래서 combustor()를 faultFactor_fuel과 eta_b가 완전히 독립된 인자를 받도록
분리한다 — 더 이상 "같은 자리에 둘 중 하나를 대입"하는 방안 B 우회가 아니라,
실제 entity와 1:1로 대응하는 정식 구현이다:
  - 시나리오2(연료계통 고장, 07_fuel_fault_generator.py): faultFactor_fuel만 변화,
    eta_b=1.0 고정 (Issue #3/#6 실측 검증, 1.0/0.7/0.5)
  - 시나리오1(연소효율 저하 실화, 10_combustion_efficiency_fault_generator.py):
    eta_b만 변화, faultFactor_fuel=1.0 고정 (JSSG-2007A §3.2.2.3.5/§3.2.2.6)
이렇게 하면 fuel_air_ratio_actual(=FAR_actual)이 eta_b의 영향을 받지 않으므로,
시나리오1에서는 FAR_actual≈FAR_demand(연료공급 정상)가 유지되고 시나리오2에서만
FAR_actual<FAR_demand가 되어, Issue #6이 원래 요구했던 원인 구분 지표가 살아난다.

파라미터 값 출처: GitHub Issue #6/#9(팀원이 공유한 실제 Twin Builder VHDL-AMS
컴포넌트 코드) + Issue #3(faultFactor_fuel 실측 검증) + 06_vhdl_comparison.py
(교차검증) — 07_fuel_fault_generator.py 원본 도입부 주석 참조.
"""

T_AMB0   = 288.15      # K, ISA 해면고도
P_AMB0   = 101325.0    # Pa
GAMMA_A  = 1.4
GAMMA_G  = 1.31
R_GAS    = 287.04      # J/(kg*K)
CP_AIR   = GAMMA_A * R_GAS / (GAMMA_A - 1.0)   # ≈1004.64 J/(kg*K)
CP_GAS   = GAMMA_G * R_GAS / (GAMMA_G - 1.0)   # ≈1212.66 J/(kg*K)
FUEL_CAL = 43_000_000.0  # J/kg

PR        = 10.55   # ⚠ Issue#6 entity 기본값(8.0) 아님, 실제 스키매틱 값
ETA_COMP  = 0.85
EFF_COMB  = 0.96     # ⚠ entity 기본값(0.95) 아님 — 압력손실계수, 온도/에너지와 무관
COMB_REF0 = 1365.0   # K, Issue #3 검증 런 기준
ETA_T     = 0.87     # ⚠ entity 기본값(0.88) 아님 (turbine generic eta_t, Issue #9에서도 변경 없음)
ETA_M     = 0.9      # ⚠ 2026-07-08 Issue #9: 팀원이 "0.98은 표기 오류"라고 정정 — 0.98→0.9로 수정
MFLOW     = 3.493    # kg/s, Honeywell 설계 공기유량


def inlet(altitude=0.0, mach=0.0):
    a1, a2 = 0.0065, 5.2561
    t_amb = T_AMB0 - a1 * altitude
    p_amb = P_AMB0 * ((t_amb / T_AMB0) ** a2)
    t_out = t_amb * (1.0 + (GAMMA_A - 1.0) / 2.0 * mach ** 2)
    p_out = p_amb * ((1.0 + (GAMMA_A - 1.0) / 2.0 * mach ** 2) ** (GAMMA_A / (GAMMA_A - 1.0)))
    return t_out, p_out


def compressor(t_in, p_in):
    t_out = t_in * (1.0 + (1.0 / ETA_COMP) * (PR ** ((GAMMA_A - 1.0) / GAMMA_A) - 1.0))
    p_out = PR * p_in
    power = MFLOW * CP_AIR * (t_out - t_in)   # W
    return t_out, p_out, power


def combustor(t_in, p_in, comb_ref, faultFactor_fuel=1.0, eta_b=1.0):
    """
    Twin Builder Combustor 블록 그대로(Issue #6/#9 entity 코드 1:1 대응).

    fuel_air_ratio_demand/fuel_air_ratio_actual 계산식은 절대 수정하지 않는다는
    원칙이 Issue #8→#9에서 실제로 지켜졌음을 확인함 — 아래 두 줄은 faultFactor_fuel
    에만 반응하고 eta_b와는 무관하다:
        far_demand = ...
        far_actual = far_demand * faultFactor_fuel      (eta_b 관여 없음)
    eta_b는 열발생 항(fuel_calorific)에만 곱해진다:
        t_out = t_in * (1 + far_actual*(fuel_calorific*eta_b)/(cp*t_in)) / (1+far_actual)

    faultFactor_fuel: 시나리오2(연료계통 고장) 전용 — 시나리오1 호출 시 1.0 고정
    eta_b           : 시나리오1(실화, 연소효율저하) 전용 — 시나리오2 호출 시 1.0 고정
    (둘 다 1.0이면 정상 운전, 기존 방안B 이전과 동일한 결과로 수렴)

    반환값에 fa_demand_out(=far_demand), wf_out(=연료유량, mflow_fuel)을 추가해
    Issue #9 entity의 신규 출력 포트와 1:1로 맞췄다.
    """
    far_demand = ((comb_ref / t_in) - 1.0) / (FUEL_CAL / (CP_GAS * t_in) - comb_ref / t_in)
    far_actual = far_demand * faultFactor_fuel
    wf = far_actual * MFLOW   # entity의 mflow_fuel == fuel_air_ratio_actual * mflow
    t_out = t_in * (1.0 + far_actual * (FUEL_CAL * eta_b) / (CP_GAS * t_in)) / (1.0 + far_actual)
    p_out = EFF_COMB * p_in
    return t_out, p_out, far_demand, far_actual, wf


def turbine(t_in, p_in, temp_diff_comp, far_comb):
    t_out = t_in + temp_diff_comp * ETA_M * (1.0 + far_comb)
    p_out = p_in * ((1.0 - (1.0 - t_out / t_in) / ETA_T) ** (GAMMA_G / (GAMMA_G - 1.0)))
    power = abs(MFLOW) * CP_GAS * (t_in - t_out)   # W
    return t_out, p_out, power
