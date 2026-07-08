"""
13_gui_dashboard.py
TPE331-10 실화(시나리오1)/연료계통고장(시나리오2) 나란히 비교 GUI (Streamlit)

구성(2026-07-08 확인 완료):
  - 좌: 시나리오1(실화, η_b 슬라이더) / 우: 시나리오2(연료계통고장, faultFactor_fuel 슬라이더)
  - 각 패널: 실시간 엔진 파라미터(T1~T4, P1~P4, EGT, W_net, SFC 근사) + 참조그래프 색상구간
    기반 상태판(2026-07-08 5차 수정 — PCA 이상탐지 점수는 스케일러 버그로 잠정 제거,
    classify_zone() 참조)
  - 하단: 고장 원인 추정 패널 — 포함하되 한계 명시(아래 CAUSE_DISCLAIMER 참조)

물리 계산은 real_engine_model_utils.py를 그대로 import해서 쓴다. 즉 향후
연소기/터빈 모델링이 바뀌어도 이 파일은 수정할 필요 없이 real_engine_model_utils.py
+ 12_export_pca_artifacts.py 재실행만으로 반영된다("파이썬 코드만 수정하면
사용할 수 있도록" 요청사항).

[2026-07-08 수정] combustor()가 Issue #9에서 eta_b/faultFactor_fuel 독립 인자 +
fa_demand_out/wf_out 출력을 갖도록 바뀌었는데(real_engine_model_utils.py), 이 파일은
방안B 시절 4-인자 호출(far_correction_factor 하나만 받아 4개 반환값만 unpack)에
멈춰 있어 실행 시 ValueError로 크래시하는 상태였다. compute_state()를 eta_b/
faultFactor_fuel 독립 인자로 수정하고, 시나리오1 패널은 eta_b만, 시나리오2 패널은
faultFactor_fuel만 움직이도록 분리했다(07/10과 동일 구조). 아울러 code/README.md가
지적한 "원인 추정 패널 문구 갱신 필요"(CAUSE_DISCLAIMER 참조)도 함께 반영 — Issue #9
이후로는 FAR_demand−FAR_actual 격차가 실제 원인 구분 신호이므로, 이 값을 하단 패널에
직접 표시하고 그 값에 근거해 판정하도록 바꿨다(06_vhdl_comparison.py 시나리오 D,
3-class 83.3%→100% 근거).

사전 준비:
  pip install streamlit joblib scikit-learn pandas numpy matplotlib streamlit-autorefresh
  python 12_export_pca_artifacts.py   (04_학습산출물/scenario{1,2}_*.joblib 생성)
  streamlit run 13_gui_dashboard.py

[2026-07-08 추가 수정]
  1) matplotlib 한글 폰트 깨짐(글자가 네모/물음표로 나오는 문제) 수정 — 기본 폰트에
     한글 글리프가 없어서였음. Windows 기본 내장 폰트인 Malgun Gothic을 우선 사용하도록
     rcParams 설정(_set_korean_font 참조).
  2) "실제 가동 중인 엔진에서 데이터를 계속 읽어온다"는 가정의 실시간 라이브 표시 추가 —
     실제 센서/Twin Builder 연동은 없으므로 07/10과 동일한 0.3% 가우시안 노이즈(AR(1)
     평활)를 현재 스로틀 설정값 위에 매 틱(streamlit-autorefresh)마다 얹어서
     st.session_state에 이력을 쌓는다. 처음엔 오실로스코프 스타일 matplotlib
     스크롤 차트로 그렸으나, "매 틱 이미지를 통째로 갈아끼우는" 구조상 갱신 주기를
     아무리 당겨도 뚝딱거림이 근본적으로 안 없어져서 st.metric(값+증감 화살표)+
     롤링 통계 텍스트로 교체했다(render_panel 참조). ⚠ 실측 데이터가 아니라는 점은
     화면 캡션에 항상 명시한다.

[2026-07-08 3차 수정] 시나리오1(η_b) 슬라이더를 [0.05, 0.80] → [0.05, 1.00]
연속 구간으로 확장했다. 기존엔 JSSG-2007A가 onset(0.65~0.80)/partial(0.35~0.65,
보간)/full(0.05~0.35)만 명문으로 정의하고 0.80~1.00 사이는 언급이 없다는 이유로
정상(1.0)을 슬라이더 밖 "별도 검증점"으로 떼어놨었다. 그런데 사용자 질의로
리서치해보니, 이미 근거문헌으로 쓰고 있는 Gas Path Analysis(GPA, Saravanamuttoo
계열)와 NASA C-MAPSS 열화 시뮬레이션 둘 다 컴포넌트 효율을 이산 단계가 아니라
기준값 대비 연속적인 건강지표(health index)로 다루는 게 표준 관례임을 확인했다
(Issue #13 코멘트에 근거자료 정리). 이 관례를 따라 eta_b를 처음부터 끝까지
연속 슬라이더로 바꾸되, JSSG가 명문으로 정의하는 3구간은 참조 그래프에 음영
밴드로 계속 구분 표시해서 "어디까지가 JSSG 원문 근거고 어디부터가 GPA 관례로
확장한 부분인지"를 감추지 않는다(sweep_curve/render_sweep_figure_png 참조).
"""

