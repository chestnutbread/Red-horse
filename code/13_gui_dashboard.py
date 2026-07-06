"""
13_gui_dashboard.py
TPE331-10 실화(시나리오1)/연료계통고장(시나리오2) 나란히 비교 GUI (Streamlit)

구성(2026-07-08 확인 완료):
  - 좌: 시나리오1(실화, η_b 슬라이더) / 우: 시나리오2(연료계통고장, faultFactor_fuel 슬라이더)
  - 각 패널: 실시간 엔진 파라미터(T1~T4, P1~P4, EGT, W_net, SFC 근사) + 이상탐지 게이지 + 상태판
  - 하단: 고장 원인 추정 패널 — 포함하되 한계 명시(아래 CAUSE_DISCLAIMER 참조)

물리 계산은 real_engine_model_utils.py를 그대로 import해서 쓴다. 즉 향후
연소기/터빈 모델링이 바뀌어도 이 파일은 수정할 필요 없이 real_engine_model_utils.py
+ 12_export_pca_artifacts.py 재실행만으로 반영된다("파이썬 코드만 수정하면
사용할 수 있도록" 요청사항).

사전 준비:
  pip install streamlit joblib scikit-learn pandas numpy --break-system-packages
  python 12_export_pca_artifacts.py   (04_학습산출물/scenario{1,2}_*.joblib 생성)
  streamlit run 13_gui_dashboard.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import streamlit as st

from real_engine_model_utils import inlet, compressor, combustor, turbine, COMB_REF0, MFLOW

HERE = Path(__file__).parent
ARTIFACT_DIR = HERE.parent / "04_학습산출물"

CAUSE_DISCLAIMER = (
    "⚠ 원인 추정은 참고용입니다. 현재 방안B 구조상 η_b(시나리오1)와 "
    "faultFactor_fuel(시나리오2)은 물리적으로 동일한 입력단(far_actual = "
    "far_demand × factor)을 공유합니다. 아래 판정은 각 시나리오에 설정된 "
    "값 구간을 근거로 한 표시일 뿐, 두 원인이 결과 데이터에서 물리적으로 "
    "분리된다는 것을 의미하지 않습니다. 신뢰할 수 있는 원인(고장 유형) 진단을 "
    "위해서는 정상상태 값이 아닌 과도응답(램프 시간 등 변화율) 기반 동적 데이터와 "
    "실측 검증이 추가로 필요합니다."
)

st.set_page_config(page_title="TPE331-10 실시간 고장 시뮬레이터", layout="wide")
st.title("TPE331-10 실시간 고장 탐지 데모")
st.caption("real_engine_model_utils.py 공통 엔진 물리모델 기반 — Issue #7 방안B")


def compute_state(far_correction_factor: float) -> dict:
    """real_engine_model_utils.py 함수를 그대로 호출 — 07/10과 동일 계산 경로."""
    T1, P1 = inlet(altitude=0.0, mach=0.0)
    T2, P2, comp_power = compressor(T1, P1)
    T3, P3, far_demand, far_actual = combustor(T2, P2, COMB_REF0, far_correction_factor)
    temp_diff_comp = T1 - T2
    T4, P4, turb_power = turbine(T3, P3, temp_diff_comp, far_actual)

    comp_power_kW = comp_power / 1000.0
    turb_power_kW = turb_power / 1000.0
    w_net_kW = turb_power_kW - comp_power_kW
    tit_error = COMB_REF0 - T3
    fuel_flow_kg_s = far_actual * MFLOW
    sfc = (fuel_flow_kg_s * 3600.0) / max(w_net_kW, 1e-6)   # kg/kWh 근사

    return dict(
        T1_K=T1, P1_Pa=P1, T2_K=T2, P2_Pa=P2, T3_K=T3, P3_Pa=P3, T4_K=T4, P4_Pa=P4,
        compressor_power_kW=comp_power_kW, turbine_power_kW=turb_power_kW,
        W_net_kW=w_net_kW, FAR_demand=far_demand, FAR_actual=far_actual,
        TIT_error_K=tit_error, EGT_K=T4, SFC=sfc,
    )


@st.cache_resource
def load_artifacts(name: str):
    scaler_path = ARTIFACT_DIR / f"{name}_scaler.joblib"
    pca_path = ARTIFACT_DIR / f"{name}_pca.joblib"
    meta_path = ARTIFACT_DIR / f"{name}_meta.joblib"
    if not (scaler_path.exists() and pca_path.exists() and meta_path.exists()):
        return None
    return {
        "scaler": joblib.load(scaler_path),
        "pca": joblib.load(pca_path),
        "meta": joblib.load(meta_path),
    }


def anomaly_score(state: dict, artifacts: dict) -> tuple:
    feature_names = artifacts["meta"]["feature_names"]
    x = np.array([[state[f] for f in feature_names]])
    x_scaled = artifacts["scaler"].transform(x)
    x_proj = artifacts["pca"].transform(x_scaled)
    x_recon = artifacts["pca"].inverse_transform(x_proj)
    score = float(np.sum((x_scaled - x_recon) ** 2))
    threshold = artifacts["meta"]["threshold"]
    return score, threshold, score > threshold


def render_panel(col, title: str, slider_label: str, slider_key: str,
                  artifact_name: str, stage_thresholds: list):
    """stage_thresholds: [(하한, 라벨), ...] 내림차순 정렬, 값이 하한 이상이면 해당 라벨."""
    with col:
        st.subheader(title)
        value = st.slider(slider_label, 0.05, 1.00, 1.00, 0.01, key=slider_key)

        state = compute_state(value)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("T3 (연소실 출구)", f"{state['T3_K']:.0f} K")
        m2.metric("EGT", f"{state['EGT_K']:.0f} K")
        m3.metric("W_net", f"{state['W_net_kW']:.0f} kW")
        m4.metric("SFC", f"{state['SFC']:.2f} kg/kWh")

        artifacts = load_artifacts(artifact_name)
        if artifacts is None:
            st.warning(f"학습된 PCA/scaler 없음 — 먼저 `python 12_export_pca_artifacts.py` 실행 필요")
            status = None
        else:
            score, threshold, is_fault = anomaly_score(state, artifacts)
            pct = min(100.0, score / threshold * 100.0) if threshold > 0 else 0.0
            st.progress(min(1.0, pct / 100.0), text=f"이상탐지 점수 {score:.2f} / 임계값 {threshold:.2f}")

            stage_label = "정상"
            for lo, label in stage_thresholds:
                if value >= lo:
                    stage_label = label
                    break

            if not is_fault:
                st.success("정상 운전")
                status = "normal"
            else:
                st.error(f"이상 감지 — 추정 단계: {stage_label}")
                status = stage_label

        return value, state, status


col1, col2 = st.columns(2)

etab_stages = [(0.80, "정상"), (0.65, "onset"), (0.35, "partial"), (0.05, "full")]
fuel_stages = [(1.00, "정상"), (0.70, "moderate"), (0.50, "severe"), (0.0, "severe 이하(미검증 구간)")]

val1, state1, status1 = render_panel(
    col1, "시나리오1 — 실화 (Flameout)", "연소효율 η_b", "etab",
    "scenario1", etab_stages,
)
val2, state2, status2 = render_panel(
    col2, "시나리오2 — 연료계통 고장 (Fuel Fault)", "faultFactor_fuel", "fuelfactor",
    "scenario2", fuel_stages,
)

st.divider()
st.subheader("고장 원인 추정 (참고용)")
st.warning(CAUSE_DISCLAIMER)

cause_col1, cause_col2 = st.columns(2)
with cause_col1:
    st.write(f"시나리오1 판정: **{status1 or '평가 불가'}**")
with cause_col2:
    st.write(f"시나리오2 판정: **{status2 or '평가 불가'}**")

with st.expander("두 패널의 원본 물리량 비교 (디버깅용)"):
    st.dataframe(pd.DataFrame([state1, state2], index=["시나리오1", "시나리오2"]).T)
