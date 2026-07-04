# 01_시뮬레이션_코드

UAV 터보프롭 엔진 브레이턴 사이클 시뮬레이션 및 이상탐지 Python 소스코드

## 파일 목록

| 파일 | 역할 | 출력 |
|------|------|------|
| `turboprop_simulator_utils.py` | 브레이턴 사이클 공통 함수, DEFAULTS/RANGES 정의 | — |
| `01_turboprop_simulator.py` | 정상 운전 데이터 3,000샘플 생성 | `../02_시뮬레이션_데이터/normal_data.csv` |
| `04_jssg_fault_generator.py` | 실화(시나리오1) 고장 데이터 3,000샘플 생성 | `../02_시뮬레이션_데이터/jssg_fault_data.csv` |
| `07_fuel_fault_generator.py` | 연료계통 고장(시나리오2) 데이터 생성 — 실제 Twin Builder VHDL-AMS 컴포넌트 코드 이식 (GitHub Issue #6/#3) | `../02_시뮬레이션_데이터/combustor_real_normal_data.csv`(정상 3,000), `fuel_fault_data.csv`(고장 3,000) |
| `02_anomaly_detector.py` | PCA-AE 이상탐지 학습·평가·시각화. 시나리오1(Plan A)과 시나리오2(실제 Twin Builder 모델)는 물리 모델이 달라 **별도 PCA로 독립 평가** | `../03_이상탐지_결과/fig1~2.png` (+있으면 fig5.png) |
| `05_twin_builder_comparison.py` | Python vs Twin Builder 잔차 비교 | `../03_이상탐지_결과/fig3~4.png, comparison_summary.csv` |
| `06_vhdl_comparison.py` | Python vs VHDL Twin Builder 파라미터/결과 비교 | 콘솔 출력 |

## 고장 시나리오 2종 비교

| 구분 | 시나리오1: 실화(Flameout) | 시나리오2: 연료계통 고장 |
|------|---------------------------|--------------------------|
| 생성 스크립트 | `04_jssg_fault_generator.py` | `07_fuel_fault_generator.py` |
| 물리 모델 | Plan A (Python 자체 브레이턴 사이클, `turboprop_simulator_utils.py`) | **실제 Twin Builder VHDL-AMS 컴포넌트 코드 이식** (GitHub Issue #6) |
| 물리적 기전 | η_b(연소효율) 저하 — 연소 자체가 덜 일어남 | `faultFactor_fuel`이 연료-공기비 demand에 곱해짐 — comb_ref(명령 TIT)는 그대로인데 실제 연료공급만 부족 (Issue #3) |
| 단계 | onset/partial/full (η_b 0.65→0.05) | moderate/severe (faultFactor_fuel 0.7/0.5, Issue #3 실측 검증) |
| 근거 | §3.2.2.3.5, §3.2.2.6 (partial은 보간 추정) | GitHub Issue #6(컴포넌트 코드), Issue #3(faultFactor_fuel 검증 수치) |
| Twin Builder 모델링 | **미완성** (사용자 확인, 2026-07-04) — 04는 Python 전용 잠정 대체재 | **완성 및 실측 검증됨** (Case1/2/3) |
| 비고 | 실제 Twin Builder 모델 완성 시 이 스크립트를 대체할 계획 | comb_ref=1365K, PR=10.55 등은 Issue #6 entity 기본값이 아니라 `06_vhdl_comparison.py`로 교차검증된 실제 스키매틱 값 (07 코드 주석 참조) |

두 시나리오는 물리적 기전이 다를 뿐 아니라(η_b↓ vs FAR 계통고장) **현재는 물리 모델 자체도 다르다** — 시나리오1은 Plan A 근사 모델, 시나리오2는 실제 검증된 Twin Builder 모델이다. 그래서 `02_anomaly_detector.py`는 두 시나리오를 하나의 PCA로 섞지 않고 완전히 독립된 파이프라인으로 평가한다.

## 실행 순서

```
python 01_turboprop_simulator.py
python 04_jssg_fault_generator.py
python 07_fuel_fault_generator.py
python 02_anomaly_detector.py
# Twin Builder CSV 생성 후:
python 05_twin_builder_comparison.py
```

## 근거 자료

| 파라미터 | 근거 문헌 | 비고 |
|----------|----------|------|
| π_c = 9.6 | Garrett TPE331-10 제원; Saravanamuttoo et al., *Gas Turbine Theory* 7th ed. (2017) 부록A | 문헌 출처 |
| η_c = 0.80 | Saravanamuttoo 2017 Ch.5 — 2단 원심 압축기 0.78~0.82 | 문헌 출처 |
| FAR = 0.018 | Mattingly, *Elements of Gas Turbine Propulsion* (2006) Ch.9 | 문헌 출처 |
| η_b = 0.990 | JSSG-2007A §3.2.2.6 신규 엔진 연소 효율 기준 | 문헌 출처 |
| η_t = 0.85~0.92 | Saravanamuttoo 2017 Ch.7 — 축류 터빈 효율 범위 | **범위 샘플링** |
| η_pt = 0.84~0.90 | Park et al. (2023), *Energy* 305 — DOI:10.1016/j.energy.2023.129697 | **범위 샘플링** |
| ΔP_b = 3~5% | Mattingly 2006 Ch.9 — 환형연소실 압력 손실 설계 기준 | **범위 샘플링** |
| 실화 onset η_b = 0.65~0.80 | JSSG-2007A §3.2.2.3.5 | 문헌 출처 |
| 실화 partial η_b = 0.35~0.65 | onset~full 선형 보간 가정 (JSSG 정의 없음) | **⚠ 임의 설정** |
| 실화 full η_b = 0.05~0.35 | JSSG-2007A §3.2.2.6 | 문헌 출처 |
| 연료계통 고장 faultFactor_fuel = 1.0/0.7/0.5 | GitHub Issue #3 — Twin Builder 실측 검증 (Case1/2/3) | 문헌 출처(팀 내부 실험) |
| 연료계통 PR=10.55, comb_ref=1365K, eff=0.96, η_t=0.87 | GitHub Issue #6 코드 + `06_vhdl_comparison.py` 교차검증 | ⚠ Issue #6 entity generic 기본값(PR=8.0, eff=0.95, η_t=0.88)과 다름 — 실제 스키매틱 설정값 사용 |
| n_components = 6 | arXiv:2505.24044 (2025) — scree plot 99% 분산 기준 | 임의 설정 |
| 임계값 = 95th pct | anomaly detection 표준 관례 | 임의 설정 |