import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

from real_engine_model_utils import inlet, compressor, combustor, turbine, COMB_REF0, MFLOW

HERE = Path(__file__).parent
ARTIFACT_DIR = HERE.parent / "04_학습산출물"

LIVE_NOISE_LEVEL = 0.003          # 07/10_fault_generator.py와 동일 관례(순수 고장효과 분리용 0.3%)
LIVE_AR_COEF = 0.95                # AR(1) 평활 계수 — 클수록 부드럽게 이어지는 값처럼 보임
LIVE_SUBSAMPLES_PER_TICK = 7        # 한 번의 재실행(틱)마다 몇 개 샘플을 한꺼번에 만들지
# 서브샘플 간 가상 시간 간격(초). 7개 × 0.05 = 0.35초로, 실제 autorefresh 간격(0.35초,
# 아래 st_autorefresh interval=350 참조)과 맞춰서 롤링 통계 창에 시간축 공백이 안 생기게 함.
LIVE_DT = 0.05
LIVE_WINDOW_SEC = 6.0                # 롤링 통계(평균/표준편차/peak-to-peak)에 사용할 시간 창(초)
LIVE_RAMP_RATE = 0.15                # 슬라이더 값이 바뀔 때 기준선이 한 서브샘플당 이 비율만큼만 새 값 쪽으로 이동(급격한 단절 완화)
# ⚠ 2026-07-08: 매 틱마다 matplotlib 오실로스코프 이미지를 통째로 다시 그리는
# 구조라 갱신 주기를 아무리 당겨도(0.4→1→0.5→0.35초로 계속 조정해봄) "뚝딱거림"이
# 근본적으로 안 없어진다는 피드백을 받아, 라이브 차트를 st.metric(증감 화살표)+
# 롤링 통계 텍스트로 교체했다(render_panel 내부 참조). DOM 텍스트는 이미지 스왑이
# 아니라 브라우저가 매끄럽게 갱신하므로 이 문제 자체가 사라진다. 아래 노이즈
# 생성 로직(AR(1) 평활)은 값 자체는 그대로 두고 표시 방식만 바꾼 것.

# [2026-07-08 5차 수정] 참조 그래프(render_sweep_figure_png)와 상태 판정(classify_zone)이
# 서로 다른 숫자를 쓰면 "그래프는 초록인데 판정은 빨강" 같은 불일치가 생기므로, 구간
# 경계값을 모듈 상수 하나로 통일해서 두 곳에서 그대로 재사용한다.
ETAB_JSSG_BANDS = (   # (하한, 상한, 라벨, 그래프 음영색) — JSSG-2007A 명문 정의 구간
    (0.65, 0.80, "onset", "#ffe9a8"),
    (0.35, 0.65, "partial", "#ffd08a"),
    (0.05, 0.35, "full", "#ffb3a8"),
)
FUEL_REF_ZONES = (    # (하한, 상한, 라벨, 그래프 음영색) — 공식 규격 아님, TB 실측점 인접 참고
    (0.85, 1.00, "정상 인접", "#cdeccd"),
    (0.60, 0.85, "moderate 인접", "#ffd08a"),
    (0.30, 0.60, "severe 인접", "#ffb3a8"),
)


def _set_korean_font():
    """matplotlib 기본 폰트엔 한글 글리프가 없어 글자가 깨져 보이던 문제 수정.
    Windows 기본 내장 폰트(Malgun Gothic)를 우선 사용, 없으면 다른 한글 폰트로 대체."""
    candidates = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    else:
        st.warning("⚠ 한글 지원 폰트를 찾지 못해 그래프 한글이 깨질 수 있습니다 "
                    "(예: 나눔고딕 설치 후 재실행 권장).")
    plt.rcParams["axes.unicode_minus"] = False   # 한글 폰트에서 마이너스 기호 깨짐 방지


_set_korean_font()

