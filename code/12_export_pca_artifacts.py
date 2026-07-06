"""
12_export_pca_artifacts.py
13_gui_dashboard.py가 재학습 없이 바로 불러 쓸 수 있도록 scaler + PCA(+95th pct
임계값)를 joblib 파일로 저장한다.

⚠ 중요 — 03_preprocess_flameout.py를 그대로 재사용하지 않는 이유:
  13_gui_dashboard.py는 real_engine_model_utils.py(공통 엔진 물리모델)를 직접
  호출해 슬라이더 입력을 실시간 계산한다. 이 물리모델은 07/10이 만드는 CSV
  스키마(T2_K,P2_Pa,T3_K,P3_Pa,T4_K,P4_Pa,compressor_power_kW,turbine_power_kW,
  FAR_actual,TIT_error_K)를 따른다.
  반면 03_preprocess_flameout.py는 시나리오1의 Plan A 데이터(01/04,
  turboprop_simulator_utils.py — 완전히 다른 물리식, T5_K/W_net_kW/eta_thermal/
  kPa 단위 포함)를 전처리하는 스크립트라 이 둘의 피처 스키마가 서로 호환되지
  않는다. 그래서 GUI용 시나리오1은 03이 아니라 10_combustion_efficiency_
  fault_generator.py(방안B, 실제모델)의 출력을 07/09와 동일한 피처 스키마로
  전처리하는 별도 함수(preprocess_realmodel)를 이 파일 안에 둔다.
  03/normal_data.csv/jssg_fault_data.csv 기반 파이프라인은 04_vhdl_comparison.py·
  normal.py의 Plan A 비교 목적으로 계속 유지된다 — 폐기 아님, 용도가 다름.

사전 준비:
  python 01_turboprop_simulator.py            (Plan A 정상 — 다른 용도, 여기선 불필요)
  python 07_fuel_fault_generator.py           (공통 정상 베이스라인 + 시나리오2 고장)
  python 10_combustion_efficiency_fault_generator.py   (시나리오1 고장, 방안B)
  python 12_export_pca_artifacts.py

산출물: ../04_학습산출물/scenario{1,2}_{scaler,pca,meta}.joblib
  meta.joblib = {"threshold": float, "feature_names": list}

n_components=6, threshold=95th pct 근거는 README.md "근거 자료" 표 참조
(arXiv:2505.24044 / anomaly detection 표준 관례).
"""

from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA

HERE = Path(__file__).parent
DATA_DIR = HERE.parent / "02_시뮬레이션_데이터"
ARTIFACT_DIR = HERE.parent / "04_학습산출물"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

N_COMPONENTS = 6
THRESHOLD_PCT = 95

# 07/10이 공유하는 real_engine_model_utils.py 기반 CSV 스키마 — 09_preprocess_fuel_fault.py
# 와 동일한 피처 선정 기준(라벨 누수 컬럼 제외, TIT_error_K 포함) 그대로 사용
REALMODEL_FEATURES = [
    'T2_K', 'P2_Pa',
    'T3_K', 'P3_Pa',
    'T4_K', 'P4_Pa',
    'compressor_power_kW', 'turbine_power_kW',
    'FAR_actual', 'TIT_error_K',
]


@dataclass
class PreprocessedData:
    X_train_normal: np.ndarray
    X_holdout_normal: np.ndarray
    X_fault: np.ndarray
    scaler: StandardScaler
    feature_names: list


def preprocess_realmodel(normal_csv: str, fault_csv: str,
                          test_size: float = 0.2, random_state: int = 42) -> PreprocessedData:
    """07/10(공통 real_engine_model_utils 기반) CSV 전용 전처리.
    09_preprocess_fuel_fault.py와 동일한 로직(train/holdout 분리, StandardScaler)이며
    시나리오1(10)·시나리오2(07/09) 양쪽에 그대로 재사용 가능하도록 일반화했다."""
    df_normal = pd.read_csv(DATA_DIR / normal_csv)
    df_fault = pd.read_csv(DATA_DIR / fault_csv)

    missing = df_normal[REALMODEL_FEATURES].isna().sum().sum() + df_fault[REALMODEL_FEATURES].isna().sum().sum()
    if missing:
        print(f"⚠ 결측치 {missing}건 발견 → 행 제거")
        df_normal = df_normal.dropna(subset=REALMODEL_FEATURES)
        df_fault = df_fault.dropna(subset=REALMODEL_FEATURES)

    df_train, df_holdout = train_test_split(df_normal, test_size=test_size, random_state=random_state)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(df_train[REALMODEL_FEATURES].values)
    X_holdout = scaler.transform(df_holdout[REALMODEL_FEATURES].values)
    X_fault = scaler.transform(df_fault[REALMODEL_FEATURES].values)

    return PreprocessedData(
        X_train_normal=X_train,
        X_holdout_normal=X_holdout,
        X_fault=X_fault,
        scaler=scaler,
        feature_names=REALMODEL_FEATURES,
    )


def reconstruction_error(X: np.ndarray, pca: PCA) -> np.ndarray:
    X_proj = pca.transform(X)
    X_recon = pca.inverse_transform(X_proj)
    return np.sum((X - X_recon) ** 2, axis=1)


def export(name: str, data: PreprocessedData):
    pca = PCA(n_components=N_COMPONENTS, random_state=42)
    pca.fit(data.X_train_normal)

    holdout_err = reconstruction_error(data.X_holdout_normal, pca)
    threshold = float(np.percentile(holdout_err, THRESHOLD_PCT))

    fault_err = reconstruction_error(data.X_fault, pca)
    detect_rate = float(np.mean(fault_err > threshold))

    joblib.dump(data.scaler, ARTIFACT_DIR / f"{name}_scaler.joblib")
    joblib.dump(pca, ARTIFACT_DIR / f"{name}_pca.joblib")
    joblib.dump(
        {"threshold": threshold, "feature_names": data.feature_names},
        ARTIFACT_DIR / f"{name}_meta.joblib",
    )

    print(f"✅ {name}: threshold={threshold:.3f} (holdout {THRESHOLD_PCT}th pct), "
          f"fault 탐지율={detect_rate*100:.1f}% → {ARTIFACT_DIR}")


if __name__ == "__main__":
    normal_csv = "combustor_real_normal_data.csv"  # 07이 생성, 07/10 공유 베이스라인

    data_s1 = preprocess_realmodel(normal_csv, "etab_flameout_fault_data.csv")   # 시나리오1 (10, 방안B)
    data_s2 = preprocess_realmodel(normal_csv, "fuel_fault_data.csv")            # 시나리오2 (07)

    export("scenario1", data_s1)
    export("scenario2", data_s2)

    print("\n13_gui_dashboard.py 실행 준비 완료 → streamlit run 13_gui_dashboard.py")
