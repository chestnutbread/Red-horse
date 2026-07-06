"""
10_combustion_efficiency_fault_generator.py
연소효율(η_b) 저하형 실화(Flameout) 데이터 생성 — 시나리오 1, 방안 B 적용

[2026-07-06, GitHub Issue #7 반영]
Issue #6 검토 결과 VHDL Combustor entity에는 η_b(연소효율) 파라미터 자체가 없어
방안 A(연소기 계산식에 η_b 항목 직접 추가)는 적용이 불가능했다. 2026-07-06
랩미팅에서 두 방안을 공유했고, 교수님 검토 결과 방안 B(연료 주입량을 η_b만큼
미리 줄여서 주입하는 우회 방식)를 우선 적용하기로 결정했다. 방안 A는 일정에
여유가 있을 경우 별도 과제로 진행한다.

모델링 수정 방향 (Issue #7 원문 그대로):
  1. 연소기 입력단에서 연료 주입량 계산 시 η_b를 사전 반영:
     far_actual = far_demand × η_b
  2. Twin Builder 연소기 블록(계산식) 자체는 수정하지 않고, 상위 입력 로직에서만 보정
  3. 시나리오 1·2 공통 엔진 모델(real_engine_model_utils.py)은 그대로 유지하고,
     고장 주입 경로(입력)만 시나리오별로 분기 — 이 스크립트는
     real_engine_model_utils.combustor()의 far_correction_factor 자리에
     faultFactor_fuel(시나리오2, 07_fuel_fault_generator.py) 대신 η_b를 대입한다.
     Combustor 블록 계산식 자체는 07과 완전히 동일하며 수정하지 않았다.

이 스크립트는 04_jssg_fault_generator.py(Plan A, η_b를 브레이턴 에너지식에 직접
곱하는 방안 A 근사 모델)를 대체하지 않는다 — 04는 계속 병행 보관한다(일정 여유
시 방안 A 별도 과제 대비 및 비교 기준용). 이 스크립트가 "실제 검증된 Twin
Builder 모델 + 방안 B" 기준의 시나리오1 데이터를 새로 제공한다.

⚠ Issue #7 요청사항(2) "보정 후 결과값이 기존 파이썬 모델 결과와 일치하는지 검증"
관련 주의: 방안 B(comb_ref 고정 + 입력단 FAR 보정)와 기존 Plan A(고정 FAR + 연소
에너지식에 η_b 직접곱셈)는 물리 구조 자체가 다르므로 절대값이 일치하지는 않는다.
검증 가능한 것은 (a) η_b=1.0(정상)일 때 방안B가 설계점(comb_ref, README 수렴값)에
정확히 수렴하는지, (b) η_b 저하에 따라 T3·터빈출력이 감소하는 정성적 추세가 두
모델에서 같은 방향으로 나타나는지이다. 정량적 비교는 06_vhdl_comparison.py의
"시나리오 D" 절 참조.

η_b 단계 (JSSG-2007A §3.2.2.3.5 / §3.2.2.6, 04_jssg_fault_generator.py와 동일 근거):
  onset  (초기): η_b = 0.65~0.80
  partial(부분): η_b = 0.35~0.65  (onset~full 선형 보간 추정 — ⚠ JSSG 정의 없음, 임의 설정)
  full   (완전): η_b = 0.05~0.35

출력:
  ../02_시뮬레이션_데이터/etab_flameout_fault_data.csv  (고장: onset/partial/full, 3,000샘플)

정상 베이스라인은 별도로 만들지 않는다 — 07_fuel_fault_generator.py가 생성하는
combustor_real_normal_data.csv(공통 엔진 모델의 η_b=1.0/faultFactor_fuel=1.0
정상 베이스라인)를 시나리오 1·2가 그대로 공유한다(Issue #7 모델링 수정 방향 3번).
"""

import numpy as np
import pandas as pd
from pathlib import Path
from real_engine_model_utils import inlet, compressor, combustor, turbine, COMB_REF0

N_PER_STAGE = 1000
SEED        = 706          # 2026-07-06, Issue #7 결정일