CAUSE_DISCLAIMER = (
    "ℹ 2026-07-08 Issue #9 반영: Combustor entity에 독립 eta_b 포트가 추가되어 "
    "η_b(시나리오1)와 faultFactor_fuel(시나리오2)이 더 이상 같은 입력단을 공유하지 "
    "않습니다. 아래 'FAR gap(=FAR_demand−FAR_actual)'이 실제 원인 구분 신호입니다 — "
    "연료계통 고장(시나리오2)에서는 이 값이 뚜렷하게 커지고, 연소효율 저하(시나리오1)에서는 "
    "0에 가깝게 유지됩니다(06_vhdl_comparison.py 시나리오 D, FAR gap+Wf 신호 추가로 "
    "3-class 진단 정확도 83.3%→100%로 검증됨). 다만 이 패널은 정상상태(steady-state) "
    "값만 사용하는 단순 임계값 판정이며, 과도응답(램프 시간 등 변화율) 기반 동적 데이터나 "
    "실측 검증까지 거친 것은 아니므로 참고용으로만 사용하세요."
)

st.set_page_config(page_title="TPE331-10 실시간 고장 시뮬레이터", layout="wide")
st.title("TPE331-10 실시간 고장 탐지 데모")
st.caption("real_engine_model_utils.py 공통 엔진 물리모델 기반 — 독립 eta_b 포트 (Issue #9, 2026-07-08)")


def compute_state(eta_b: float = 1.0, fault_factor_fuel: float = 1.0) -> dict:
    """real_engine_model_utils.py 함수를 그대로 호출 — 07/10과 동일 계산 경로.
    Issue #9부터 eta_b/faultFactor_fuel이 독립 인자이므로, 시나리오1 호출은
    eta_b만 바꾸고 fault_factor_fuel=1.0 고정(07/10의 run_case()와 대칭)."""
    T1, P1 = inlet(altitude=0.0, mach=0.0)
    T2, P2, comp_power = compressor(T1, P1)
    T3, P3, far_demand, far_actual, wf = combustor(
        T2, P2, COMB_REF0, faultFactor_fuel=fault_factor_fuel, eta_b=eta_b
    )
    temp_diff_comp = T1 - T2
    T4, P4, turb_power = turbine(T3, P3, temp_diff_comp, far_actual)

    comp_power_kW = comp_power / 1000.0
    turb_power_kW = turb_power / 1000.0
    w_net_kW = turb_power_kW - comp_power_kW
    tit_error = COMB_REF0 - T3
    sfc = (wf * 3600.0) / max(w_net_kW, 1e-6)   # kg/kWh 근사
    far_gap = far_demand - far_actual

    return dict(
        T1_K=T1, P1_Pa=P1, T2_K=T2, P2_Pa=P2, T3_K=T3, P3_Pa=P3, T4_K=T4, P4_Pa=P4,
        compressor_power_kW=comp_power_kW, turbine_power_kW=turb_power_kW,
        W_net_kW=w_net_kW, FAR_demand=far_demand, FAR_actual=far_actual,
        Wf_kg_s=wf, FAR_gap=far_gap,
        TIT_error_K=tit_error, EGT_K=T4, SFC=sfc,
    )


@st.cache_data
def sweep_curve(mode: str, n: int = 60) -> pd.DataFrame:
    """x(=eta_b 또는 faultFactor_fuel)에 따른 출력값 변화를 선그래프용 DataFrame으로
    만든다.

    [2026-07-08 재검토] eta_b(시나리오1)를 예전엔 "정상(1.0)"과 "JSSG 실화구간
    (0.05~0.80)"을 물리적으로 안 이어지는 별개 점/구간(seg 컬럼)으로 나눠서
    그렸다 — JSSG-2007A가 onset~full 3단계만 명문으로 정의하고 0.80~1.00 사이는
    언급이 없다는 이유였다. 하지만 이미 근거문헌인 Gas Path Analysis(GPA,
    Saravanamuttoo 계열)와 NASA C-MAPSS 열화 시뮬레이션 모두 컴포넌트 효율을
    이산 단계가 아니라 기준값 대비 연속 건강지표(health index)로 다루는 게 표준
    관례임을 확인하고(Issue #13 코멘트 근거자료 참조), 이 관례를 따라 eta_b를
    [0.05, 1.00] 전체에서 하나의 연속 곡선으로 스윕하도록 바꿨다(더 이상 seg로
    끊지 않음). JSSG가 명문으로 정의하는 onset(0.65~0.80)/partial(0.35~0.65,
    보간)/full(0.05~0.35) 3구간은 render_sweep_figure_png에서 음영 밴드로 별도
    표시해 "JSSG 명문 정의 구간"과 "GPA 관례로 확장한 연속 구간(0.80~1.00)"을
    시각적으로 구분한다 — 근거 출처가 다르다는 걸 숨기지 않기 위함.
    - faultFactor_fuel(시나리오2): 기존과 동일 — [0.30, 1.00] 전 구간이 모델상
      연속으로 유효하고, Twin Builder 실측 교차검증점(1.0/0.7/0.5)만
      render_sweep_figure_png에서 별도 마커로 표시한다."""
    rows = []
    if mode == "eta_b":
        for x in np.linspace(0.05, 1.00, n):   # GPA/C-MAPSS 관례: 연속 건강지표
            s = compute_state(eta_b=x, fault_factor_fuel=1.0)
            rows.append(dict(x=x, **{k: s[k] for k in ("T3_K", "EGT_K", "W_net_kW", "FAR_gap")}))
    else:
        for x in np.linspace(0.30, 1.00, n):   # 모델상 연속 — 실측점은 render_panel에서 별도 표시
            s = compute_state(eta_b=1.0, fault_factor_fuel=x)
            rows.append(dict(x=x, **{k: s[k] for k in ("T3_K", "EGT_K", "W_net_kW", "FAR_gap")}))
    return pd.DataFrame(rows)


