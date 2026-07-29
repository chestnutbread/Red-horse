"""
10_combustion_efficiency_fault_generator.py
연소효율(η_b) 저하형 실화(Flameout) 데이터 생성 — 시나리오 1

[2026-07-08, GitHub Issue #9 반영 — 방안 B 우회 종료, 정식 구현으로 전환]
Issue #6에서 "VHDL Combustor entity에는 η_b 파라미터 자체가 없다"고 확인되어
방안 B(η_b를 faultFactor_fuel 자리에 대신 대입하는 우회)를 Issue #7에서 임시
채택했었다. 그런데 Issue #7에서 이 우회의 부작용(η_b와 faultFactor_fuel이 같은
메커니즘이 되어 시나리오1·2를 결과 데이터로 구분할 수 없음)이 드러나 Issue #8로
Combustor entity에 독립 eta_b 포트 추가를 요청했고, 팀원이 Issue #9에서 실제로
반영했다 — "fuel_air_ratio_demand/actual 계산식은 절대 수정하지 않음"이라는
요청사항을 그대로 지키면서, eta_b는 열발생 항(fuel_calorific)에만 곱하도록
Combustor entity/architecture를 수정함(실제 코드는 real_engine_model_utils.py
combustor() 함수 참조).

★ 이 스크립트의 핵심 변경점: 이제 eta_b를 faultFactor_fuel 자리에 대입하지 않고
  combustor()의 독립 인자로 그대로 전달한다 — faultFactor_fuel=1.0(연료공급 정상
  고정), eta_b=목표값. 그 결과 시나리오1에서는 FAR_actual≈FAR_demand(연료공급은
  정상)가 유지된 채로 T3만 떨어지는, 방안 A가 원래 의도했던 물리 그대로 재현된다.
  방안 B 시절과 달리 이제 시나리오1·2가 진짜로 물리적으로 구분되는 신호
  (FAR_demand-actual 격차, Wf)를 갖는다 — Issue #6이 원래 요구했던 상태.

이 스크립트는 04_jssg_fault_generator.py(Plan A, η_b를 브레이턴 에너지식에 직접
곱하는 근사 모델)를 대체하지 않는다 — 04는 계속 병행 보관한다(비교 기준용).

⚠ 검증 기준 갱신: 방안 B 시절엔 "Plan A와 절대값이 다를 수밖에 없다"고 했지만,
지금은 진짜 방안 A 방식이라 Plan A와 물리 구조가 훨씬 가까워졌다 — η_b=1.0 극한
수렴 확인 + FAR_demand≈FAR_actual 유지 확인이 핵심 검증 항목이다(아래 stage
loop 이후 출력 참조).

η_b 단계 (JSSG-2007A §3.2.2.3.5 / §3.2.2.6, 04_jssg_fault_generator.py와 동일 근거):
  onset  (초기): η_b = 0.65~0.80
  partial(부분): η_b = 0.35~0.65  (onset~full 선형 보간 추정 — ⚠ JSSG 정의 없음, 임의 설정)
  full   (완전): η_b = 0.05~0.35

출력:
  ../02_시뮬레이션_데이터/etab_flameout_fault_data.csv  (고장: onset/partial/full, 3,000샘플)

정상 베이스라인은 별도로 만들지 않는다 — 07_fuel_fault_generator.py가 생성하는
combustor_real_normal_data.csv(공통 엔진 모델의 η_b=1.0/faultFactor_fuel=1.0
정상 베이스라인)를 시나리오 1·2가 그대로 공유한다.

[2026-07-08] 07번 데이터가 6,000→7,000건으로 조정됐지만, 이 파일(시나리오1,
onset/partial/full 각 1,000샘플=3,000)은 팀원 모델링이 시나리오1도 7,000건
기준인지 확인되기 전까지는 조정 대상이 아니다(2026-07-08 기준, 미확인).

[2026-07-29, 세은 수정] 이 파일 아래쪽에 구버전(Issue #7 방안B) 스크립트 전체가
가드 없이 중복 이어붙여져 있던 버그를 제거했다 — 실행 시 두 번째 if __name__
블록이 combustor() 반환값 개수 불일치로 크래시하던 문제였다(GitHub Issue #30
참조). 크래시로 끝나 실제 데이터 덮어쓰기는 발생하지 않았고, 업로드 대상
Supabase 테이블(fuel_fault_samples)도 애초에 존재하지 않아 데이터 영향은 없었음
— 이번 수정은 코드 정리만 해당.
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
    07_fuel_fault_generator.py의 run_case()와 대칭 구조 — 07은 faultFactor_fuel만
    바꾸고 eta_b=1.0 고정, 여기는 eta_b만 바꾸고 faultFactor_fuel=1.0 고정
    (Issue #9, 완전히 독립된 두 인자)."""
    comb_ref = COMB_REF0 + rng.uniform(-15.0, 15.0)

    T1, P1 = inlet(altitude=0.0, mach=0.0)
    T2, P2, comp_power = compressor(T1, P1)
    T3, P3, far_demand, far_actual, wf = combustor(T2, P2, comb_ref, faultFactor_fuel=1.0, eta_b=eta_b)
    temp_diff_comp = T1 - T2
    T4, P4, turb_power = turbine(T3, P3, temp_diff_comp, far_actual)

    out = dict(T1_K=T1, P1_Pa=P1, T2_K=T2, P2_Pa=P2,
               comb_ref_K=comb_ref, T3_K=T3, P3_Pa=P3,
               T4_K=T4, P4_Pa=P4,
               FAR_demand=far_demand, FAR_actual=far_actual, Wf_kg_s=wf,
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
                       correction_scheme='independent_eta_b_port',
                       source_issue='github.com/chestnutbread/Red-horse/issues/9')
            fault_records.append(rec)
            sample_id += 1

    df_fault = pd.DataFrame(fault_records)
    df_fault.to_csv(FAULT_PATH, index=False)
    print(f"✅ 연소효율 저하 실화 데이터(독립 eta_b, Issue #9) {len(df_fault):,}샘플 → {FAULT_PATH}")
    print(df_fault.groupby('fault_stage')[['eta_b', 'T3_K', 'TIT_error_K', 'FAR_demand', 'FAR_actual', 'turbine_power_kW']].mean().round(4))

    far_gap = (df_fault['FAR_demand'] - df_fault['FAR_actual']).abs()
    print(f"\n검증1: FAR_demand - FAR_actual 절대차 평균 = {far_gap.mean():.6f} (연료공급 정상 유지 확인, 0에 가까워야 함)")
    print("검증2: η_b→1.0 극한에서 T3→comb_ref, TIT_error_K→0 이어야 함 (아래 06_vhdl_comparison.py 시나리오 D 참조)")
    print("검증3(원인 구분): 07_fuel_fault_generator.py 결과와 비교 시 이 파일은 FAR_actual≈FAR_demand,")
    print("               07은 FAR_actual<FAR_demand — 이 차이가 Issue #6/#8이 요구했던 원인 구분 신호다.")
