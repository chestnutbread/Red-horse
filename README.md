# UAV 터보프롭 엔진 이상탐지 프로젝트

> Ansys Simulation Challenge 참가작 | 팀원 2명

## 폴더 구조

```
├── code       ← Python 소스 파일
├── components     ← Twin Builder 구조 코드 파일
└── docs
```

⚠ **2026-07-23 기준 안내**: 아래 §수식/파라미터는 팀 내부 `Ansys simulation_V2/` 작업분(로컬, 이 저장소에는 아직 미푸시)을 포함해 최신 상태로 정리한 것입니다. 이 저장소의 `code/real_engine_model_utils.py`는 `comb_ref=1365K` 기준이며, V2에서 SSOT가 `comb_ref=1250K`로 갱신되었고 추진체인(gearbox/propeller/nozzle) 확장과 4-class 고장판별기(`identify_faults`/`classify_case`)가 추가되었습니다 — 해당 V2 코드는 별도 푸시 예정입니다.

---

## 연구 주제

**UAV 터보프롭 엔진 실시간 상태 진단을 위한 Twin Builder + AI 융합 이상탐지 시스템**

- 물리 시뮬레이션(Ansys Twin Builder 1D) + AI(PCA Autoencoder → LSTM Autoencoder) 하이브리드
- 집중 고장 모드: 연소실 실화(Flameout) — JSSG-2007A §3.2.2.3.5 / §3.2.2.6, 연료계통 고장

---

## 목표

- 물리 시뮬레이션(Ansys Twin Builder) + AI(PCA Autoencoder → LSTM Autoencoder) 하이브리드 이상탐지 시스템 구축
- TPE331-10 터보프롭 엔진의 실시간 상태 진단(CBM+, Condition-Based Maintenance Plus) 가능성 검증
- JSSG-2007A 요구도를 근거로 디지털 트윈의 입증 적용 범위를 체계적으로 정의
- 서로 다른 물리적 기전을 가진 두 가지 독립 고장 시나리오(연소실 실화, 연료계통 고장)에 대해 Python 시뮬레이션과 Ansys Twin Builder 결과를 상호 검증

---

## ⚠ 용어 주의 — 이 프로젝트에 "시나리오1"이 두 개 있습니다