@st.cache_data
def render_sweep_figure_png(mode: str, value: float, y_col: str, y_label: str, slider_label: str) -> bytes:
    """정적 참조 그래프(스윕 곡선 + 현재 선택값 마커)를 PNG 바이트로 렌더링해서
    st.cache_data로 캐시한다. autorefresh가 0.4~1초마다 전체 스크립트를 다시 실행할
    때, 슬라이더 값이 그대로면(대부분의 틱이 이 경우) matplotlib를 다시 호출하지
    않고 캐시된 이미지를 그대로 재사용 — "화면이 하얘짐/그래프가 안 움직임" 원인이던
    과부하(패널 2개 × 그림 2개를 매 틱 통째로 다시 그리던 것)를 줄이기 위한 조치.
    실시간 오실로스코프 차트는 값 자체가 매 틱 바뀌어야 하므로 이 캐시 대상이 아니다.

    [2026-07-08] eta_b는 이제 [0.05, 1.00] 전 구간을 하나의 연속선으로 그린다
    (GPA/NASA C-MAPSS 연속 건강지표 관례, sweep_curve 참조). JSSG-2007A가
    명문으로 정의하는 onset(0.65~0.80)/partial(0.35~0.65)/full(0.05~0.35)
    구간은 배경 음영(axvspan)으로 표시해 "이 부분만 JSSG 원문 근거가 있다"는
    걸 계속 드러내고, 정상(η_b=1.0)은 더 이상 끊어서 그리지 않고 연속선 위의
    강조 마커로만 표시한다.

    [2026-07-08 4차 수정] ① 그래프 크기를 (4.2,2.8)→(6.4,4.2)로 키워달라는
    요청 반영(제목/범례 폰트도 같이 키움 — 안 그러면 확대된 그림 대비 글자가
    너무 작아 보임). ② 시나리오1(eta_b)에만 있던 "단계별 색상 구간"을
    시나리오2(faultFactor_fuel)에도 적용해달라는 요청 반영. 다만 faultFactor_fuel은
    JSSG처럼 공식적으로 정의된 "구간"이 없고 Twin Builder 실측 교차검증점
    (1.0/0.7/0.5, Issue #3) 3개 점뿐이라, 경계를 지어내지 않고 "가장 가까운
    실측점" 기준(중간값 0.85/0.60)으로만 옅게 색을 나눴다 — JSSG 음영과
    혼동되지 않도록 범례/캡션에 "참고용, 공식 구간 아님"을 명시한다."""
    curve = sweep_curve(mode)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    if mode == "eta_b":
        ax.plot(curve["x"], curve[y_col], linestyle="-", linewidth=1.8, color="tab:blue")
        # JSSG-2007A 명문 정의 구간(음영) — 그 밖(0.80~1.00)은 GPA 관례로 확장한
        # 부분이라 일부러 음영을 넣지 않아 "여기부터는 JSSG 원문 근거가 없다"는
        # 걸 시각적으로 구분한다. classify_zone()과 같은 상수(ETAB_JSSG_BANDS)를
        # 써서 그래프 색과 아래 상태 판정이 항상 일치하도록 한다.
        for lo_b, hi_b, band_label, color in ETAB_JSSG_BANDS:
            ax.axvspan(lo_b, hi_b, color=color, alpha=0.5, zorder=0,
                       label=f"JSSG {band_label}")
        s_normal = compute_state(eta_b=1.0, fault_factor_fuel=1.0)
        ax.scatter([1.0], [s_normal[y_col]], color="black", marker="o", s=70,
                   zorder=6, label="정상(η_b=1.0)")
    else:
        ax.plot(curve["x"], curve[y_col], linestyle="-", linewidth=1.8, color="tab:blue")
        # 공식 규격 구간이 아니라 "실측점 3개 중 가장 가까운 점" 기준 참고용
        # 색 구분 — 경계(0.85/0.60)는 세 실측점의 중간값일 뿐 근거문헌 수치가 아님.
        # classify_zone()과 같은 상수(FUEL_REF_ZONES)를 써서 그래프 색과 아래 상태
        # 판정이 항상 일치하도록 한다.
        for lo_z, hi_z, zone_label, color in FUEL_REF_ZONES:
            ax.axvspan(lo_z, hi_z, color=color, alpha=0.4, zorder=0, label=zone_label)
        for i, vx in enumerate((1.0, 0.7, 0.5)):
            vs = compute_state(eta_b=1.0, fault_factor_fuel=vx)
            ax.scatter([vx], [vs[y_col]], color="black", marker="x", s=70, zorder=6,
                       label="TB 실측 교차검증점 (Issue #3)" if i == 0 else None)
    state_at_value = compute_state(eta_b=value, fault_factor_fuel=1.0) if mode == "eta_b" \
        else compute_state(eta_b=1.0, fault_factor_fuel=value)
    ax.axvline(value, color="gray", linestyle="--", linewidth=1)
    ax.scatter([value], [state_at_value[y_col]], color="tab:red", s=70, zorder=7, label="현재 선택값")
    ax.set_xlabel(slider_label, fontsize=11)
    ax.set_ylabel(y_label, fontsize=11)
    ax.tick_params(labelsize=9)
    title_suffix = "(JSSG 음영 + GPA 연속 건강지표)" if mode == "eta_b" else "(TB 실측점 인접 참고 구간)"
    ax.set_title(f"{y_label} vs {slider_label} {title_suffix}", fontsize=12)
    ax.legend(fontsize=9, loc="best")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return buf.getvalue()


