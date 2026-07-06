# 01_시뮬레이션_코드

UAV 터보프롭 엔진 브레이턴 사이클 시뮬레이션 및 이상탐지 Python 소스코드

## 파일 목록

| 파일 | 역할 | 출력 |
|------|------|------|
| `turboprop_simulator_utils.py` | 브레이턴 사이클 공통 함수(Plan A), DEFAULTS/RANGES 정의 | — |
| `real_engine_model_utils.py` | 실제 Twin Builder VHDL-AMS 엔진 공통 함수(inlet/compressor/combustor/turbine). 시나리오1(방안B)·시나리오2가 공유 (Issue #7, 2026-07-06 07에서 분리) | — |
| `01_turboprop_simulator.py` | 정상 운전 데이터 3,000샘플 생성 | `../02_시뮬레이션_데이터/normal_data.csv` |
| `03_preprocess_flameout.py` | 시나리오1 전처리 파이프라인(라벨/eta_b 누수 컬럼 제거, 정상 train/holdout 분리, StandardScaler) — 09_preprocess_fuel_fault.py의 시나리오1 대응판 (2026-07-08 신설, 번호 공백이던 03 사용) | `PreprocessedData` (X_train_normal/X_holdout_normal/X_fault, scaler) |
| `04_jssg_fault_generator.py` | 실화(시나리오1) 고장 데이터 3,000샘플 생성 — Plan A(방안 A류, η_b 직접곱셈), 병행 보관용 | `../02_시뮬레이션_데이터/jssg_fault_data.csv` |
| `07_fuel_fault_generator.py` | 연료계통 고장(시나리오2) 데이터 생성 — 실제 Twin Builder VHDL-AMS 컴포넌트 코드 이식 (GitHub Issue #6/#3). real_engine_model_utils.py 공통 모듈 사용 | `../02_시뮬레이션_데이터/combustor_real_normal_data.csv`(정상 3,000), `fuel_fault_data.csv`(고장 3,000) |
| `10_combustion_efficiency_fault_generator.py` | 연소효율(η_b) 저하 실화(시나리오1) 데이터 생성 — **방안 B**(연료 주입량 사전보정) 적용, 실제 Twin Builder 모델로 재현 (GitHub Issue #7, 2026-07-06) | `../02_시뮬레이션_데이터/etab_flameout_fault_data.csv`(고장 3,000) |
| `02_anomaly_detector.py` | PCA-AE 이상탐지 학습·평가·시각화. 시나리오1(Plan A)과 시나리오2(실제 Twin Builder 모델)는 물리 모델이 달라 **별도 PCA로 독립 평가** | `../03_이상탐지_결과/fig1~2.png` (+있으면 fig5.png) |
| `05_twin_builder_comparison.py` | Python vs Twin Builder 잔차 비교 | `../03_이상탐지_결과/fig3~4.png, comparison_summary.csv` |
| `06_vhdl_comparison.py` | Python vs VHDL Twin Builder 파라미터/결과 비교. Issue #6 검토 결과(eff↔η_b 명칭 혼동, η_b 미존재) + Issue #7 방안 B 검증(시나리오 D) 반영 | 콘솔 출력 |
| `08_upload_to_supabase.py` | 시나리오2 CSV(정상+고장 6,000행)를 Supabase `public.fuel_fault_samples` 테이블에 업로드 | Supabase DB (project: Red-horse) |
| `09_preprocess_fuel_fault.py` | 시나리오2 전처리 파이프라인(라벨 누수 컬럼 제거, TIT_error_K 피처 추가, 정상 train/holdout 분리, StandardScaler) | `PreprocessedData` (X_train_normal/X_holdout_normal/X_fault, scaler) |
| `11_upload_flameout_to_supabase.py` | 시나리오1 CSV(정상+고장 6,000행)를 Supabase `public.flameout_fault_samples` 테이블에 업로드 (08의 시나리오1 대응판, 2026-07-08 신설) | Supabase DB (project: Red-horse) |
| `12_export_pca_artifacts.py` | 07/10(공통 real_engine_model_utils 기반) CSV를 전처리해 시나리오1·2 PCA/scaler/95th pct 임계값을 joblib으로 저장 — 13번 GUI가 재학습 없이 바로 로드 (2026-07-08 신설) | `../04_학습산출물/scenario{1,2}_{scaler,pca,meta}.joblib` |
| `13_gui_dashboard.py` | 실화(시나리오1)/연료계통고장(시나리오2) 나란히 비교 Streamlit GUI — η_b·faultFactor_fuel 슬라이더로 실시간 계산+이상탐지+상태판. 원인 추정 패널은 한계 명시(Issue #8 해결 전까지 참고용) (2026-07-08 신설) | 브라우저 대시보드 (`streamlit run 13_gui_dashboard.py`) |
| `14_upload_etab_to_fuel_fault_samples.py` | 10번(방안B) 고장 데이터를 Supabase `public.fuel_fault_samples.eta_b` 컬럼에 업로드(정상 행은 07/08과 중복이라 재업로드 안 함) (2026-07-08 신설) | Supabase DB (project: Red-horse) |

## 고장 시나리오 2종 비교

| 구분 | 시나리오1: 실화(Flameout) | 시나리오2: 연료계통 고장 |
|------|---------------------------|--------------------------|
| 생성 스크립트 | `04_jssg_fault_generator.py` | `07_fuel_fault_generator.py` |
| 물리 모델 | Plan A (Python 자체 브레이턴 사이클, `turboprop_simulator_utils.py`) | **실제 Twin Builder VHDL-AMS 컴포넌트 코드 이식** (GitHub Issue #6) |
| 물리적 기전 | η_b(연소효율) 저하 — 연소 자체가 덜 일어남 | `faultFactor_fuel`이 연료-공기비 demand에 곱해짐 — comb_ref(명령 TIT)는 그대로인데 실제 연료공급만 부족 (Issue #3) |
| 단계 | onset/partial/full (η_b 0.65→0.05) | moderate/severe (faultFactor_fuel 0.7/0.5, Issue #3 실측 검증) |
| 근거 | §3.2.2.3.5, §3.2.2.6 (partial은 보간 추정) | GitHub Issue #6(컴포넌트 코드), Issue #3(faultFactor_fuel 검증 수치) |
| Twin Builder 모델링 | **방안 B로 이식 완료 (Issue #7, 2026-07-06)** — `10_combustion_efficiency_fault_generator.py`가 `real_engine_model_utils.py` 공통 엔진 모델에 η_b를 입력단 보정(far_actual = far_demand × η_b)으로 대입해 재현. **방안 A(계산식 직접 추가)는 여전히 불가(Issue #6): VHDL Combustor entity에는 η_b(연소효율) 파라미터 자체가 없음** — 있는 것은 eff(압력손실계수, p_out=eff*p_in)뿐이며 온도/에너지 계산과 무관. `04`는 Plan A 병행 보관용으로 유지(방안 A 별도 과제 대비) | **완성 및 실측 검증됨** (Case1/2/3) |
| 비고 | 정량 검증은 `06_vhdl_comparison.py` "시나리오 D" 절 참조 — Plan A와 방안 B는 물리 구조가 달라 절대값이 아닌 정성적 추세/설계점 수렴으로 검증(Issue #7 요청사항 2) | comb_ref=1365K, PR=10.55 등은 Issue #6 entity 기본값이 아니라 `06_vhdl_comparison.py`로 교차검증된 실제 스키매틱 값 (07 코드 주석 참조) |

두 시나리오는 물리적 기전이 다르지만(η_b↓ vs FAR 계통고장), 2026-07-06(Issue #7) 이후로는 **같은 실제 Twin Builder 엔진 모델(`real_engine_model_utils.py`)을 공유**하고 입력단 보정계수(η_b vs faultFactor_fuel)만 다르다. `02_anomaly_detector.py`는 여전히 시나리오1(Plan A, `jssg_fault_data.csv`)과 시나리오2를 별도 PCA로 평가하는데, 이는 시나리오1이 아직 `04`(Plan A) 기준 데이터로 학습되어 있기 때문 — `10`의 방안 B 데이터로 전환할지는 별도 결정 필요(아래 참고).

> ⚠ **Issue #6 검토 결과 (2026-07-04, `06_vhdl_comparison.py` 반영):**
> 1. **명칭 혼동** — `06_vhdl_comparison.py`의 시나리오 B/B2에서 브레이턴 에너지식의 η_b 자리에 대입해 온 값(0.96)은 실제로는 VHDL Combustor entity의 **eff(압력손실계수)**이며 **η_b(연소효율)가 아니다**. eff는 `p_out = eff * p_in`으로 압력에만 작용하고 온도/에너지 계산에는 관여하지 않는다(`07_fuel_fault_generator.py`의 `combustor()` 참조). Plan A의 η_b(0.990, JSSG-2007A)와는 물리적으로 다른 양이므로 혼동해서는 안 된다.
> 2. **시나리오1(실화) 방안 A 이식 불가** — VHDL Combustor entity에는 η_b(연소효율) 파라미터 자체가 없어, η_b를 계산식에 직접 추가하는 방안 A는 이 실제 Twin Builder 모델에 적용할 수 없다.

> ✅ **Issue #7 결정 (2026-07-06):** 방안 B(연료 주입량을 η_b만큼 미리 줄여서 주입하는 입력단 우회 보정) 채택 — `10_combustion_efficiency_fault_generator.py` 참조. Combustor 블록 계산식 자체는 07/10에서 동일하며 수정하지 않았다. 방안 A는 일정 여유 시 별도 과제로 진행.

> ⚠ **Issue #8 (2026-07-08, 진행 중):** 방안 B는 η_b와 faultFactor_fuel이 동일한 입력단(far_actual = far_demand × factor)을 공유하게 만들어, 실화와 연료계통고장을 결과 데이터만으로 구분(원인 진단)할 수 없다는 한계가 있다. Twin Builder Combustor entity에 독립적인 eta_b 포트 + fa_demand_out/wf_out 출력을 추가해달라고 요청한 상태 — 완료 전까지 `13_gui_dashboard.py`의 원인 추정 패널은 참고용이며 신뢰도가 낮음을 명시한다.

## 실행 순서

```
python 01_turboprop_simulator.py
python 04_jssg_fault_generator.py           # 시나리오1, Plan A (병행 보관용)
python 07_fuel_fault_generator.py           # 시나리오2 + 공통 정상 베이스라인 생성 (10 실행 전 필수)
python 10_combustion_efficiency_fault_generator.py   # 시나리오1, 방안 B (Issue #7)
python 06_vhdl_comparison.py                # 시나리오 D 검증 포함
python 02_anomaly_detector.py
python 12_export_pca_artifacts.py           # 13번 GUI용 PCA/scaler 저장
streamlit run 13_gui_dashboard.py           # 실시간 비교 GUI
python 14_upload_etab_to_fuel_fault_samples.py   # eta_b 데이터 Supabase 반영(선택)
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
| η_b 방안 B 입력단 보정(far_actual = far_demand × η_b) | GitHub Issue #7 (2026-07-06 랩미팅 결정, 교수님 검토) | 방안 A(계산식 직접 추가)는 Issue #6 사유로 불가 — 10_combustion_efficiency_fault_generator.py 참조 |
| n_components = 6 | arXiv:2505.24044 (2025) — scree plot 99% 분산 기준 | 임의 설정 |
| 임계값 = 95th pct | anomaly detection 표준 관례 | 임의 설정 |
