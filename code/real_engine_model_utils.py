"""
real_engine_model_utils.py
실제 Twin Builder VHDL-AMS 컴포넌트 코드 기반 엔진 열역학 공통 모델

[2026-07-06, GitHub Issue #7 반영] 07_fuel_fault_generator.py에 있던 엔진 코어
함수(inlet/compressor/combustor/turbine)를 공통 모듈로 분리했다.
시나리오1(연소효율 저하 실화)과 시나리오2(연료계통 고장)가 동일한 엔진 물리모델을
공유하고, 고장 주입 경로(입력단 보정계수)만 시나리오별로 분기하도록 하기 위함이다
(Issue #7 "모델링 수정 방향" 2, 3번 항목).

combustor()의 far_correction_factor 인자는 호출 시나리오에 따라 의미가 다르다:
  - 시나리오2(연료계통 고장, 07_fuel_fault_generator.py): faultFactor_fuel
    (Issue #3/#6 실측 검증, 1.0/0.7/0.5)
  - 시나리오1(연소효율 저하 실화, 10_combustion_efficiency_fault_generator.py):
    η_b (JSSG-2007A §3.2.2.3.5/§3.2.2.6, 방안 B, Issue #7)
Combustor 블록(계산식) 자체는 두 시나리오에서 완전히 동일하며 수정하지 않는다 —
상위 입력 로직(far_correction_factor 값)만 시나리오별로 분기한다.

파라미터 값 출처: GitHub Issue #6(팀원이 공유한 실제 Twin Builder VHDL-AMS
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
ETA_T     = 0.87     # ⚠ entity 기본값(0.88) 아님
ETA_M     = 0.98
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


def combustor(t_in, p_in, comb_ref, far_correction_factor):
    """
    Twin Builder Combustor 블록 그대로(Issue #6 아키텍처): comb_ref(명령 TIT)를
    만족하는 far_demand를 역산한 뒤, far_actual = far_demand * far_correction_factor
    로 입력단에서만 보정한다. 이 함수(Combustor 블록 계산식 자체)는 시나리오와
    무관하게 수정하지 않는다 (Issue #7 모델링 수정 방향 2번).
    """
    far_demand = ((comb_ref / t_in) - 1.0) / (FUEL_CAL / (CP_GAS * t_in) - comb_ref / t_in)
    far_actual = far_demand * far_correction_factor
    t_out = t_in * (1.0 + far_actual * FUEL_CAL / (CP_GAS * t_in)) / (1.0 + far_actual)
    p_out = EFF_COMB * p_in
    return t_out, p_out, far_demand, far_actual


def turbine(t_in, p_in, temp_diff_comp, far_comb):
    t_out = t_in + temp_diff_comp * ETA_M * (1.0 + far_comb)
    p_out = p_in * ((1.0 - (1.0 - t_out / t_in) / ETA_T) ** (GAMMA_G / (GAMMA_G - 1.0)))
    power = abs(MFLOW) * CP_GAS * (t_in - t_out)   # W
    return t_out, p_out, power