def classify_zone(mode: str, value: float) -> tuple:
    """현재 슬라이더 값이 참조 그래프의 어느 색상 구간에 속하는지 판정해서
    (설명 텍스트, 레벨) 튜플을 반환한다. 레벨은 'normal'/'warning'/'danger' 중
    하나이며 각각 st.success/st.warning/st.error로 표시된다.

    [2026-07-08 5차 수정] 기존엔 PCA 재구성오차(anomaly_score)로 정상/이상을
    판정했는데, StandardScaler가 학습 데이터에서 분산이 0에 가까운 피처
    (altitude/mach를 항상 고정값으로 生성해 T2_K/P2_Pa 등이 거의 상수였던 것)를
    나누면서 점수가 10^20 이상으로 발산하는 버그가 발견됐다(2026-07-08 사용자
    리포트 — "이상탐지 점수 113148...같은 값"). 근본 수정(스케일러 재학습)은
    별도 작업이 필요해서, 우선 점수/진행바 표시는 제거하고, 참조 그래프
    배경색(ETAB_JSSG_BANDS/FUEL_REF_ZONES — render_sweep_figure_png와 동일 상수)
    과 항상 일치하는 구간 기반 상태 표시로 교체했다. "그래프는 초록인데 판정은
    빨강" 같은 불일치가 나올 수 없도록 색상 소스를 하나로 통일하는 게 목적."""
    if mode == "eta_b":
        if value >= 0.80:
            return f"η_b={value:.2f} — 정상 범위(0.80 이상)", "normal"
        for lo, hi, band_label, _ in ETAB_JSSG_BANDS:
            if lo <= value < hi:
                level = "danger" if band_label == "full" else "warning"
                return f"η_b={value:.2f} — {band_label} 구간", level
        return f"η_b={value:.2f}", "warning"
    else:
        for lo, hi, zone_label, _ in FUEL_REF_ZONES:
            if lo <= value <= hi:
                if zone_label.startswith("정상"):
                    level = "normal"
                elif zone_label.startswith("severe"):
                    level = "danger"
                else:
                    level = "warning"
                return f"faultFactor_fuel={value:.2f} — {zone_label}", level
        return f"faultFactor_fuel={value:.2f}", "warning"


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
                  artifact_name: str, value_range: tuple, mode: str,
                  y_col: str = "T3_K", y_label: str = "T3 (K)",
                  note: str | None = None, default: float | None = None):
    """value_range: (하한, 상한) — 슬라이더가 움직일 수 있는 전체 구간.

    [2026-07-08 재검토] eta_b(시나리오1) 슬라이더 범위를 기존 [0.05, 0.80]에서
    [0.05, 1.00]으로 넓혔다. 기존엔 JSSG-2007A가 onset(0.65~0.80)/partial
    (0.35~0.65, 보간)/full(0.05~0.35)만 명문으로 정의하고 0.80~1.00 사이는
    언급이 없다는 이유로, 정상(1.0)을 슬라이더 밖 "별도 검증점"으로 떼어놨었다.
    하지만 사용자 질의로 리서치한 결과 Gas Path Analysis(GPA, Saravanamuttoo —
    이미 근거문헌으로 인용 중)와 NASA C-MAPSS 열화 시뮬레이션 둘 다 컴포넌트
    효율을 애초에 이산 단계가 아니라 기준값 대비 연속 건강지표(health index)로
    다루는 게 표준 관례임을 확인했고(Issue #13 코멘트 근거자료 참조), 이 관례를
    따라 eta_b 전체를 연속 슬라이더로 바꿨다. JSSG가 명문으로 정의하는 3구간은
    여전히 참조 그래프에 음영 밴드로 구분 표시해 "이 부분만 JSSG 원문 근거가
    있다"는 걸 감추지 않는다(render_sweep_figure_png 참조) — 출처가 다른 두
    근거(JSSG 명문 vs GPA 관례로 확장한 부분)를 섞어서 "전부 똑같이 검증됨"처럼
    보이지 않게 하는 게 목적.
    - faultFactor_fuel(시나리오2): 기존과 동일 — [0.30, 1.00] 전 구간이 모델상
      연속으로 유효하고 1.0(정상)도 자연스럽게 포함된다. note로 "실측 교차검증은
      그중 3점뿐"이라는 caveat만 남긴다.
    mode: 'eta_b'(시나리오1, faultFactor_fuel=1.0 고정) 또는
          'fault_factor'(시나리오2, eta_b=1.0 고정) — Issue #9 독립 인자 반영."""
    with col:
        st.subheader(title)
        lo, hi = value_range
        default_value = default if default is not None else round((lo + hi) / 2, 3)
        value = st.slider(f"{slider_label} (범위 {lo:.2f}~{hi:.2f})",
                           lo, hi, default_value, 0.01, key=f"{slider_key}_value")
        if note:
            st.caption(note)
        if mode == "eta_b":
            st.caption(
                "ℹ 참조 그래프의 배경 음영(onset/partial/full)은 JSSG-2007A가 "
                "명문으로 정의한 구간(0.05~0.80)입니다. 그 밖(0.80~1.00)은 "
                "Gas Path Analysis 관례(Saravanamuttoo 등 — 효율을 연속 건강지표로 "
                "취급)를 따라 연속으로 확장한 부분이며 JSSG 원문 근거는 아닙니다."
            )
        else:
            st.caption(
                "ℹ 참조 그래프의 배경 색상 구간은 공식 규격(JSSG 같은) 구간이 "
                "아닙니다. Twin Builder 실측 교차검증점(1.0/0.7/0.5, Issue #3) "
                "3개 중 가장 가까운 점을 기준으로 나눈 참고용 구분이며, 경계값"
                "(0.85/0.60)은 세 실측점의 중간값일 뿐 근거문헌 수치가 아닙니다."
            )
        if mode == "eta_b":
            state = compute_state(eta_b=value, fault_factor_fuel=1.0)
        else:
            state = compute_state(eta_b=1.0, fault_factor_fuel=value)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("T3 (연소실 출구)", f"{state['T3_K']:.0f} K")
        m2.metric("EGT", f"{state['EGT_K']:.0f} K")
        m3.metric("W_net", f"{state['W_net_kW']:.0f} kW")
        m4.metric("SFC", f"{state['SFC']:.2f} kg/kWh")

        # 정적 참조 그래프는 캐시된 PNG로 — 슬라이더 값이 그대로인 틱(대부분)에는
        # matplotlib를 다시 호출하지 않는다 (과부하로 인한 백지 화면 방지).
        png_bytes = render_sweep_figure_png(mode, value, y_col, y_label, slider_label)
        st.image(png_bytes)

        # ── 실시간 라이브 상태 (숫자 기반, 2026-07-08 그래프→숫자로 교체) ──────
        # 실제 엔진/Twin Builder 연동은 없음 — 현재 스로틀 설정값 주위를 AR(1)
        # 평활 노이즈(07/10과 동일 0.3% 수준이 정상상태 표준편차가 되도록 보정)로
        # 흔들리게 하는 노이즈 생성 로직은 이전과 동일하게 유지한다. 다만
        # matplotlib 오실로스코프 차트는 "매 틱 정지 이미지를 통째로 갈아끼우는"
        # 구조라 갱신 주기를 아무리 당겨도 뚝딱거림이 근본적으로 안 없어진다는
        # 피드백을 받아, st.metric(값+증감 화살표) + 롤링 통계 텍스트로 교체했다.
        # st.metric은 이미지가 아니라 DOM 텍스트라 브라우저가 매끄럽게 갱신한다.
        hist_key = f"__live_hist_{slider_key}"
        noise_key = f"__live_noise_{slider_key}"
        t0_key = f"__live_t0_{slider_key}"
        base_key = f"__live_base_{slider_key}"
        prev_key = f"__live_prev_{slider_key}"
        # ⚠ 세 키를 하나의 if로 묶어서 초기화하면, autorefresh가 빠르게 반복될 때
        # 스크립트 실행이 중간에 취소(재실행 요청으로 강제 중단)되는 경우 hist_key만
        # 설정되고 t0_key는 설정되지 못한 채로 넘어가는 경우가 생겨 다음 실행에서
        # "hist_key가 이미 있으니 초기화 건너뜀 → t0_key 없음"으로 KeyError가 났었다.
        # 각 키를 독립적으로 setdefault해서 어느 지점에서 중단되든 다음 실행에서
        # 누락된 키만 채우도록 고쳤다.
        st.session_state.setdefault(hist_key, [])
        st.session_state.setdefault(noise_key, 0.0)
        st.session_state.setdefault(t0_key, time.time())
        st.session_state.setdefault(base_key, state[y_col])   # 노이즈를 얹는 기준선(ramp로 서서히 이동)
        st.session_state.setdefault(prev_key, state[y_col])   # 직전 표시값(증감 화살표 계산용)

        now = time.time() - st.session_state[t0_key]
        rng = np.random.default_rng()
        sigma_step = LIVE_NOISE_LEVEL * float(np.sqrt(1.0 - LIVE_AR_COEF ** 2))
        for i in range(LIVE_SUBSAMPLES_PER_TICK):
            # 슬라이더를 바꾸면 state[y_col](목표값)이 즉시 바뀌지만, 기준선은
            # 그쪽으로 한 서브샘플당 LIVE_RAMP_RATE 비율만큼만 옮겨가게 해서
            # 표시값이 순간이동하듯 뚝 끊기지 않고 부드럽게 이어지도록 한다
            # (실제 과도응답 동특성을 재현한 건 아니고 시각적 완화용 램프임).
            st.session_state[base_key] += LIVE_RAMP_RATE * (state[y_col] - st.session_state[base_key])
            st.session_state[noise_key] = (
                LIVE_AR_COEF * st.session_state[noise_key] + rng.normal(0.0, sigma_step)
            )
            t_sample = now - (LIVE_SUBSAMPLES_PER_TICK - 1 - i) * LIVE_DT
            v_sample = st.session_state[base_key] * (1.0 + st.session_state[noise_key])
            st.session_state[hist_key].append((t_sample, v_sample))

        cutoff = now - LIVE_WINDOW_SEC
        st.session_state[hist_key] = [(t, v) for t, v in st.session_state[hist_key] if t >= cutoff]

        hist_v = [v for _, v in st.session_state[hist_key]]
        current_val = hist_v[-1] if hist_v else state[y_col]
        prev_val = st.session_state[prev_key]
        delta = current_val - prev_val
        st.session_state[prev_key] = current_val

        live_col1, live_col2 = st.columns([1, 1])
        with live_col1:
            st.metric(f"{y_label} (실시간, 시뮬레이션)", f"{current_val:,.1f}",
                      delta=f"{delta:+.2f}", delta_color="off")
        with live_col2:
            if len(hist_v) >= 2:
                arr = np.array(hist_v)
                st.caption(
                    f"최근 {LIVE_WINDOW_SEC:.0f}초 롤링 통계\n\n"
                    f"평균 {arr.mean():,.1f} · 표준편차 {arr.std():.3f} · "
                    f"최대편차(peak-to-peak) {(arr.max() - arr.min()):.2f}"
                )
            else:
                st.caption("데이터 수집 중…")
        st.caption("⚠ 실측 데이터가 아니라 시뮬레이션 노이즈입니다 (AR(1) 평활, 07/10 스크립트와 동일 0.3% 수준).")

        # [2026-07-08 5차 수정] PCA 이상탐지 점수/진행바 제거 — StandardScaler가
        # 분산 0에 가까운 피처를 나누며 점수가 10^20 이상으로 발산하는 버그가
        # 있어(사용자 리포트), 근본 수정 전까지는 표시하지 않는다. 대신 참조
        # 그래프와 동일한 색상 구간 기준(classify_zone)으로 상태를 판정해서
        # "그래프 색과 아래 상태가 항상 일치"하도록 바꿨다.
        zone_text, zone_level = classify_zone(mode, value)
        if zone_level == "normal":
            st.success(f"정상 — {zone_text}")
        elif zone_level == "warning":
            st.warning(f"주의 — {zone_text}")
        else:
            st.error(f"위험 — {zone_text}")
        status = zone_text

        return value, state, status


