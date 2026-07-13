# UAV 터보프롭 엔진 이상탐지 프로젝트

> Ansys Simulation Challenge 참가작 | 팀원 2명 | 7일 개발

## 폴더 구조

```
├── code       ← Python 소스 파일
├── components     ← Twin Builder 구조 코드 파일
└── docs 
---

## 연구 주제

**UAV 터보프롭 엔진 실시간 상태 진단을 위한 Twin Builder + AI 융합 이상탐지 시스템**

- 물리 시뮬레이션(Ansys Twin Builder 1D) + AI(PCA Autoencoder → LSTM Autoencoder) 하이브리드
- 집중 고장 모드: 연소실 실화(Flameout) — JSSG-2007A §3.2.2.3.5 / §3.2.2.6

---

## 목표

- 물리 시뮬레이션(Ansys Twin Builder) + AI(PCA Autoencoder → LSTM Autoencoder) 하이브리드 이상탐지 시스템 구축
- TPE331-10 터보프롭 엔진의 실시간 상태 진단(CBM+, Condition-Based Maintenance Plus) 가능성 검증
- JSSG-2007A 요구도를 근거로 디지털 트윈의 입증 적용 범위를 체계적으로 정의
- 서로 다른 물리적 기전을 가진 두 가지 독립 고장 시나리오(연소실 실화, 연료계통 고장)에 대해 Python 시뮬레이션과 Ansys Twin Builder 결과를 상호 검증

---

## 고장 시나리오

### 시나리오 1 — 연소실 실화 (Flameout, `FF-FLAMEOUT`)

| 항목 | 내용 |
|------|------|
| 근거 | JSSG-2007A §3.2.2.3.5 (onset), §3.2.2.6 (full) |
| 물리적 기전 | 연소 효율 η_b 저하 — 연소 자체가 덜 일어남 |
| 물리 모델 | Plan A (Python 자체 브레이턴 사이클, `turboprop_simulator_utils.py`) |
| 생성 스크립트 | `01_시뮬레이션_코드/04_jssg_fault_generator.py` |

단계별 η_b 범위 (각 단계 1,000샘플, 총 3,000샘플):

| 단계 | η_b 범위 | 근거 |
|------|---------|------|
| onset (초기) | 0.65 ~ 0.80 | JSSG-2007A §3.2.2.3.5 |
| partial (부분) | 0.35 ~ 0.65 | onset~full 선형 보간 추정 (⚠ JSSG 정의 없음, 임의 설정) |
| full (완전) | 0.05 ~ 0.35 | JSSG-2007A §3.2.2.6 |

> ⚠ **Twin Builder 이식 불가 확인 (2026-07-04)**: VHDL-AMS Combustor entity에는 η_b(연소효율) 파라미터 자체가 없음 — 존재하는 것은 eff(압력손실계수, `p_out = eff × p_in`)뿐이며 온도·에너지 계산과는 무관. 따라서 시나리오1은 실제 Twin Builder 모델로 이식할 방법이 없어, 검증 전까지 Plan A(Python 전용) 잠정 대체재로 유지한다.

### 시나리오 2 — 연료계통 고장 (Fuel System Fault, `FS-FUELSTARV`)

| 항목 | 내용 |
|------|------|
| 근거 | GitHub Issue #6 (Twin Builder VHDL-AMS 컴포넌트 코드 공유), Issue #3 (`faultFactor_fuel` 실측 검증) |
| 물리적 기전 | `faultFactor_fuel`이 연료-공기비 demand에 곱해짐 — comb_ref(명령 TIT)는 그대로인데 실제 연료 공급만 부족해짐 (명령 vs 실제의 괴리) |
| 물리 모델 | 실제 Twin Builder VHDL-AMS 컴포넌트 코드를 Python으로 그대로 이식·교차검증 완료 |
| 핵심 고장 시그니처 | `TIT_error = comb_ref − T3` |
| 생성 스크립트 | `01_시뮬레이션_코드/07_fuel_fault_generator.py` |

`faultFactor_fuel` 3케이스 (Issue #3 실측 검증, 지상 설계점 기준):

| 케이스 | faultFactor_fuel | 결과 |
|--------|-------------------|------|
| Case1 (정상) | 1.0 | comb_t_out ≈ comb_ref (오차 0) |
| Case2 (경미, moderate) | 0.7 | comb_t_out ≈ comb_ref − 235K (1365K → ~1130K) |
| Case3 (중증, severe) | 0.5 | comb_t_out ≈ comb_ref − 400K (1365K → ~965K) |

실제 컴포넌트 파라미터 (Issue #6 코드 + Issue #3 / `06_vhdl_comparison.py` 교차검증 — entity generic 기본값과 다름 주의):

| 파라미터 | 값 |
|----------|-----|
| PR (compressor) | 10.55 |
| η_comp | 0.85 |
| comb_ref | 1365 K |
| eff (combustor) | 0.96 |
| η_t | 0.87 |
| η_m | 0.98 |
| ṁ (mflow) | 3.493 kg/s |

두 시나리오는 물리적 기전(η_b↓ vs 연료계통 FAR 고장)뿐 아니라 물리 모델 자체가 다르므로(시나리오1: Plan A 근사 모델 / 시나리오2: 실제 검증된 Twin Builder 모델), PCA Autoencoder 이상탐지도 하나로 섞지 않고 완전히 독립된 파이프라인으로 평가한다 (`02_anomaly_detector.py`).

## 핵심 근거 문헌

| 문헌 | 활용 |
|------|------|
| Saravanamuttoo et al., *Gas Turbine Theory* 7th ed. (2017) | π_c, η_c, η_t 범위 |
| Mattingly, *Elements of Gas Turbine Propulsion* (2006) | FAR, ΔP_b |
| JSSG-2007A (2007) | η_b, 실화 단계 정의 |
| Park et al., *Energy* 305 (2023) DOI:10.1016/j.energy.2023.129697 | η_pt 범위 |
| ISO 2533 | 표준 대기 (T₁, P₁) |
| ASTM D1655 / MIL-DTL-83133 | Jet-A 연료 LHV |
| arXiv:2505.24044 (2025) | PCA-AE 방법론 |
