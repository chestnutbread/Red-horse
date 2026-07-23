# UAV 터보프롭 엔진 이상탐지 프로젝트

Ansys Simulation Challenge 참가작 | 팀원 2명 (chestnutbread, junslee02)

## 폴더 구조

```
├── code        ← Python 소스 파일
├── components  ← Twin Builder 구조 코드 파일
└── docs
```

## 이 문서에 대하여 (2026-07-24 갱신)

이 README는 GitHub 이슈 원문(#1~#26), Supabase(cbakdduteipgpycrtrmf) 실측 테이블, 로컬 Python 코드(real_engine_model_utils.py, 02_fault_scenario_verification.py, 03_python_theory_dataset_generator.py) 세 가지 1차 자료만 근거로 독립적으로 재작성했습니다. 이전 세션들이 남긴 "확정" 서술을 그대로 이어받지 않고, junslee02가 이슈에서 실제로 무엇을 확인/미확인했는지 원문 인용 기준으로 재판정했습니다. "확정"이라는 표현은 junslee02 본인이 이슈에서 명시적으로 확인한 경우에만 사용하고, 그 외에는 "~로 판단됨(근거: …)" 또는 "미해결"로 표기합니다.

## 연구 주제

UAV 터보프롭 엔진 실시간 상태 진단을 위한 Twin Builder + AI 융합 이상탐지 시스템. 물리 시뮬레이션(Ansys Twin Builder 1D) + AI(PCA Autoencoder → LSTM Autoencoder) 하이브리드. TPE331-10 터보프롭 엔진의 실시간 상태 진단(CBM+) 가능성 검증.

---

## 1. 고장 시나리오 정의 및 근거

### 1-1. 이 프로젝트에는 서로 다른 "시나리오1"이 두 개 존재합니다 (미해결 용어 혼선)

원문 대조 결과, 이 혼선은 프로젝트 초기(Issue #1, 2026-06-30)부터 있었고 아직 junslee02의 명시적 확인으로 닫히지 않았습니다.

| 계열 | 정의 | 실제 근거 | 현재 상태 |
|---|---|---|---|
| Issue #1 원안 / Twin Builder 실측 파이프라인의 "S1" (Issue #1, #10, #24) | η_t (터빈 등엔트로피효율) 저하 | junslee02가 Issue #24에서 실제로 Twin Builder를 돌려 4단계(t=300/380/450/550/600/700s) 계단형 T4·T5 응답을 실측·업로드함(ENGINE_EFF) | junslee02가 실측으로 확인함 |
| Python 코드의 "시나리오1" (real_engine_model_utils.py, 02_fault_scenario_verification.py) | η_b (연소효율) 저하, "실화(Flameout)" | JSSG-2007A §3.2.2.3.5/§3.2.2.6 근거로 채택 | Issue #6(2026-07-04)에서 chestnutbread는 "이 Combustor 컴포넌트 코드에는 η_b 파라미터가 없어 이식 불가"라고 기록. Issue #8/#9에서 독립 η_b 포트가 실제 entity에 추가되어 이식은 가능해졌으나, η_b를 실제로 저하시킨 Twin Builder 실측 스윕은 이 세션 기준으로 아직 업로드되지 않음. Issue #26에서 chestnutbread(작성자 본인이 "병행 세션"이라 표기, 즉 이전 Claude 세션)가 "JSSG-2007A 기준 공식 시나리오1=η_b로 확정"이라고 자체적으로 정리했지만, junslee02는 이 항목에 답하지 않았고, 같은 이슈에서 chestnutbread 스스로 "2, 3번(η_b 배선 확인·재시뮬레이션)은 진행해주시는 대로 기다리겠습니다"라고 적어 재실행이 안 된 상태임을 인정하고 있습니다. |

이번 세션의 판단: Issue #26의 "확정"이라는 단어는 junslee02의 승인이 아니라 이전 세션의 자체 판단이었으므로, 이 README에서는 "확정"이 아니라 "JSSG-2007A 근거로 채택한 설계 판단(팀 확인 대기 중)"으로 표기합니다. junslee02가 실제로 Twin Builder에서 검증한 것은 η_t 저하이지 η_b 저하가 아닙니다.

### 1-2. Supabase 실측 시계열 — 테이블별 실제 패턴 직접 관찰 결과

8개 대형 시계열 테이블(ENGINE_STABLE, ENGINE_EFF, ENGINE_ALL, ENGINE_FUELFAULT, RAMP_STABLE, RAMP_EFF, RAMP_ALL, RAMP_FUEL)을 SQL로 직접 조회했습니다. 이 테이블들에는 고장계수 라벨 컬럼이 없어(스키마 확인 완료), 어떤 시나리오인지는 T4(TIT) 시계열 패턴을 코드의 물리식과 대조해서 이번 세션이 직접 판단한 것이며, 테이블명 자체가 시나리오를 보증하지 않습니다.

| 테이블 | 행 수 / 시간범위 | 관찰된 패턴 | 판단 (확실성) |
|---|---|---|---|
| ENGINE_STABLE | 34,219행, 0~123.8s | T2 일정(~288K, 고도 변화 없음), T4가 0→120s에 500K→1250.0K로 매끄럽게 수렴 후 평탄 | 지상 정지 스풀업만 있는 순수 정상상태 검증런 (고장 없음). 확실성: 높음(데이터 직접 관찰) |
| ENGINE_EFF | 131,981행, 0~443.1s | T2가 288.7→269.3K로 계속 하강(고도 상승 중), T4는 t≈150~294s 동안 정확히 1250.0K 평탄 유지 후 t≈294~306s부터 계단형으로 하강 시작(1250→1238→1224→1194→1165K, t=443s 시점) | η_t 저하 스윕과 패턴 일치(Issue #24 실측 서술의 t=300s 온셋과 부합). 단, 데이터가 443s에서 끊겨 Issue #24 텍스트가 말한 후반 단계(~710K, t=700s)까지는 이 테이블에서 확인 불가. 확실성: 중간(패턴은 뚜렷하나 라벨 컬럼 없이 시간 축으로 추정) |
| ENGINE_ALL | 131,994행, 0~443.1s | ENGINE_EFF와 거의 동일(오차 <0.02K) | 관측 가능한 구간(~443s) 안에서는 η_t 단독 스윕과 사실상 동일 — Issue #24가 설명한 "700~850s 연료계통 고장 추가" 구간은 이 테이블에도 아직 없음(443s에서 절단). 확실성: 중간 |
| ENGINE_FUELFAULT | 94,718행, 0~337.5s | T2 하강(고도 상승) 패턴은 EFF와 유사. T4는 t≈150s부터 337.5s(테이블 끝)까지 1250.0K로 평탄, 하강 없음 | 이 테이블이 실제로 담고 있는 범위(0~337.5s) 안에서는 연료계통 고장이 관측되지 않음. Issue #24 텍스트는 연료계통 고장이 t=700s부터 시작한다고 서술하는데, 이 테이블은 700s에 도달하지 않음 — 이름과 달리 현재 이 테이블에는 고장 구간 데이터가 없는 것으로 판단됨(테이블명을 근거로 "연료계통 고장 데이터"라고 인용하면 안 됨). 확실성: 높음(관측 범위 전체를 직접 확인) |
| RAMP_STABLE/RAMP_EFF/RAMP_ALL | 각각 위 ENGINE_* 테이블과 대응하는 행 수, 고도/마하 램프 입력값 저장 | — | 위 판단과 일관 |
| RAMP_FUEL | 35,199행, 0~1000s | Issue #26(2026-07-23) 시점에는 0행이었으나 현재는 채워져 있음 | Issue #26 항목3(RAMP_FUEL 누락)은 이번 조회 시점 기준 해소된 것으로 보임. 다만 RAMP_FUEL은 0~1000s인데 짝이 되어야 할 ENGINE_FUELFAULT는 0~337.5s까지만 있어 두 테이블의 시간범위가 서로 안 맞습니다 — 재확인 필요 |
| ENGINE_PYTHON_THEORY | 151행 | case_label/fault_factor_fuel/eta_b/far_gap/wf 등 라벨 컬럼 포함, 지상 설계점(comb_ref=1250K) 고정, η_b·faultFactor_fuel 스윕 | Python 이론모델(노이즈 없음) 그대로 — 03_python_theory_dataset_generator.py 재실행 결과와 완전 일치 확인(직접 재실행함) |

보안 권고 (직접 조회 중 확인, 자동조치 안 함): ENGINE_STABLE, RAMP_STABLE, ENGINE_EFF, RAMP_EFF, RAMP_FUEL, ENGINE_ALL, RAMP_ALL, ENGINE_FUELFAULT 8개 테이블은 Row Level Security가 비활성화되어 있어 anon key로 누구나 읽기/쓰기가 가능한 상태입니다. 정책 설계 없이 무작정 RLS를 켜면 접근이 전부 막히므로, 팀 논의 후 적용 여부를 결정해주세요.
### 1-3. 시나리오 1 — 연소실 실화 (Flameout) — η_b 저하 (Python 코드 정의)

| 항목 | 내용 |
|---|---|
| 근거 | JSSG-2007A §3.2.2.3.5 (onset), §3.2.2.6 (full) |
| 물리적 기전 | η_b가 열발생 항에만 작용 — 연료 공급량(FAR_actual)에는 영향 없음 |
| 물리 모델 검증 | Issue #9에서 Combustor entity에 독립 η_b 포트가 실제로 추가됨(entity 코드는 Issue #23에서 원문 확인). real_engine_model_utils.combustor()가 entity 수식과 라인 단위로 일치(02_fault_scenario_verification.py 재실행, 오차 < 1e-9) |
| 실측 검증 상태 | 미완료 — 위 1-1 참조. η_b를 실제로 저하시킨 Twin Builder 스윕 데이터는 아직 없음 |
| 판별 신호(이론모델 기준) | FAR_gap ≡ 0 (연료는 정상 공급), T4(TIT) 단조 감소 |

단계별 η_b 범위 (JSSG onset/full만 문헌 정의, partial은 선형 보간 추정):

| 단계 | η_b 범위 |
|---|---|
| onset | 0.65 ~ 0.80 |
| partial | 0.35 ~ 0.65 (보간 추정) |
| full | 0.05 ~ 0.35 |

### 1-4. 시나리오 2 — 연료계통 고장 (Fuel System Fault) — faultFactor_fuel 저하

| 항목 | 내용 |
|---|---|
| 근거 | Issue #3 — junslee02가 Twin Builder에서 직접 실측(3-case 스윕: 1.0/0.7/0.5) |
| 물리적 기전 | FAR_actual = FAR_demand × faultFactor_fuel — comb_ref(명령 TIT)는 그대로인데 실제 연료 공급만 부족 |
| 실측 결과(Issue #3, junslee02 확정) | faultFactor_fuel 0.7 → T4 1365→1130K(−235K), 0.5 → 1365→965K(−400K). FAR 감소율에 비해 온도 하강폭이 더 가파른 비선형성 확인(연소기 출구온도식이 FAR에 비선형이기 때문) |
| Python 교차검증 | 오차 < 1e-9로 entity 수식과 일치 |
| 핵심 판별 신호 | TIT_error = comb_ref − T4, wf(연료유량) 단조 감소 |

### 1-5. 시나리오 4 — 동시 고장

02_fault_scenario_verification.py 재실행 결과(10개 결정론적 케이스, 오차 < 1e-6): FAR_gap·wf는 faultFactor_fuel만의 함수라 시나리오2와 완전히 같은 값이 나오고, T4가 시나리오2보다 항상 낮다는 점으로만 구분됩니다. (단, 이 "동시고장"은 Python 코드에서는 η_b+faultFactor_fuel 조합이고, junslee02가 Issue #24에서 실제로 돌린 "동시고장"은 η_t+faultFactor_fuel 조합입니다 — 서로 다른 실험입니다.)

### 1-6. 핵심 수식 (스테이션 표기: 하첨자=스테이션, T2=압축기입구 … T5=터빈출구, T4=TIT / 상첨자=지수)

- 압축기: $T_3 = T_2\left(1+\dfrac{1}{\eta_c}\left(\pi_c^{(\gamma_a-1)/\gamma_a}-1\right)\right)$, $P_3=\pi_c P_2$
- - 연소기: $FAR_{demand}=\dfrac{(comb_{ref}/T_3)-1}{LHV/(cp_g T_3)-comb_{ref}/T_3}$, $FAR_{actual}=FAR_{demand}\cdot faultFactor_{fuel}$
  -   $T_4=T_3\cdot\dfrac{1+FAR_{actual}\cdot(LHV\cdot\eta_b)/(cp_g T_3)}{1+FAR_{actual}}$, $P_4=eff\cdot P_3$, $FAR_{gap}=FAR_{demand}-FAR_{actual}$
  -   - 터빈: $T_5=T_4+\Delta T_{comp}\cdot\eta_m\cdot(1+FAR_{actual})$, $P_5=P_4\left(1-\dfrac{1-T_5/T_4}{\eta_t}\right)^{\gamma_g/(\gamma_g-1)}$
   
      - ---

      ## 2. 파라미터표 (Supabase engine_parameters 테이블 직접 조회, 14행 전수)

      | 기호 | 이름 | VHDL값 | 문헌값 | 출처 | 비고 |
      |---|---|---|---|---|---|
      | π_c | 압축비 | 10.55 | 10.55 | Honeywell TPE331-10 브로셔(N61-1491) / FAA TCDS E4WE | 공개 제원과 정확히 일치, entity generic 기본값(9.6)과는 다름(스키매틱 인스턴스 값 사용) |
      | η_comp | 압축기 효율 | 0.85 | 0.80 | Saravanamuttoo 2017 Ch.5(2단 원심압축기 통상범위 0.78~0.82) | 0.85는 인용 범위 상단(0.82)을 초과 — Issue #26에서 "팀 확정값(범위 초과를 인지하고 의도적 유지)"로 처리하기로 함(chestnutbread 코멘트, junslee02 반대 없음) |
      | η_b | 연소 효율 | 1.0(정상) | 0.990 | JSSG-2007A §3.2.2.6 | 정상운전 1.0, 시나리오1에서 1.0→0.2 |
      | FAR | 연료-공기비 | 0.019 | 0.018 | Mattingly 2006 Ch.9 | — |
      | TIT | 터빈입구온도(T4) | 1250K vs 1373K — 미해결, 아래 4장 참조 | — | — | 상세는 4장 참조 |
      | η_t | 터빈효율 | 0.87 | 0.88 | Saravanamuttoo 2017 Ch.7 | Python 코드에서는 상수 고정(고장 스윕 대상 아님) — 1-1 참조 |
      | ṁ | 공기유량 | 3.493 kg/s | 3.493 kg/s | Honeywell 브로셔(7.7 lb/s) | 일치 확인됨 |
      | eff | 연소기 압력손실계수 | 0.96 | — | Mattingly 2006 (통상 3~5% 손실) | η_b와 무관 — 압력에만 작용(2026-07-22 명칭 혼동 해소, Issue #6) |
      | η_m | 터빈 기계효율 | 0.90 | 0.90 | Saravanamuttoo 2017 | Issue #9: "0.98은 표기오류"로 정정 |
      | γ_comb | 연소가스 비열비 | 1.31 | — | 출처 미확인 | 후속 조사 필요 |

      ---
      ## 3. 탐지 성능 — 이번 세션 직접 계산 (재현 가능)

      과거 문서들이 인용해온 "탐지 정확도 100% / ROC-AUC=1.000 / Cohen's d=4.90"은 GitHub Issue #19 텍스트를 그대로 인용한 것이며, 그 근거문서(260707_작업계획_파라미터불일치_이상탐지재평가.md)는 이번 세션에도 마운트되어 있지 않아 원문 대조가 불가능합니다. 아래는 그 숫자를 재인용하지 않고, 이번 세션이 실제 데이터/코드로 직접 계산한 결과입니다.

      ### 3-1. η_t 저하 — 실측 데이터(ENGINE_EFF) 기반, 이번 세션 직접 계산

      관측 가능한 구간(정상 구간 t=200~289s vs 온셋 이후 t≥306s, 둘 다 실측)에서 T4 단일 변수로:

      - 정상 구간: T4 = 1250.000K ± 0.0001K (n=25,282) — 거버너가 사실상 완벽하게 setpoint에 고정
      - - 고장 이후 구간: T4 = 1199.1K ± 30.1K (n=46,271, 이 구간의 심각도는 균일하지 않고 온셋~중간 단계가 섞여 있음)
        - - 단순 임계값 분류(T4 < 1249.99K → 고장) 혼동행렬: TN=25,282, FP=0, FN=3,139, TP=47,909 → 정확도 95.9%, 재현율(고장) 93.9%, 정밀도(고장) 100%
          - - 근사 ROC-AUC(순위기반, 동점 0.5 가중): 약 0.97
            - - Cohen's d ≈ 2.10 (이전 문서가 인용한 4.90과 다름 — 관측 구간이 온셋~중간 단계까지만 포함하고 Issue #24가 서술한 후반 심각 단계(~710K)까지는 이 테이블에 없어서, 완전한 심각도 범위를 다 포함하면 d가 더 커질 가능성이 있음. 이번 계산은 어디까지나 현재 Supabase에 있는 데이터 범위 안에서 나온 값)
             
              - 이 수치는 실측 시계열 안에서 시간축으로 정상/고장을 나눈 것이라, 고도·마하 상승이라는 공통 시간축과 완전히 분리되지 않는 한계가 있습니다(다만 T4는 거버너가 비행조건과 무관하게 setpoint로 고정하는 값이라 다른 신호보다는 이 교란에 덜 민감합니다).
             
              - ### 3-2. η_b/faultFactor_fuel — 이론모델(ENGINE_PYTHON_THEORY) 기반, 몬테카를로 노이즈 주입 후 직접 계산
             
              - real_engine_model_utils.py 그대로 재실행해 지상 설계점(고정 비행조건, comb_ref=1250K)에서 151행(정상 1 + 시나리오1/2/4 각 50)을 재생성하고, 항공용 센서 통상 오차 수준을 가정(열전대 σ=2K, 유량계 상대오차 2%, FAR_gap 절대오차 σ=2×10⁻⁴ — 실측 검증된 값이 아니라 이번 세션이 가정한 값)해 조건당 300회 몬테카를로 노이즈를 주입한 뒤 다항 로지스틱 회귀(4-class: 정상/S1/S2/S4)로 직접 계산:
             
              - | 특징 조합 | 정확도 | macro OvR ROC-AUC |
              - |---|---|---|
              - | T4 단독 | 43.2% | 0.733 |
              - | T4 + wf | 85.2% | 0.953 |
              - | T4 + wf + FAR_gap | 86.6% | 0.953 |
              - | wf + FAR_gap (T4 제외) | 58.4% | 0.763 |
             
              - 노이즈를 5K/5%/5×10⁻⁴로 늘려도 결과는 비슷(정확도 83~84%대). 노이즈가 전혀 없는 이론적 조건(02_fault_scenario_verification.py의 classify_case)에서는 10개 대표 케이스 전원 100% 분리되지만, 이는 결정론적 수식의 완전분리이지 통계적 탐지 성능이 아닙니다. Issue #8이 언급한 "3-class 정확도 83.3%→100%"도 노이즈 없는 조건에서 나온 수치로 보이며, 현실적 센서 노이즈를 가정하면 80%대로 낮아진다는 것이 이번 세션의 정직한 결론입니다.
             
              - 요약 — 확실한 것 vs 추정
             
              - | 주장 | 수준 |
              - |---|---|
              - | faultFactor_fuel 저하 시 T4·FAR·wf가 물리식대로 반응한다 | 확정 (junslee02 Issue #3 실측 + Python 교차검증 <1e-9) |
              - | η_t 저하가 ENGINE_EFF에서 단계적 T4 하강으로 나타난다 | 확정 (junslee02 Issue #24 실측 + 이번 세션 직접 데이터 조회로 재확인) |
              - | η_t 저하 탐지 정확도/AUC/Cohen's d 구체 수치 | 이번 세션 직접 계산값(정확도 95.9%, AUC≈0.97, d≈2.10, 관측 구간 한정) — 과거 인용된 100%/1.000/4.90과는 다름 |
              - | "시나리오1 공식 정의 = η_b" | 팀(이전 세션) 판단, junslee02 미확인 — 확정 아님 |
              - | η_b 저하 탐지 성능 | 노이즈 없는 이론모델에서만 계산 가능(정확도 43~87%, 특징조합별). 실측 데이터 없음 |
             
              - ---
              ## 4. 파생 이슈 — 이번 세션에서 확인한 미해결 항목 (팀 확인 필요)

              [항목1] TIT 설계점 1250K vs 1365K(구 code/) vs 1373K(APISAT 초록) 불일치 — Issue #23의 tit_limiter1 entity generic 기본값은 1250K이고, 이번 세션이 Supabase ENGINE_STABLE/ENGINE_EFF/ENGINE_ALL/ENGINE_FUELFAULT 4개 테이블을 전부 직접 조회한 결과 T4는 예외 없이 정확히 1250.0K에서 평탄화됩니다 — 즉 실측 데이터는 1250K을 지지합니다. 반면 Issue #24 본문(junslee02)은 같은 종류의 검증런을 설명하며 "T4가 1373~1375K에서 TIT limiter setpoint를 정확히 추종한다"고 서술합니다 — 이슈 텍스트와 실제 Supabase 데이터가 서로 다른 숫자를 말하고 있습니다. 이번 세션은 텍스트보다 직접 관찰한 데이터를 우선해 1250K 쪽에 무게를 두지만, 이 자체가 미해결 불일치이므로 팀 확인이 필요합니다.

              [항목2] 시나리오1 정의 이원화 (1-1 참조) — junslee02의 η_b 배선 확인 및 재실행 대기 중.

              [항목3] RAMP_FUEL(0~1000s) vs ENGINE_FUELFAULT(0~337.5s) 시간범위 불일치 — 쌍을 이뤄야 할 두 테이블의 시간범위가 다름.

              [항목4] ENGINE_FUELFAULT 테이블에 연료계통 고장 구간이 관측되지 않음 — 테이블명과 달리 현재 데이터는 전 구간 정상(TIT=1250K 평탄)으로 보임. 재확인/재업로드 필요.

              [항목5] nozzle1 초킹 분기 압력추력항 버그 — p_e:=p_cr 재정의 후 (p_cr-p_e)가 항등적으로 0 (Issue #23, chestnutbread 코드 감사로 확정된 버그). 수정 미반영.

              [항목6] nozzle1 area=0.3m² 비현실성 — 질량연속성 기준 역산값 ≈0.0096m²와 31배 차이. 실제 스키매틱 값 미확인.

              [항목7] turbine1이 gearbox1/propeller1 부하와 열역학적으로 분리됨 — 축 결합 스키매틱 확인 필요(Issue #23).

              [항목8] K_τ(프로펠러 부하토크계수) = 0.16 — chestnutbread가 정격 축출력 재현을 목표로 자체 역산한 값(재현율 99.98%)이며, junslee02의 Twin Builder 실측 대조는 아직 없음.

              [항목9] Supabase RLS 비활성 8개 테이블 — 보안 권고 사항, 팀 논의 후 정책 적용 필요(위 1-2 참조).

              ---

              ## 5. 핵심 근거 문헌

              | 문헌 | 활용 |
              |---|---|
              | Saravanamuttoo et al., Gas Turbine Theory 7th ed. (2017) | π_c, η_c, η_t 범위 |
              | Mattingly, Elements of Gas Turbine Propulsion (2006) | FAR, ΔP_b |
              | JSSG-2007A (2007) | η_b, 실화 단계 정의 |
              | Honeywell TPE331-10 브로셔(N61-1491-000-000) | π_c, ṁ, N_gg, N_prop |
              | FAA TCDS E4WE Rev.34 | 기어비(GR) |

              ---

              *본 문서는 2026-07-24, GitHub 이슈 원문 전수 확인 + Supabase 직접 SQL 조회 + 로컬 Python 코드 재실행을 근거로 독립 재작성되었습니다. 이전 세션이 남긴 결론(예: "시나리오1=η_b 확정", "탐지정확도 100%")은 그대로 인용하지 않고 원문 대조로 재검증했으며, 확인되지 않는 부분은 4장에 미해결 항목으로 남겼습니다.*
              