| 구분 | 대상 파라미터 | 데이터/파이프라인 |
|---|---|---|
| **Python 코드의 "시나리오1"** (`real_engine_model_utils.py`, `identify_faults`/`classify_case`) | **η_b (연소효율) 저하** — JSSG-2007A §3.2.2.3.5/§3.2.2.6 "연소실 실화" | `ENGINE_PYTHON_THEORY`(노이즈 없는 이론값), Issue #9에서 VHDL Combustor entity에 독립 포트로 실제 구현됨 |
| **Twin Builder 실측/이상탐지 파이프라인의 "S1"** (Issue #10/#24) | **η_t (터빈 등엔트로피효율) 저하** | `ENGINE_EFF`(실측 시계열), PCA+통계적 판별 |

**JSSG-2007A 기준 공식 "시나리오1(연소실 실화)"은 η_b 저하로 확정**(Issue #26)되었으나, 이미 보고된 "탐지 정확도 100%/ROC-AUC=1.000/Cohen's d=4.90"은 **η_t 쪽 실측 결과**이며 η_b(본 코드가 검증하는 대상)의 통계적 탐지 성능이 아닙니다. 두 수치를 섞어 인용하지 마십시오.

---

## 고장 시나리오

### 시나리오 1 — 연소실 실화 (Flameout, `FF-FLAMEOUT`) — η_b 저하

| 항목 | 내용 |
|------|------|
| 근거 | JSSG-2007A §3.2.2.3.5 (onset), §3.2.2.6 (full) |
| 물리적 기전 | 연소 효율 η_b 저하 — 열발생 항에만 작용, 연료 공급량(FAR_actual)에는 영향 없음 |
| 물리 모델 | **Issue #9에서 VHDL Combustor entity에 독립 `eta_b` 포트가 실제로 추가됨** — 더 이상 Plan A 근사가 아니라 `real_engine_model_utils.combustor()`가 entity와 1:1 대응(방안A 정식 구현). Python↔VHDL 오차 <1e-9(`02_fault_scenario_verification.py`) |
| 판별 신호 | `FAR_gap ≡ 0`(연료는 정상 공급), TIT(=T4) 단조 감소 |

단계별 η_b 범위:

| 단계 | η_b 범위 |
|------|---------|
| onset (초기) | 0.65 ~ 0.80 |
| partial (부분) | 0.35 ~ 0.65 (onset~full 선형 보간 추정, JSSG 정의 없음) |
| full (완전) | 0.05 ~ 0.35 |

> ~~2026-07-04 "Twin Builder 이식 불가" 기록은 해소됨~~ — Issue #9에서 독립 `eta_b` 포트가 추가되어 실제 entity와 1:1 대응하는 정식 구현으로 전환 완료(2026-07-08).

### 시나리오 2 — 연료계통 고장 (Fuel System Fault, `FS-FUELSTARV`) — faultFactor_fuel 저하

| 항목 | 내용 |
|------|------|
| 근거 | Issue #6(VHDL-AMS 컴포넌트 코드 공유), Issue #3(`faultFactor_fuel` 실측 검증) |
| 물리적 기전 | `faultFactor_fuel`이 `FAR_demand`에 곱해짐 — comb_ref(명령 TIT)는 그대로인데 실제 연료 공급만 부족(`FAR_gap = FAR_demand×(1−faultFactor_fuel) > 0`) |
| 물리 모델 | 실제 Twin Builder VHDL-AMS 컴포넌트 코드를 Python으로 이식·교차검증 완료(오차<1e-9) |
| 핵심 시그니처 | `TIT_error = comb_ref − T4`, `wf`(연료유량) 단조 감소 |

`faultFactor_fuel` 케이스(Issue #3 실측 검증, 지상 설계점 기준):

| 케이스 | faultFactor_fuel |
|--------|-------------------|
| 정상 | 1.0 |
| mild | 0.8 |
| moderate | 0.7 |
| severe | 0.5 |

### 시나리오 4 — 동시 고장 (η_b<1 AND faultFactor_fuel<1)

`FAR_gap`·`wf`는 `faultFactor_fuel`만의 함수라 시나리오2와 완전히 동일한 값이 나옴(단독 판별 불가) — TIT가 시나리오2보다 항상 낮다는 점으로만 구분 가능. (FAR_gap, TIT) 2D 판별기 `classify_case()`가 {정상/S1/S2/S4} 4-class를 오차 <1e-6로 완전 분리.

---

## 핵심 수식 (스테이션별, `real_engine_model_utils.py` 기준)

표기: 하첨자=스테이션(T2=압축기입구 … T5=터빈출구, T4=TIT), 상첨자=지수.

**압축기**: T3 = T2·(1 + (1/η_c)·(π_c^((γa−1)/γa) − 1)), P3 = π_c·P2

**연소기**: FAR_demand = ((comb_ref/T3) − 1) / (LHV/(cp_g·T3) − comb_ref/T3), FAR_actual = FAR_demand·faultFactor_fuel
T4 = T3·(1 + FAR_actual·(LHV·η_b)/(cp_g·T3)) / (1 + FAR_actual), P4 = eff·P3
**FAR_gap = FAR_demand − FAR_actual** (핵심 판별신호)

**터빈**: T5 = T4 + ΔT_comp·η_m·(1+FAR_actual), P5 = P4·(1 − (1−T5/T4)/η_t)^(γg/(γg−1))

**역산기 `identify_faults(TIT, FAR_gap, comb_ref, T_in)`**: combustor() 식을 대수적으로 뒤집어 (faultFactor_fuel, η_b)를 직접 복원(노이즈 없는 조건에서 오차 <1e-6). 상세 유도·노즐/기어박스/프로펠러 수식은 `Ansys simulation_V2/02_검증결과/260724_수식_파라미터_기호_정리.md` 참조(V2, 로컬).

---

## 파라미터 (인스턴스 값 — 엔티티 generic 기본값과 다름 주의)

| 파라미터 | 값 | 비고 |
|----------|-----|------|
| π_c (압축비) | 10.55 | Honeywell 공식 사양, 엔티티 기본값 9.6 |
| η_c (압축기효율) | 0.85 | 팀 확정값(문헌 0.78~0.82 상단 초과 인지) |
| eff (연소기 압력손실계수) | 0.96 | η_b와 무관, 압력에만 작용 |
| comb_ref (SSOT) | **1250 K**(V2) / 1365 K(이 저장소 code/ 현재값) | 1250K = tit_limiter1 setpoint = Supabase 실측과 유일하게 일치 |
| η_t (터빈효율) | 0.87 | 본 Python 코드에서 상수 고정 — 고장 스윕 대상 아님(위 "용어 주의" 참조) |
| η_m (기계효율) | 0.90 | Issue #9: "0.98은 표기오류"로 정정 |
| ṁ (MFLOW) | 3.493 kg/s | Honeywell 공식 사양(7.7 lb/s) |
| γ_a / γ_g | 1.4 / 1.31 | 공기 / 연소가스 |
| K_τ(프로펠러 부하토크계수) | **0.16**(V2, 2026-07-23 정정) | 구 0.0512는 근거불명·정격출력 재현율 32% → 0.16으로 재계산, 재현율 99.98% |
| GR(기어비) | 26.229 | FAA TCDS E4WE Rev.34 |

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
| Honeywell TPE331-10 브로슈어(N61-1491-000-000) | π_c, ṁ, N_gg, N_prop |
| FAA TCDS E4WE Rev.34 | 기어비(GR) |