OUTPUT_DIR  = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FAULT_PATH  = OUTPUT_DIR / "etab_flameout_fault_data.csv"
NORMAL_PATH = OUTPUT_DIR / "combustor_real_normal_data.csv"   # 07과 공유(신규 생성 안 함)

NOISE_LEVEL = 0.003   # 07_fuel_fault_generator.py와 동일 관례(순수 고장효과 분리)

STAGES = [
    ('onset',   0.65, 0.80),
    ('partial', 0.35, 0.65),
    ('full',    0.05, 0.35),
]


def run_case(eta_b, rng):
    """지상 설계점(altitude=0, mach=0 고정) + comb_ref 미세변동 + 0.3% 센서노이즈.
    07_fuel_fault_generator.py의 run_case()와 동일 구조 — far_correction_factor
    자리에 faultFactor_fuel 대신 η_b를 대입하는 것이 방안 B의 전부다(Issue #7)."""
    comb_ref = COMB_REF0 + rng.uniform(-15.0, 15.0)

    T1, P1 = inlet(altitude=0.0, mach=0.0)
    T2, P2, comp_power = compressor(T1, P1)
    T3, P3, far_demand, far_actual = combustor(T2, P2, comb_ref, eta_b)
    temp_diff_comp = T1 - T2
    T4, P4, turb_power = turbine(T3, P3, temp_diff_comp, far_actual)

    out = dict(T1_K=T1, P1_Pa=P1, T2_K=T2, P2_Pa=P2,
               comb_ref_K=comb_ref, T3_K=T3, P3_Pa=P3,
               T4_K=T4, P4_Pa=P4,
               FAR_demand=far_demand, FAR_actual=far_actual,
               eta_b=eta_b,
               compressor_power_kW=comp_power / 1000.0,
               turbine_power_kW=turb_power / 1000.0,
               TIT_error_K=comb_ref - T3)   # 명령(comb_ref) - 실제(T3)

    for k in ['T1_K', 'P1_Pa', 'T2_K', 'P2_Pa', 'T3_K', 'P3_Pa', 'T4_K', 'P4_Pa',
              'compressor_power_kW', 'turbine_power_kW']:
        out[k] = out[k] * (1.0 + rng.normal(0.0, NOISE_LEVEL))
    return out


if __name__ == "__main__":
    if not NORMAL_PATH.exists():
        raise SystemExit(
            f"⚠ {NORMAL_PATH.name} 없음 → 먼저 `python 07_fuel_fault_generator.py`를 "
            f"실행해 공통 정상 베이스라인을 생성하세요. 시나리오 1·2는 동일 엔진모델을 "
            f"공유합니다(Issue #7 모델링 수정 방향 3번)."
        )

    rng = np.random.default_rng(SEED)
    fault_records = []; sample_id = 0
    for stage_name, lo, hi in STAGES:
        for _ in range(N_PER_STAGE):
            eta_b = rng.uniform(lo, hi)
            rec = run_case(eta_b, rng)
            rec.update(sample_id=sample_id, label='fault', fault_type='FF-FLAMEOUT',
                       fault_stage=stage_name, jssg_ref='§3.2.2.3.5/3.2.2.6',
                       correction_scheme='PlanB_input_far_scaling',
                       source_issue='github.com/chestnutbread/Red-horse/issues/7')
            fault_records.append(rec)
            sample_id += 1

    df_fault = pd.DataFrame(fault_records)
    df_fault.to_csv(FAULT_PATH, index=False)
    print(f"✅ 연소효율 저하 실화 데이터(방안 B, 실제모델) {len(df_fault):,}샘플 → {FAULT_PATH}")
    print(df_fault.groupby('fault_stage')[['eta_b', 'T3_K', 'TIT_error_K', 'turbine_power_kW']].mean().round(2))
    print("\n검증: η_b→1.0 극한에서 far_actual→far_demand, TIT_error_K→0 (comb_ref 정상 추종)이어야 함.")
    print("      정량 비교는 06_vhdl_comparison.py '시나리오 D' 절 참조 (Issue #7 요청사항 2).")
