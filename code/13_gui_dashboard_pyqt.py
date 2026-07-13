"""
13_gui_dashboard_pyqt.py
TPE331-10 실화(시나리오1)/연료계통고장(시나리오2) 나란히 비교 GUI (PyQt6)

[2026-07-13] github.com/chestnutbread/Red-horse/code/13_gui_dashboard.py
(main 브랜치 최신본, 534줄)를 그대로 PyQt6로 옮겼다. 지난번에 만든 초판은
사용자가 업로드한 파일 기준이었는데, 그 파일은 방안B 시절(far_correction_factor
단일 인자) 버전이라 실제 GitHub main과 어긋나 있었다 — GitHub 이슈/코드가
기준이라는 원칙에 따라 이번엔 raw.githubusercontent.com에서 최신 코드를 직접
받아 대조했다. 주요 차이(반영 완료):
  - combustor()가 Issue #9로 eta_b/faultFactor_fuel 독립 인자 + wf(연료유량)
    반환을 갖도록 바뀜 (real_engine_model_utils.py도 함께 최신화 필요 — 아래 참고)
  - ETA_M 0.98 → 0.9 (Issue #9, 팀원이 "0.98은 표기 오류"라고 정정)
  - 슬라이더가 정상/onset/partial/full 단계 구분 없이 연속 구간
    (η_b: [0.05, 1.00], faultFactor_fuel: [0.30, 1.00])
  - PCA 이상탐지 점수는 StandardScaler 발산 버그로 제거됨 — 대신 참조 그래프와
    동일한 색상 구간 기준(classify_zone)으로 정상/주의/위험 판정
  - 하단 원인 추정 패널이 CAUSE_DISCLAIMER + FAR gap(=FAR_demand−FAR_actual)
    기반으로 바뀜 (Issue #9 근거)

Issue #12(GUI 실행 가이드) 반영 사항 — Streamlit 버전에서 있었던 문제들이
PyQt6 구조에서는 애초에 발생하지 않거나 다른 방식으로 해결됨:
  - "한글 깨짐": matplotlib 참조 그래프에는 동일하게 _set_korean_font() 적용.
    PyQt 위젯 텍스트(QLabel 등)는 OS 시스템 폰트를 그대로 쓰므로 별도 조치 불필요.
  - "session_state KeyError로 크래시": PyQt는 세션 상태 딕셔너리 대신 클래스
    인스턴스 속성(self.hist, self.base 등)을 쓰므로 이 문제 자체가 구조적으로 없음.
  - "화면이 하얗게 멈춤(과부하)": 원인이었던 "매 틱마다 그래프 4개 통째로 재렌더링"을
    그대로 피함 — 참조 그래프(matplotlib)는 슬라이더 값이 바뀔 때만 다시 그리고,
    실시간 값은 QTimer(350ms)로 QLabel 텍스트만 갱신한다(이미지 재생성 없음).
  - "슬라이더가 마우스를 놓아야 반영됨": Streamlit 고유의 제약이었음. PyQt의
    QSlider.valueChanged는 드래그 중에도 실시간으로 발생하므로 이 제약이 없다.

⚠ real_engine_model_utils.py도 GitHub 최신본(Issue #9 반영판, combustor 시그니처
변경 + ETA_M=0.9)으로 함께 교체해야 이 파일이 정상 동작한다. 이 대화에서 이전에
업로드받은 real_engine_model_utils.py는 Issue #9 이전 버전이라 그대로 두면
TypeError(combustor() 인자 불일치)가 난다.

사전 준비:
  pip install PyQt6 matplotlib joblib scikit-learn pandas numpy --break-system-packages
  (real_engine_model_utils.py를 GitHub main 최신본으로 교체)
  python 13_gui_dashboard_pyqt.py
"""

from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QGroupBox, QFrame, QTableWidget, QTableWidgetItem,
    QSizePolicy,
)

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from real_engine_model_utils import inlet, compressor, combustor, turbine, COMB_REF0

HERE = Path(__file__).parent
ARTIFACT_DIR = HERE.parent / "04_학습산출물"   # (현재 미사용 — PCA 게이지는 GitHub에서 제거됨, 참고용으로만 유지)

