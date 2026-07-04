# UAV 터보프롭 엔진 이상탐지 프로젝트

> Ansys Simulation Challenge 참가작 | 팀원 2명 | 7일 개발
> 최종 저장 경로: `N:\개인\2026\1_연구\엔진\`

---

## 폴더 구조

```
엔진/
├── 01_시뮬레이션_코드/       ← Python 소스 파일
├── 02_시뮬레이션_데이터/     ← CSV 데이터 파일
├── 03_이상탐지_결과/         ← 그래프(PNG) 및 비교 요약
├── 04_파라미터_문서/         ← 엑셀 파라미터 표, 가이드 문서
└── 05_Twin_Builder/          ← Twin Builder 프로젝트 및 출력 CSV
```

각 폴더에 `README.md`가 있으며, 파일별 근거 자료가 정리되어 있습니다.

---

## 파일 저장 규칙 (Claude와 협업 시)

| 결과물 종류 | 저장 폴더 |
|------------|----------|
| Python 소스 (.py) | `01_시뮬레이션_코드/` |
| CSV 데이터 | `02_시뮬레이션_데이터/` |
| 그래프 (PNG), 분석 결과 CSV | `03_이상탐지_결과/` |
| 엑셀 문서, 가이드, 보고서 | `04_파라미터_문서/` |
| Twin Builder 파일, 팀원 결과 | `05_Twin_Builder/` |

새로운 유형의 결과물이 생길 경우 `(숫자)_(폴더명)` 형식으로 폴더를 추가합니다.

---

## 연구 주제

**UAV 터보프롭 엔진 실시간 상태 진단을 위한 Twin Builder 1D + AI 융합 이상탐지 시스템**

- 물리 시뮬레이션(Ansys Twin Builder 1D) + AI(PCA Autoencoder → LSTM Autoencoder) 하이브리드
- 집중 고장 모드: 연소실 실화(Flameout) — JSSG-2007A §3.2.2.3.5 / §3.2.2.6

---

## 목표

- 물리 시뮬레이션(Ansys Twin Builder 1D) + AI(PCA Autoencoder → LSTM Autoencoder) 하이브리드 이상탐지 시스템 구축
- TPE331-10 터보프롭 엔진의 실시간 상태 진단(CBM+, Condition-Based Maintenance Plus) 가능성 검증
- JSSG-2007A 요구도를 근거로 디지털 트윈의 MOC-A(Analysis) 입증 적용 범위를 체계적으로 정의 — 기존 CFD 유체·구조 시뮬레이션에 편중된 MOC-A 입증 관행의 공백을 메움
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

---

## 진행 현황 (2026-07-04 기준)

| 항목 | 상태 |
|------|------|
| 시나리오1 (실화) Python 시뮬레이션 및 이상탐지 | ✅ 완료 — 3,000샘플, PCA-AE ROC-AUC 1.000, 단계별 탐지율 100% |
| 시나리오2 (연료계통 고장) Python 시뮬레이션 | ✅ 완료 — 실제 Twin Builder 컴포넌트 코드 이식, 정상/고장 각 3,000/3,000샘플 |
| 시나리오1 Twin Builder 모델링 | ❌ 이식 불가 확인 (Combustor entity에 η_b 파라미터 없음) — Python 대체재 유지 |
| 시나리오2 Twin Builder 모델링 | ✅ 완료 및 실측 검증 (Case1/2/3, Issue #3/#6) |
| Supabase DB 업로드 (시나리오2) | ✅ 완료 — `public.fuel_fault_samples` 테이블 |
| Python vs Twin Builder 잔차 비교 (시나리오1) | ⏳ 진행 중 (팀원 Twin Builder 실행 대기) |
| 보고서·발표자료 | ⏳ 예정 |

| 일차 | 상태 | 내용 |
|------|------|------|
| Day 1 | ✅ | 시뮬레이터 코드, 기본 고장 시나리오 |
| Day 2 | ✅ | PCA-AE 이상탐지, 결과 그래프 |
| Day 3 | ✅ | Plan A 적용, JSSG 실화 집중, Supabase DB, 파라미터 문서 |
| Day 4 | ✅ | 연료계통 고장(시나리오2) 실제 Twin Builder 컴포넌트 코드 이식 및 검증 (Issue #3/#6 반영) |
| Day 5 | ⏳ | Python vs Twin Builder 잔차 비교 (시나리오1) |
| Day 6 | ⏳ | 보고서·발표자료 완성 |
| Day 7 | ⏳ | 제출 |

> ⚠ 탐지율 100%는 정상·고장 데이터가 동일 함수로 생성되어 신호가 수학적으로 분리된 결과이며, 센서 노이즈(0.5%)도 실제(±2°C, ~0.3%) 대비 보수적으로 설정됨. Twin Builder 비교 이후 현실성 재평가가 필요하다.

---

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
