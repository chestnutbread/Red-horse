"""
15_apply_analysis_noise.py
Red-Horse APISAT 2026 논문 — 분석/Figure용 공통 노이즈 주입 유틸리티

[배경, 2026-07-30]
Supabase에 저장된 VHDL-AMS(Twin Builder) 및 Python 시계열 원본 데이터는 둘 다
노이즈 없는 결정론적(deterministic) 솔버/모델 출력임을 직접 확인함
(ENGINE_STABLE_Python 정상상태 T4=정확히 1250.000..., MQ-9_*_25000ft/M0.45
계열도 등간격 스무스 램프 — 무작위 산포 없음). 코드베이스에 이미 존재하는
add_sensor_noise()(turboprop_simulator_utils.py, ±0.5%, 07/10 결함 생성기에서는
±0.3%)는 결함 시나리오 학습 데이터 생성에만 쓰였고, 이 논문의 본 비교
Figure(4~11)에 쓰인 데이터에는 적용되지 않았음.

[목적]
논문 Sec. 3(Experimental Setup)에 새로 추가한 방법론 문단과 일치하도록,
Python 예측값과 Twin Builder 측정값 양쪽에 "동일한 기준"으로 사후(post-hoc)
센서 노이즈를 주입한 뒤 분석·Figure 생성에 사용한다. 두 데이터셋에 같은
노이즈 모델을 적용해야 "measured vs. numerical simulation" 비교가 노이즈
유무 비대칭 없이 공정해진다.

[사용법]
    from apply_analysis_noise import apply_common_noise
    df_noisy = apply_common_noise(df, seed=42)   # df: T2..T5, P2..P5 컬럼 포함

준서님이 1373K/GR 정정 데이터를 업로드하면, 새 테이블에 대해 이 함수를
그대로 재실행하기만 하면 Figure 재생성 준비가 끝남 (컬럼 스키마 동일 가정).
"""

import numpy as np
import pandas as pd

# 프로젝트 기존 관례와 동일한 값 (turboprop_simulator_utils.add_sensor_noise 참조)
NOISE_LEVEL = 0.005  # ±0.5%, Gaussian, multiplicative

NOISE_COLUMNS = ["T1", "T2", "T3", "T4", "T5", "P1", "P2", "P3", "P4", "P5"]


def apply_common_noise(
    df: pd.DataFrame,
    noise_level: float = NOISE_LEVEL,
    columns=None,
    seed: int | None = None,
) -> pd.DataFrame:
    """Twin Builder / Python 데이터 양쪽에 동일 기준으로 곱셈형 가우시안 노이즈 주입.

    df: 원본 데이터프레임 (컬럼명은 대소문자 무관하게 매칭 시도)
    noise_level: 표준편차 비율 (기본 0.5%, 프로젝트 기존 관례와 동일)
    columns: 노이즈를 적용할 컬럼 목록 (기본: T1-T5, P1-P5 중 존재하는 것만)
    seed: 재현성을 위한 RNG 시드. Twin Builder/Python 두 데이터셋을 같은 seed로
          호출하면 "같은 노이즈 실현(realization)"이 아니라 "같은 노이즈 통계"가
          적용됨 — 두 데이터셋은 서로 다른 물리 신호이므로 실현값 자체를 공유할
          필요는 없고, 노이즈의 통계적 기준(σ)만 동일하면 됨. 다만 완전한 재현성이
          필요하면 호출부에서 seed를 명시적으로 고정할 것.
    """
    rng = np.random.default_rng(seed)
    out = df.copy()

    if columns is None:
        # 대소문자 무관 매칭
        lower_map = {c.lower(): c for c in df.columns}
        columns = [lower_map[c.lower()] for c in NOISE_COLUMNS if c.lower() in lower_map]

    if not columns:
        raise ValueError(
            "No matching noise columns found. Expected some subset of "
            f"{NOISE_COLUMNS}, got columns={list(df.columns)}"
        )

    for col in columns:
        out[col] = out[col] * (1 + rng.normal(0, noise_level, size=len(out)))

    return out


def apply_to_pair(df_measured: pd.DataFrame, df_python: pd.DataFrame, seed: int | None = None):
    """Twin Builder(measured)와 Python(numerical simulation) 데이터에
    동일 σ로 각각 노이즈를 주입해서 (measured_noisy, numsim_noisy) 튜플 반환.

    두 데이터프레임에 동일한 seed를 넘기면 재현 가능한 결과를 얻을 수 있음.
    seed=None이면 매 실행마다 다른 노이즈 실현이 나오므로, 논문용 최종 Figure는
    반드시 고정 seed로 재실행해서 재현성을 확보할 것 (권장: seed=42).
    """
    measured_noisy = apply_common_noise(df_measured, seed=seed)
    # Python(수치 시뮬레이션) 쪽은 seed+1 등으로 분리해 서로 다른 노이즈 실현을 쓰되
    # 동일 σ(NOISE_LEVEL)를 적용 — "같은 기준으로 노이즈를 넣는다"는 요건은
    # 실현값 공유가 아니라 통계적 기준(분산) 동일성을 의미함.
    numsim_noisy = apply_common_noise(df_python, seed=None if seed is None else seed + 1)
    return measured_noisy, numsim_noisy


if __name__ == "__main__":
    # 간단한 자체 테스트 (실제 Supabase 연결 없이 동작 확인용)
    demo = pd.DataFrame(
        {
            "t2": np.full(5, 288.15),
            "t3": np.full(5, 560.0),
            "t4": np.full(5, 1250.0),
            "p2": np.full(5, 101.325),
        }
    )
    noisy = apply_common_noise(demo, seed=42)
    print("원본:\n", demo)
    print("\n노이즈 주입 후 (σ=0.5%):\n", noisy)