LIVE_NOISE_LEVEL = 0.003
LIVE_AR_COEF = 0.95
LIVE_SUBSAMPLES_PER_TICK = 7
LIVE_DT = 0.05
LIVE_WINDOW_SEC = 6.0
LIVE_RAMP_RATE = 0.15
TIMER_INTERVAL_MS = 350   # streamlit-autorefresh와 동일 주기(0.35초)

ETAB_JSSG_BANDS = (
    (0.65, 0.80, "onset", "#ffe9a8"),
    (0.35, 0.65, "partial", "#ffd08a"),
    (0.05, 0.35, "full", "#ffb3a8"),
)
FUEL_REF_ZONES = (
    (0.85, 1.00, "정상 인접", "#cdeccd"),
    (0.60, 0.85, "moderate 인접", "#ffd08a"),
    (0.30, 0.60, "severe 인접", "#ffb3a8"),
)

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
FAR_GAP_EPS = 1e-4

ETAB_RANGE = (0.05, 1.00)
FUEL_RANGE = (0.30, 1.00)
FUEL_NOTE = (
    "⚠ Twin Builder 실측 교차검증점은 1.00(정상)/0.70(moderate)/0.50(severe) 3개뿐입니다 "
    "(Issue #3). 그 외 값은 faultFactor_fuel×FAR_demand 계산상 유효하지만 "
    "Twin Builder 실측 대조는 안 된 모델 보간값입니다."
)


def _set_korean_font():
    candidates = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


_set_korean_font()


def compute_state(eta_b: float = 1.0, fault_factor_fuel: float = 1.0) -> dict:
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
    sfc = (wf * 3600.0) / max(w_net_kW, 1e-6)
    far_gap = far_demand - far_actual

    return dict(
        T1_K=T1, P1_Pa=P1, T2_K=T2, P2_Pa=P2, T3_K=T3, P3_Pa=P3, T4_K=T4, P4_Pa=P4,
        compressor_power_kW=comp_power_kW, turbine_power_kW=turb_power_kW,
        W_net_kW=w_net_kW, FAR_demand=far_demand, FAR_actual=far_actual,
        Wf_kg_s=wf, FAR_gap=far_gap,
        TIT_error_K=tit_error, EGT_K=T4, SFC=sfc,
    )


@lru_cache(maxsize=None)
def sweep_curve(mode: str, n: int = 60) -> pd.DataFrame:
    rows = []
    if mode == "eta_b":
        for x in np.linspace(0.05, 1.00, n):
            s = compute_state(eta_b=x, fault_factor_fuel=1.0)
            rows.append(dict(x=x, **{k: s[k] for k in ("T3_K", "EGT_K", "W_net_kW", "FAR_gap")}))
    else:
        for x in np.linspace(0.30, 1.00, n):
            s = compute_state(eta_b=1.0, fault_factor_fuel=x)
            rows.append(dict(x=x, **{k: s[k] for k in ("T3_K", "EGT_K", "W_net_kW", "FAR_gap")}))
    return pd.DataFrame(rows)


def classify_zone(mode: str, value: float) -> tuple:
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


ZONE_STYLE = {
    "normal": "padding: 6px; border-radius: 4px; background: #d4edda; color: #155724;",
    "warning": "padding: 6px; border-radius: 4px; background: #fff3cd; color: #856404;",
    "danger": "padding: 6px; border-radius: 4px; background: #f8d7da; color: #721c24;",
}
ZONE_PREFIX = {"normal": "정상 — ", "warning": "주의 — ", "danger": "위험 — "}


class SweepCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.fig = matplotlib.figure.Figure(figsize=(6.0, 4.0), dpi=100)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)

    def update_figure(self, mode: str, value: float, y_col: str, y_label: str, slider_label: str):
        curve = sweep_curve(mode)
        self.ax.clear()
        self.ax.plot(curve["x"], curve[y_col], linestyle="-", linewidth=1.8, color="tab:blue")

        if mode == "eta_b":
            for lo_b, hi_b, band_label, color in ETAB_JSSG_BANDS:
                self.ax.axvspan(lo_b, hi_b, color=color, alpha=0.5, zorder=0, label=f"JSSG {band_label}")
            s_normal = compute_state(eta_b=1.0, fault_factor_fuel=1.0)
            self.ax.scatter([1.0], [s_normal[y_col]], color="black", marker="o", s=70,
                             zorder=6, label="정상(η_b=1.0)")
        else:
            for lo_z, hi_z, zone_label, color in FUEL_REF_ZONES:
                self.ax.axvspan(lo_z, hi_z, color=color, alpha=0.4, zorder=0, label=zone_label)
            for i, vx in enumerate((1.0, 0.7, 0.5)):
                vs = compute_state(eta_b=1.0, fault_factor_fuel=vx)
                self.ax.scatter([vx], [vs[y_col]], color="black", marker="x", s=70, zorder=6,
                                 label="TB 실측 교차검증점 (Issue #3)" if i == 0 else None)

        state_at_value = compute_state(eta_b=value, fault_factor_fuel=1.0) if mode == "eta_b" \
            else compute_state(eta_b=1.0, fault_factor_fuel=value)
        self.ax.axvline(value, color="gray", linestyle="--", linewidth=1)
        self.ax.scatter([value], [state_at_value[y_col]], color="tab:red", s=70, zorder=7, label="현재 선택값")
        self.ax.set_xlabel(slider_label, fontsize=11)
        self.ax.set_ylabel(y_label, fontsize=11)
        self.ax.tick_params(labelsize=9)
        title_suffix = "(JSSG 음영 + GPA 연속 건강지표)" if mode == "eta_b" else "(TB 실측점 인접 참고 구간)"
        self.ax.set_title(f"{y_label} vs {slider_label} {title_suffix}", fontsize=12)
        self.ax.legend(fontsize=8, loc="best")
        self.fig.tight_layout()
        self.draw()


