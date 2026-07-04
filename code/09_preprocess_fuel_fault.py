"""
09_preprocess_fuel_fault.py
시나리오2(연료계통 고장) 데이터 전처리 파이프라인.

Q. 전처리는 Python으로 하는 게 맞는가?
A. 맞습니다. StandardScaler/PCA 학습, train-정상/holdout-정상 분리, 라벨 컬럼 제거 같은
   작업은 SQL/스프레드시트보다 pandas + scikit-learn으로 하는 게 표준적이고, 이미
   02_anomaly_detector.py도 이 방식(pandas→StandardScaler→PCA)을 쓰고 있습니다.
   이 파일은 그 파이프라인을 아래 두 가지로 보완합니다.
     1) TIT_error_K(comb_ref_K − T3_K)를 명시적 피처로 포함 — 지난 분석에서
        가장 강한 고장 시그니처인데 기존 FEATURES_FUEL에는 빠져 있었음.
     2) 정상 데이터를 train/holdout으로 분리해서, "학습에 쓴 데이터로 그대로
        임계값을 정하는" 낙관적 편향을 피함.

입력: ../02_시뮬레이션_데이터/combustor_real_normal_data.csv, fuel_fault_data.csv
출력: 전처리된 numpy 배열 + fit된 scaler (다른 스크립트에서 import해서 재사용 가능)
"""

from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

DATA_DIR = Path(__file__).parent.parent / "02_시뮬레이션_데이터"

# ── 1) 라벨성/누수 컬럼 제외, 실제 물리 측정값만 피처로 사용 ──────────────
# 제외 이유:
#   sample_id, label, fault_type, fault_stage, twin_builder_case, source_issue : 메타/정답 라벨
#   faultFactor_fuel : 정답 그 자체 (절대 넣으면 안 됨 — label leakage)
#   FAR_demand        : 목표치 역산값, 고장 여부와 무관 (요구량일 뿐 실제 공급량 아님)
#   comb_ref_K        : 명령값 자체는 정상/고장 모두 같은 분포로 랜덤 흔들어놨음 (설계 의도상 무관)
#   T1_K, P1_Pa       : Inlet 조건 — 고장(Combustor 하류)과 무관, 노이즈만 있음
FEATURES = [
    'T2_K', 'P2_Pa',                 # Compressor 출구 (고장과 무관하지만 정규화 기준점 역할)
    'T3_K', 'P3_Pa',                 # Combustor 실제 출구 — 핵심
    'T4_K', 'P4_Pa',                 # Turbine 출구 — 핵심
    'compressor_power_kW',
    'turbine_power_kW',              # 실측 결과 판별력 약함(계속 관찰 필요, 아래 참고)
    'FAR_actual',                    # 핵심
    'TIT_error_K',                   # ★ 가장 강한 고장 시그니처. 기존 코드에 없었음 → 추가
]

# 참고: turbine_power_kW는 T3·T4가 같이 떨어져서 (T3−T4) 차이가 잘 안 변해
# 판별력이 약하다는 게 실측으로 확인됨 (정상 1377~1385 vs moderate 1368~1376, 거의 겹침).
# 그래도 PCA에 넣어두는 건 무방 — 표준화 이후엔 분산이 작은 피처는 자동으로 덜 반영됨.


@dataclass
class PreprocessedData:
    X_train_normal: np.ndarray   # 정상 중 학습용 (scaler/PCA fit에 사용)
    X_holdout_normal: np.ndarray  # 정상 중 홀드아웃 (임계값 산정에 사용, fit에는 미사용)
    X_fault: np.ndarray
    df_fault_meta: pd.DataFrame  # fault_stage 등 원본 라벨(평가용, 학습엔 미사용)
    scaler: StandardScaler
    feature_names: list


def load_raw():
    df_normal = pd.read_csv(DATA_DIR / "combustor_real_normal_data.csv")
    df_fault  = pd.read_csv(DATA_DIR / "fuel_fault_data.csv")
    return df_normal, df_fault


def preprocess(test_size: float = 0.2, random_state: int = 42) -> PreprocessedData:
    df_normal, df_fault = load_raw()

    # 결측치 확인 (있으면 여기서 바로 드러남 — 있을 경우 dropna 또는 imputation 필요)
    missing_normal = df_normal[FEATURES].isna().sum().sum()
    missing_fault  = df_fault[FEATURES].isna().sum().sum()
    if missing_normal or missing_fault:
        print(f"⚠ 결측치 발견: normal={missing_normal}, fault={missing_fault} → 행 제거")
        df_normal = df_normal.dropna(subset=FEATURES)
        df_fault  = df_fault.dropna(subset=FEATURES)

    # 2) 정상 데이터를 train/holdout으로 분리
    #    - train: scaler.fit + PCA.fit 에만 사용
    #    - holdout: 임계값(threshold) 산정에 사용 → train에 없던 데이터로 검증하는 셈이라
    #      "학습데이터로 그대로 임계값 잡기"보다 덜 낙관적인 추정치가 나옴
    df_train, df_holdout = train_test_split(
        df_normal, test_size=test_size, random_state=random_state
    )

    # 3) 스케일링: StandardScaler는 반드시 train(정상)만으로 fit
    #    (온도 K 단위 수백~천, 압력 Pa 단위 10만~100만, FAR 0.01~0.02 — 스케일 차이가
    #     크기 때문에 표준화 없이 PCA하면 압력 컬럼이 분산을 독식함)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(df_train[FEATURES].values)
    X_holdout = scaler.transform(df_holdout[FEATURES].values)
    X_fault = scaler.transform(df_fault[FEATURES].values)

    return PreprocessedData(
        X_train_normal=X_train,
        X_holdout_normal=X_holdout,
        X_fault=X_fault,
        df_fault_meta=df_fault[['fault_stage', 'faultFactor_fuel', 'TIT_error_K']].reset_index(drop=True),
        scaler=scaler,
        feature_names=FEATURES,
    )


if __name__ == "__main__":
    data = preprocess()
    print(f"전처리 완료:")
    print(f"  train(정상, PCA/scaler fit용) : {data.X_train_normal.shape}")
    print(f"  holdout(정상, 임계값 산정용)   : {data.X_holdout_normal.shape}")
    print(f"  fault(고장, 평가용)            : {data.X_fault.shape}")
    print(f"  피처 {len(data.feature_names)}개: {data.feature_names}")
    print("\n표준화 후 평균/표준편차 확인 (train은 평균≈0, 표준편차≈1이어야 정상):")
    print(f"  train mean={data.X_train_normal.mean():.4f}, std={data.X_train_normal.std():.4f}")

    print("\n이 결과를 그대로 02_anomaly_detector.py 스타일 PCA(pca.fit(X_train_normal))에 넣거나,")
    print("scikit-learn의 IsolationForest, OneClassSVM 등 다른 비지도 이상탐지 모델에도 바로 사용 가능.")
