"""
07_fuel_fault_generator.py
연료계통 고장(Fuel System Fault) 데이터 생성 — 시나리오 2

[2026-07-04 전면 재작성]
팀원(junslee02)이 GitHub Issue #6("연료 시스템 고장 시나리오 파이썬 코드 작성을 위한
각 컴포넌트 구성 코드 공유")에 실제 Twin Builder VHDL-AMS 컴포넌트 코드(Inlet/
Compressor/Combustor/Turbine)를 올렸고, Issue #3("[Combustor 연료 시스템 고장]
변수 faultFactor_fuel 도입 및 검증 결과")에 faultFactor_fuel=1.0/0.7/0.5 3케이스
실측 검증 결과가 있어, 이번 버전은 그 실제 코드/수치를 그대로 이식했다.
(이전 버전은 Plan A brayton_cycle에 FAR×factor를 억지로 곱하는 방식이었고,
이는 실제 Combustor 모델의 "명령(comb_ref) vs 실제(t_out) 괴리" 구조를 전혀
반영하지 못했음 — 아래 배경 설명 참조.)

────────────────────────────────────────────────────────────────
왜 이전 버전(FAR × factor on Plan A)을 폐기했는가
────────────────────────────────────────────────────────────────
Issue #3 배경 설명 그대로:
  기존 combustor 모델은 comb_ref(목표 TIT)를 그대로 만족하는 연료량을 역산하는
  구조였음 (t_out_temp == comb_ref). 여기서 comb_ref를 인위적으로 낮추면
  "FCU 명령 자체가 바뀐 상황"이 되어버려서, "명령은 정상인데 계통이 명령을
  이행하지 못하는 상황"(진짜 고장)을 재현하지 못함.
  → 해결책: 연료-공기비 계산식에 faultFactor_fuel을 곱해서, comb_ref(명령)는
    그대로 두고 실제 출력(t_out)만 명령과 어긋나게 만듦.
    fuel_air_ratio_actual = fuel_air_ratio_demand * faultFactor_fuel
    faultFactor_fuel = 1.0 → 정상 (comb_t_out == comb_ref 정확히 일치)
    faultFactor_fuel < 1.0 → 연료 부족 (comb_t_out < comb_ref, 명령-실제 괴리 발생)

이전 버전은 이 "명령 vs 실제" 구조 자체가 없어서 물리적으로 다른 모델이었음.
이번 버전은 Issue #6의 Combustor VHDL-AMS 코드(fuel_air_ratio_demand 역산식,
fuel_air_ratio_actual = demand × faultFactor_fuel)를 Python으로 그대로 옮김.

────────────────────────────────────────────────────────────────
실제 컴포넌트 파라미터 값 (Issue #6 코드의 generic 기본값이 아니라,
Issue #3 검증 수치 및 06_vhdl_comparison.py에서 이미 교차검증된 "실제 스키매틱
설정값"을 사용함 — 아래 각주 참조)
────────────────────────────────────────────────────────────────
  T1(inlet out)   = 288.15 K   (ISA 해면고도, altitude=0, mach=0)
  PR(compressor)  = 10.55      ⚠ Issue #6 entity 코드의 generic 기본값은 8.0이지만,
                                  README 설계점 검증(T2=613.75K, temp_diff_comp=
                                  -325.6K)과 06_vhdl_comparison.py가 이미 역산한
                                  실제 스키매틱 설정값 10.55와 정확히 일치함(재검산 완료).
  eta_comp        = 0.85       (Issue #6 generic 기본값, T2=613.75K 재현으로 확인)
  comb_ref        = 1365 K     ⚠ README 설계점 섹션의 1250K는 별도의 초기 수렴검증
                                  런이고, Issue #3의 faultFactor_fuel 검증은 1365K
                                  기준으로 수행됨 — 본 파일은 시나리오2 재현이 목적이므로
                                  1365K 채택.
  eff(combustor)  = 0.96       ⚠ entity 기본값 0.95 아님, README 컴포넌트 표 기준.
  fuel_calorific  = 43,000,000 J/kg (Issue #6 코드 그대로)
  eta_t           = 0.87       (Issue #6 generic 기본값 0.88 아님, README/06 교차검증값)
  eta_m           = 0.9        ⚠ 2026-07-08 Issue #9: 팀원이 0.98은 표기 오류라고 정정 — 0.9가 맞음
  gamma_air=1.4, gamma_gas=1.31, R=287.04 J/(kg·K)  (Issue #6 코드 그대로)
  mflow           = 3.493 kg/s (Honeywell 설계 공기유량, 06_vhdl_comparison.py와 동일)

faultFactor_fuel 3케이스 (Issue #3 실측 검증):
  Case1 정상   : 1.0  → comb_t_out == comb_ref (오차 0)
  Case2 경미   : 0.7  → comb_t_out ≈ comb_ref - 235K (1365→~1130K, 700s 기준)
  Case3 중증   : 0.5  → comb_t_out ≈ comb_ref - 400K (1365→~965K)
  (본 파일 값은 위 방정식을 지상 설계점에서 그대로 계산한 것이라 팀원의 실측
   그래프 값과는 비행 프로파일 시점 차이만큼 수 % 오차가 있을 수 있음 — 검증 결과
   섹션 참조)

시나리오1(압축기 실화)과의 관계:
  사용자 확인: 이 Issue #6 구성(Twin Builder 실제 모델)은 시나리오2(연료계통
  고장)만 완성되어 있고, 시나리오1(실화) Twin Builder 모델링은 아직 미완성.
  따라서 04_jssg_fault_generator.py(Plan A, η_b 기반)는 계속 Python 전용
  잠정 대체재로 유지하며, 실제 Twin Builder 검증 전까지는 시나리오1과
  시나리오2를 같은 물리 모델로 비교하지 않는다(아래 combustor_real_normal_data.csv
  참조 — 시나리오2는 자체 베이스라인을 따로 둠).

[2026-07-08, 팀원 모델링 데이터 7,000건 기준 통일에 맞춰 샘플 수 조정]
팀원이 Twin Builder에서 뽑는 데이터를 7,000건으로 맞춘다고 확인되어, 기존 6,000건
(normal 3,000 / moderate 1,500 / severe 1,500, 5:2.5:2.5 비율)을 같은 비율로
7,000건(normal 3,500 / moderate 1,750 / severe 1,750)에 맞게 조정했다.

출력:
  ../02_시뮬레이션_데이터/fuel_fault_data.csv            (fault: moderate/severe, 3,500샘플)
  ../02_시뮬레이션_데이터/combustor_real_normal_data.csv (정상: faultFactor_fuel=1.0, 3,500샘플)
    → 이 정상 데이터는 Plan A의 normal_data.csv와 물리 모델이 다르므로
      (PR=10.55 vs pi_c=9.6, comb_ref 명령구조 vs η_b 직접곱셈 등) 반드시
      이 파일끼리만 짝지어 PCA 베이스라인으로 써야 한다 (02_anomaly_detector.py 참조).

[2026-07-06, Issue #7 반영] 엔진 코어 함수(inlet/compressor/combustor/turbine)를
real_engine_model_utils.py 공통 모듈로 분리했다. 시나리오1(연소효율 저하 실화,
10_combustion_efficiency_fault_generator.py)이 방안 B로 동일한 엔진 모델을
공유해야 하기 때문이다(Issue #7 "모델링 수정 방향" 3번). 이 파일의 물리식과
파라미터 값은 전혀 바뀌지 않았고, 함수 정의 위치만 이동했다.

[2026-07-08, Issue #9 반영] 팀원이 Combustor entity에 독립 eta_b 포트를 실제로
추가해서(Issue #8 요청 그대로), combustor()가 faultFactor_fuel/eta_b를 독립
인자로 받도록 바뀌었다. 이 파일(시나리오2)은 eta_b=1.0으로 고정 호출한다 —
연료계통 고장은 eta_b와 무관해야 하므로 물리적으로 당연한 값이고, 그 결과
fuel_air_ratio_actual 계산식 자체(faultFactor_fuel에만 반응)는 이 변경으로
전혀 달라지지 않는다. 다만 turbine()의 ETA_M이 0.98→0.9로 정정되어(팀원 확인:
0.98은 표기 오류) T4/turbine_power_kW 값은 이전 실행분과 달라지므로, 이 파일을
재실행하고 Supabase도 재업로드해야 한다.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from real_engine_model_utils import (
    inlet, compressor, combustor, turbine, COMB_REF0,
)

N_PER_STAGE = 1750   # 2026-07-08: 1,500→1,750 (7,000건 기준, 5:2.5:2.5 비율 유지)
SEED        = 331

OUTPUT_DIR   = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FAULT_PATH   = OUTPUT_DIR / "fuel_fault_data.csv"
NORMAL_PATH  = OUTPUT_DIR / "combustor_real_normal_data.csv"

NOISE_LEVEL = 0.003   # 센서노이즈(가우시안), 기존 프로젝트 관례(0.5%)보다 약간 낮게
                      # → 팀원 실험처럼 "순수 연료고장 효과 분리"를 위해 altitude/mach는 고정하고
                      #   comb_ref만 소폭(±15K, 스로틀 미세조정 대응) 흔든다.

N_NORMAL = 3500   # 2026-07-08: 팀원 모델링 7,000건 기준에 맞춰 6,000→7,000(5:2.5:2.5 비율 유지)

STAGES = [
    ('moderate', 0.7, 'Case2'),
    ('severe',   0.5, 'Case3'),
]


def run_case(fault_factor, rng):
    """지상 설계점(altitude=0, mach=0 고정) + comb_ref 미세변동 + 0.3% 센서노이즈."""
    comb_ref = COMB_REF0 + rng.uniform(-15.0, 15.0)   # 스로틀 미세조정 대응, 순수 고장효과 분리 유지

    T1, P1 = inlet(altitude=0.0, mach=0.0)
    T2, P2, comp_power = compressor(T1, P1)
    T3, P3, far_demand, far_actual, wf = combustor(T2, P2, comb_ref, faultFactor_fuel=fault_factor, eta_b=1.0)
    temp_diff_comp = T1 - T2
    T4, P4, turb_power = turbine(T3, P3, temp_diff_comp, far_actual)

    out = dict(T1_K=T1, P1_Pa=P1, T2_K=T2, P2_Pa=P2,
               comb_ref_K=comb_ref, T3_K=T3, P3_Pa=P3,
               T4_K=T4, P4_Pa=P4,
               FAR_demand=far_demand, FAR_actual=far_actual, Wf_kg_s=wf,
               faultFactor_fuel=fault_factor,
               compressor_power_kW=comp_power / 1000.0,
               turbine_power_kW=turb_power / 1000.0,
               TIT_error_K=comb_ref - T3)   # ★핵심 고장 시그니처: 명령(comb_ref) - 실제(T3)

    # 0.3% 가우시안 센서노이즈
    for k in ['T1_K', 'P1_Pa', 'T2_K', 'P2_Pa', 'T3_K', 'P3_Pa', 'T4_K', 'P4_Pa',
              'compressor_power_kW', 'turbine_power_kW']:
        out[k] = out[k] * (1.0 + rng.normal(0.0, NOISE_LEVEL))
    return out


if __name__ == "__main__":
    # ── 정상 데이터 (faultFactor_fuel=1.0) ──────────────────────────────
    rng = np.random.default_rng(SEED)
    normal_records = []
    for i in range(N_NORMAL):
        rec = run_case(1.0, rng)
        rec.update(sample_id=i, label='normal', fault_type='none')
        normal_records.append(rec)

    df_normal = pd.DataFrame(normal_records)
    df_normal.to_csv(NORMAL_PATH, index=False)
    print(f"✅ 연료계통 실제모델 정상 데이터 {len(df_normal):,}샘플 → {NORMAL_PATH}")
    print(f"   (faultFactor_fuel=1.0 → TIT_error 평균 {df_normal['TIT_error_K'].mean():.4f} K, 이론상 0)")

    # ── 고장 데이터 (moderate=0.7 / severe=0.5) ─────────────────────────
    rng = np.random.default_rng(SEED + 1)
    fault_records = []; sample_id = 0
    for stage_name, factor, tb_case in STAGES:
        for _ in range(N_PER_STAGE):
            rec = run_case(factor, rng)
            rec.update(sample_id=sample_id, label='fault', fault_type='FS-FUELSTARV',
                       fault_stage=stage_name, twin_builder_case=tb_case,
                       source_issue='github.com/chestnutbread/Red-horse/issues/3,6')
            fault_records.append(rec)
            sample_id += 1

    df_fault = pd.DataFrame(fault_records)
    df_fault.to_csv(FAULT_PATH, index=False)
    print(f"\n✅ 연료계통 고장 데이터 {len(df_fault):,}샘플 → {FAULT_PATH}")
    print(df_fault.groupby('fault_stage')[['faultFactor_fuel', 'T3_K', 'TIT_error_K', 'turbine_power_kW']].mean().round(2))
    print("\n참고: Issue #3 실측(700s 기준) comb_t_out ≈ 1130K(Case2) / 965K(Case3).")
    print("      본 지상설계점 계산값과는 팀원 실험의 비행프로파일 시점 차이만큼 수% 편차가 날 수 있음.")