class MetricWidget(QFrame):
    def __init__(self, label: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        cap = QLabel(label)
        cap.setStyleSheet("color: gray; font-size: 11px;")
        self.value = QLabel("-")
        self.value.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(cap)
        layout.addWidget(self.value)

    def set_value(self, text: str):
        self.value.setText(text)


class ScenarioPanel(QGroupBox):
    def __init__(self, title: str, slider_label: str, slider_key: str,
                 value_range: tuple, mode: str, y_col: str = "T3_K",
                 y_label: str = "T3 (K)", note: str | None = None,
                 default: float | None = None):
        super().__init__(title)
        self.slider_label = slider_label
        self.mode = mode
        self.y_col = y_col
        self.y_label = y_label
        self.lo, self.hi = value_range
        self.value = default if default is not None else round((self.lo + self.hi) / 2, 3)
        self.state = compute_state(
            eta_b=self.value if mode == "eta_b" else 1.0,
            fault_factor_fuel=1.0 if mode == "eta_b" else self.value,
        )
        self.status = None

        self.hist: list = []
        self.noise = 0.0
        self.now = 0.0
        self.base = self.state[y_col]
        self.prev = self.state[y_col]
        self._rng = np.random.default_rng()

        layout = QVBoxLayout(self)

        self.slider_caption = QLabel(f"{slider_label} (범위 {self.lo:.2f}~{self.hi:.2f}): {self.value:.2f}")
        layout.addWidget(self.slider_caption)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(round(self.lo * 100))
        self.slider.setMaximum(round(self.hi * 100))
        self.slider.setValue(round(self.value * 100))
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

        if note:
            note_label = QLabel(note)
            note_label.setWordWrap(True)
            note_label.setStyleSheet("color: #856404; font-size: 11px;")
            layout.addWidget(note_label)

        mode_caption_text = (
            "ℹ 참조 그래프의 배경 음영(onset/partial/full)은 JSSG-2007A가 명문으로 정의한 "
            "구간(0.05~0.80)입니다. 그 밖(0.80~1.00)은 Gas Path Analysis 관례(Saravanamuttoo 등 "
            "— 효율을 연속 건강지표로 취급)를 따라 연속으로 확장한 부분이며 JSSG 원문 근거는 아닙니다."
            if mode == "eta_b" else
            "ℹ 참조 그래프의 배경 색상 구간은 공식 규격(JSSG 같은) 구간이 아닙니다. Twin Builder "
            "실측 교차검증점(1.0/0.7/0.5, Issue #3) 3개 중 가장 가까운 점을 기준으로 나눈 참고용 "
            "구분이며, 경계값(0.85/0.60)은 세 실측점의 중간값일 뿐 근거문헌 수치가 아닙니다."
        )
        mode_caption = QLabel(mode_caption_text)
        mode_caption.setWordWrap(True)
        mode_caption.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(mode_caption)

        metrics_row = QHBoxLayout()
        self.metric_t3 = MetricWidget("T3 (연소실 출구)")
        self.metric_egt = MetricWidget("EGT")
        self.metric_wnet = MetricWidget("W_net")
        self.metric_sfc = MetricWidget("SFC")
        for m in (self.metric_t3, self.metric_egt, self.metric_wnet, self.metric_sfc):
            metrics_row.addWidget(m)
        layout.addLayout(metrics_row)

        self.canvas = SweepCanvas()
        layout.addWidget(self.canvas)

        live_row = QHBoxLayout()
        self.live_metric = MetricWidget(f"{y_label} (실시간, 시뮬레이션)")
        self.live_stats = QLabel("데이터 수집 중…")
        self.live_stats.setWordWrap(True)
        self.live_stats.setStyleSheet("color: gray; font-size: 11px;")
        live_row.addWidget(self.live_metric)
        live_row.addWidget(self.live_stats)
        layout.addLayout(live_row)

        live_warn = QLabel("⚠ 실측 데이터가 아니라 시뮬레이션 노이즈입니다 (AR(1) 평활, 07/10 스크립트와 동일 0.3% 수준).")
        live_warn.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(live_warn)

        self.zone_label = QLabel()
        self.zone_label.setWordWrap(True)
        layout.addWidget(self.zone_label)

        self._recompute_state_and_static()

    def _current_kwargs(self, value):
        if self.mode == "eta_b":
            return dict(eta_b=value, fault_factor_fuel=1.0)
        return dict(eta_b=1.0, fault_factor_fuel=value)

    def _on_slider_changed(self, int_value: int):
        self.value = int_value / 100.0
        self._recompute_state_and_static()

    def _recompute_state_and_static(self):
        self.slider_caption.setText(
            f"{self.slider_label} (범위 {self.lo:.2f}~{self.hi:.2f}): {self.value:.2f}"
        )
        self.state = compute_state(**self._current_kwargs(self.value))

        self.metric_t3.set_value(f"{self.state['T3_K']:.0f} K")
        self.metric_egt.set_value(f"{self.state['EGT_K']:.0f} K")
        self.metric_wnet.set_value(f"{self.state['W_net_kW']:.0f} kW")
        self.metric_sfc.set_value(f"{self.state['SFC']:.2f} kg/kWh")

        self.canvas.update_figure(self.mode, self.value, self.y_col, self.y_label, self.slider_label)

        zone_text, zone_level = classify_zone(self.mode, self.value)
        self.zone_label.setText(ZONE_PREFIX[zone_level] + zone_text)
        self.zone_label.setStyleSheet(ZONE_STYLE[zone_level])
        self.status = zone_text

    def live_tick(self):
        sigma_step = LIVE_NOISE_LEVEL * float(np.sqrt(1.0 - LIVE_AR_COEF ** 2))
        target = self.state[self.y_col]
        for i in range(LIVE_SUBSAMPLES_PER_TICK):
            self.base += LIVE_RAMP_RATE * (target - self.base)
            self.noise = LIVE_AR_COEF * self.noise + self._rng.normal(0.0, sigma_step)
            self.now += LIVE_DT
            v_sample = self.base * (1.0 + self.noise)
            self.hist.append((self.now, v_sample))

        cutoff = self.now - LIVE_WINDOW_SEC
        self.hist = [(t, v) for t, v in self.hist if t >= cutoff]

        hist_v = [v for _, v in self.hist]
        current_val = hist_v[-1] if hist_v else target
        delta = current_val - self.prev
        self.prev = current_val

        self.live_metric.set_value(f"{current_val:,.1f}  ({delta:+.2f})")
        if len(hist_v) >= 2:
            arr = np.array(hist_v)
            self.live_stats.setText(
                f"최근 {LIVE_WINDOW_SEC:.0f}초 롤링 통계\n"
                f"평균 {arr.mean():,.1f} · 표준편차 {arr.std():.3f} · "
                f"최대편차(peak-to-peak) {(arr.max() - arr.min()):.2f}"
            )
        else:
            self.live_stats.setText("데이터 수집 중…")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TPE331-10 실시간 고장 탐지 데모")
        self.resize(1400, 950)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        title = QLabel("TPE331-10 실시간 고장 탐지 데모")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        caption = QLabel("real_engine_model_utils.py 공통 엔진 물리모델 기반 — 독립 eta_b 포트 (Issue #9, 2026-07-08)")
        caption.setStyleSheet("color: gray;")
        outer.addWidget(title)
        outer.addWidget(caption)

        panels_row = QHBoxLayout()
        self.panel1 = ScenarioPanel(
            "시나리오1 — 실화 (Flameout)", "연소효율 η_b", "etab",
            ETAB_RANGE, mode="eta_b", default=1.00,
        )
        self.panel2 = ScenarioPanel(
            "시나리오2 — 연료계통 고장 (Fuel Fault)", "faultFactor_fuel", "fuelfactor",
            FUEL_RANGE, mode="fault_factor", note=FUEL_NOTE,
        )
        panels_row.addWidget(self.panel1)
        panels_row.addWidget(self.panel2)
        outer.addLayout(panels_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(divider)

        cause_title = QLabel("고장 원인 추정 (FAR gap 기반, Issue #9)")
        cause_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        outer.addWidget(cause_title)

        cause_info = QLabel(CAUSE_DISCLAIMER)
        cause_info.setWordWrap(True)
        cause_info.setStyleSheet("padding: 8px; border-radius: 4px; background: #d1ecf1; color: #0c5460;")
        outer.addWidget(cause_info)

        cause_row = QHBoxLayout()
        self.cause_label1 = QLabel()
        self.cause_label1.setWordWrap(True)
        self.cause_label2 = QLabel()
        self.cause_label2.setWordWrap(True)
        cause_row.addWidget(self.cause_label1)
        cause_row.addWidget(self.cause_label2)
        outer.addLayout(cause_row)

        compare_box = QGroupBox("두 패널의 원본 물리량 비교 (디버깅용)")
        compare_layout = QVBoxLayout(compare_box)
        self.compare_table = QTableWidget()
        self.compare_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        compare_layout.addWidget(self.compare_table)
        outer.addWidget(compare_box)

        self.panel1.slider.valueChanged.connect(self._refresh_cause_and_table)
        self.panel2.slider.valueChanged.connect(self._refresh_cause_and_table)
        self._refresh_cause_and_table()

        self.timer = QTimer(self)
        self.timer.setInterval(TIMER_INTERVAL_MS)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _on_tick(self):
        self.panel1.live_tick()
        self.panel2.live_tick()

    def _refresh_cause_and_table(self):
        s1, s2 = self.panel1.state, self.panel2.state
        gap1_ok = abs(s1["FAR_gap"]) < FAR_GAP_EPS
        gap2_ok = abs(s2["FAR_gap"]) < FAR_GAP_EPS
        self.cause_label1.setText(
            f"시나리오1 판정(슬라이더 기준): <b>{self.panel1.status or '평가 불가'}</b><br>"
            f"FAR gap = {s1['FAR_gap']:.6f} → "
            f"{'연료공급 정상 (원인=연소효율 저하 신호)' if gap1_ok else '연료공급 이상 신호 감지'}"
        )
        self.cause_label2.setText(
            f"시나리오2 판정(슬라이더 기준): <b>{self.panel2.status or '평가 불가'}</b><br>"
            f"FAR gap = {s2['FAR_gap']:.6f} → "
            f"{'연료공급 정상' if gap2_ok else '연료공급 이상 (원인=연료계통 고장 신호)'}"
        )

        df = pd.DataFrame([s1, s2], index=["시나리오1", "시나리오2"]).T
        self.compare_table.setRowCount(len(df.index))
        self.compare_table.setColumnCount(len(df.columns))
        self.compare_table.setHorizontalHeaderLabels(list(df.columns))
        self.compare_table.setVerticalHeaderLabels(list(df.index))
        for i, row_name in enumerate(df.index):
            for j, col_name in enumerate(df.columns):
                val = df.loc[row_name, col_name]
                item = QTableWidgetItem(f"{val:.6f}" if isinstance(val, float) else str(val))
                self.compare_table.setItem(i, j, item)
        self.compare_table.resizeColumnsToContents()


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