if HAS_AUTOREFRESH:
    # ⚠ 2026-07-08 변경 이력: 0.4초 간격 + 매 틱마다 패널 2개×그림 2개(정적+실시간)
    # 전부 다시 그리던 구조가 저사양 환경에서 렌더링 시간 > 갱신 간격이 돼
    # "취소→재시작" 루프에 빠져 화면이 하얗게 멈추는 원인이었다. 정적 그래프는
    # 캐시로 뺐고(render_sweep_figure_png), 라이브 차트는 아예 matplotlib 이미지
    # 대신 st.metric+텍스트로 바꿔서(render_panel 참조) "이미지 통째로 갈아끼우기"
    # 자체를 없앴다 — 그 덕에 갱신 주기를 0.35초까지 당겨도 부담이 거의 없다.
    st_autorefresh(interval=350, key="__live_refresh_tick")   # 0.35초마다 재실행 + 틱당 7개 서브샘플
else:
    st.button("🔄 다음 샘플 가져오기 (streamlit-autorefresh 설치 시 자동으로 계속 흘러갑니다: "
              "pip install streamlit-autorefresh)")

col1, col2 = st.columns(2)

# 2026-07-08: "정상/onset/partial/full" 식 단계 radio를 없애고, 슬라이더 자체를
# 하나의 연속 구간으로 단순화했다.
# eta_b: [2026-07-08 재검토] 기존엔 JSSG-2007A onset(0.65~0.80)+partial(0.35~0.65,
# 보간)+full(0.05~0.35)이 이어져 만드는 [0.05, 0.80]만 슬라이더로 노출하고, 정상(1.0)은
# 안 이어지는 별도 검증점으로 떼어놨었다. 이후 리서치에서 Gas Path Analysis(GPA,
# Saravanamuttoo)/NASA C-MAPSS가 효율을 이산 단계가 아니라 연속 건강지표로 다루는
# 관례임을 확인하고(Issue #13 코멘트 근거자료), [0.05, 1.00] 전체를 연속 슬라이더로
# 확장했다. JSSG 3구간은 render_sweep_figure_png에서 음영으로만 구분 표시한다.
ETAB_RANGE = (0.05, 1.00)
# faultFactor_fuel: 순수 배수 입력이라 물리적 gap이 없어 [0.30, 1.00] 전 구간이
# 연속으로 유효 — 1.0(정상)도 자연스럽게 그 안에 포함되므로 별도 취급 불필요.
FUEL_RANGE = (0.30, 1.00)
FUEL_NOTE = (
    "⚠ Twin Builder 실측 교차검증점은 1.00(정상)/0.70(moderate)/0.50(severe) 3개뿐입니다 "
    "(Issue #3). 그 외 값은 faultFactor_fuel×FAR_demand 계산상 유효하지만 "
    "Twin Builder 실측 대조는 안 된 모델 보간값입니다."
)

