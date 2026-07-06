"""
03_preprocess_flameout.py
시나리오1(연소효율 η_b 저하 실화, Plan A) 데이터 전처리 파이프라인.

[2026-07-08] 시나리오2에는 09_preprocess_fuel_fault.py가 있는데 시나리오1에는
그에 대응하는 전처리 스크립트가 없어서(02_anomaly_detector.py가 스케일링/PCA를
전부 인라인으로 처리, train/holdout 분리 없음) 09와 동일한 구조로 신설했다.
번호는 01(정상데이터)·02(이상탐지)·04(고장데이터) 사이에 비어 있던 03을 사용—
9번이 시나리오2 전처리이니 대응 관계상 자연스러운 자리라고 판단.

09_preprocess_fuel_fault.py와 동일한 두 가지 보완:
  1) 정상 데이터를 train/holdout으로 분리 — "학습에 쓴 데이터로 그대로 임계값을
     정하는" 낙관적 편향 방지 (02_anomaly_detector.py는 현재 이 분리가 없음).
  2) 라벨성/누수 컬럼을 명시적으로 배제 — 특히 eta_b는 고장 여부 그 자체이므로
     반드시 피처에서 제외해야 함(09의 faultFactor_fuel과 동일한 성격의 누수 위험).

입력: ../02_시뮬레이션_데이터/normal_data.csv, jssg_fault_data.csv
출력: 전처리된 numpy 배열 + fit된 scaler (다른 스크립트에서 import해서 재사용 가능)
"""

from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

DATA_DIR = Path(__file__).parent.parent / "02_시뮬레이션_데이터"

# ── 라벨성/누수 컬럼 제외, 실제 물리 측정값만 피처로 사용 ──────────────────
# 제외 이유:
#   sample_id, label, fault_type, fault_stage, jssg_ref : 메타/정답 라벨
#   eta_b            : 정답 그 자체 (절대 넣으면 안 됨 — label leakage,
#                       09의 faultFactor_fuel과 동일한 성격)
#   pi_c, FAR         : 정상·고장 데이터 모두 turboprop_simulator_utils.RANGES에서
#                       동일하게 무작위 샘플링됨 — 고장 여부와 무관한 운전조건 잡음
#   T1_K, P1_kPa      : Inlet 조건 — Combustor 상류라 고장(η_b 저하)과 무관
FEATURES = [
    'T2_K', 'P2_kPa',      # Compressor 출구 (정규화 기준점)
    'T3_K', 'P3_kPa',      # Combustor 출구 — 핵심 (η_b가 직접 작용하는 지점)
    'T4_K', 'P4_kPa',      # Turbine 출구
    'T5_K',                 # = EGT, Power Turbine 출구
    'W_net_kW',             # 순출력
    'EGT_K',                # T5_K와 동일값이나 02_anomaly_detector.py 호환을 위해 유지
    'SFC',                  # 연료소모율 — η_b 저하 시 SFC 악화(같은 연료로 열 발생 감소)
    'eta_thermal',          # 열효율
]


@dataclass
class PreprocessedData:
    X_train_normal: np.ndarray    # 정상 중 학습용 (scaler/PCA fit에 사용)
    X_holdout_normal: np.ndarray  # 정상 중 홀드아웃 (임계값 산정에 사용, fit에는 미사용)
    X_fault: np.ndarray
    df_fault_meta: pd.DataFrame   # fault_stage, eta_b 등 원본 라벨(평가용, 학습엔 미사용)
    scaler: StandardScaler
    feature_names: list


def load_raw():
    df_normal = pd.read_csv(DATA_DIR / "normal_data.csv")
    df_fault  = pd.read_csv(DATA_DIR / "jssg_fault_data.csv")
    return df_normal, df_fault


def preprocess(test_size: float = 0.2, random_state: int = 42) -> PreprocessedData:
    df_normal, df_fault = load_raw()

    missing_normal = df_normal[FEATURES].isna().sum().sum()
    missing_fault  = df_fault[FEATURES].isna().sum().sum()
    if missing_normal or missing_fault:
        print(f"⚠ 결측치 발견: normal={missing_normal}, fault={missing_fault} → 행 제거")
        df_normal = df_normal.dropna(subset=FEATURES)
        df_fault  = df_fault.dropna(subset=FEATURES)

    # 정상 데이터를 train/holdout으로 분리
    #   - train: scaler.fit + PCA.fit 에만 사용
    #   - holdout: 임계값(threshold) 산정에 사용 → 낙관적 편향 방지
    df_train, df_holdout = train_test_split(
        df_normal, test_size=test_size, random_state=random_state
    )

    # 스케일링: StandardScaler는 반드시 train(정상)만으로 fit
    scaler = StandardScaler()
    X_train = scaler.fit_transform(df_train[FEATURES].values)
    X_holdout = scaler.transform(df_holdout[FEATURES].values)
    X_fault = scaler.transform(df_fault[FEATURES].values)

    return PreprocessedData(
        X_train_normal=X_train,
        X_holdout_normal=X_holdout,
        X_fault=X_fault,
        df_fault_meta=df_fault[['fault_stage', 'eta_b']].reset_index(drop=True),
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