val1, state1, status1 = render_panel(
    col1, "시나리오1 — 실화 (Flameout)", "연소효율 η_b", "etab",
    "scenario1", ETAB_RANGE, mode="eta_b", default=1.00,
)
val2, state2, status2 = render_panel(
    col2, "시나리오2 — 연료계통 고장 (Fuel Fault)", "faultFactor_fuel", "fuelfactor",
    "scenario2", FUEL_RANGE, mode="fault_factor", note=FUEL_NOTE,
)

st.divider()
st.subheader("고장 원인 추정 (FAR gap 기반, Issue #9)")
st.info(CAUSE_DISCLAIMER)

FAR_GAP_EPS = 1e-4   # 정상 부동소수 오차 수준 — 이 이하면 "연료공급 정상"으로 판정

cause_col1, cause_col2 = st.columns(2)
with cause_col1:
    st.write(f"시나리오1 판정(슬라이더 기준): **{status1 or '평가 불가'}**")
    st.write(f"FAR gap = {state1['FAR_gap']:.6f} → "
             f"{'연료공급 정상 (원인=연소효율 저하 신호)' if abs(state1['FAR_gap']) < FAR_GAP_EPS else '연료공급 이상 신호 감지'}")
with cause_col2:
    st.write(f"시나리오2 판정(슬라이더 기준): **{status2 or '평가 불가'}**")
    st.write(f"FAR gap = {state2['FAR_gap']:.6f} → "
             f"{'연료공급 정상' if abs(state2['FAR_gap']) < FAR_GAP_EPS else '연료공급 이상 (원인=연료계통 고장 신호)'}")

with st.expander("두 패널의 원본 물리량 비교 (디버깅용)"):
    st.dataframe(pd.DataFrame([state1, state2], index=["시나리오1", "시나리오2"]).T)
