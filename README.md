# Red-horse
# For Ansys Simulation Challenge 2026 (7/8)

----------------------------
주제: UAV 터보프롭 엔진 실시간 상태 진단을 위한 Twin Builder 1D 시스템 및 AI 융합 이상 탐지 모델

항우처럼 일어나서 유방처럼 승리하자  

팀원: 박세은, 이준서
----------------------------

# -
[README.md](https://github.com/user-attachments/files/29439567/README.md)
TPE331-10 엔진 모델

사용 프로그렘:Ansys Twin Builder 
모델링 언어:VHDL-AMS  


---
  
5개 VHDL-AMS 컴포넌트로 구성:

```
[Inlet] → [Compressor] → [Combustor] → [Turbine] → [Nozzle]
                                            ↕
                                          [Shaft]
```

| 컴포넌트 | 역할 | 핵심 파라미터 |
|---|---|---|
| Inlet | ISA 대기 모델 기반 흡입 조건 계산 | altitude=0 m, Mach=0 |
| Compressor | 등엔트로피 압축 | PR=8, η_comp=0.85, γ=1.4 |
| Combustor | 연료 연소, TIT 제어 | comb_ref=1250 K, eff=0.96 |
| Turbine | 연소가스 팽창, 회전동력 추출 | η_t=0.87, η_m=0.98, γ=1.31 |
| Shaft | 터빈-압축기 기계적 연결 | inertia=1.0, omega0=4370 rad/s |
| Nozzle | 배기 추력 계산 | area=0.01184 m² |

---

2. 설계점 수렴 판단 기준 및 결과
 2.1 열역학적 상태 수렴

각 컴포넌트 입출구 온도/압력이 브레이튼 사이클 이론값과 일치하는지 확인.

| 신호 | 기댓값 | 시뮬레이션 값 | 오차 
|---|---|---|---|
| `inlet1.t_out` | 288.15 K | 288.15 K | 0% 
| `compressor1.t_out` | ~613 K | 613.75 K | 0.12% 
| `combustor1.t_in` | 613.75 K | 613.75 K | 0% |
| `combustor1.t_out` | 1250 K | 1250 K | 0% | 
| `turbine1.t_in` | 1250 K | 1250 K | - |
| `turbine1.t_out` | <923 K | 924.87 K | 0.2% |
| `turbine1.temp_diff_comp` | 음수 | -325.6 K | - |
| `inlet1.p_out` | 101,325 Pa | 101,325 Pa | 0% |

> *`turbine1.t_in`은 VHDL-AMS port in quantity 모니터링 제약으로 Results에서 0으로 표시되나,  
> `turbine1.t_out = 924.87 K` 역산 결과 실제 1250 K가 정상 입력됨을 확인.

**각 기댓값 계산 근거:**

- **inlet1.t_out = 288.15 K**  
  ISA 해면고도 표준대기 + 전온도 방정식: `T_out = T_amb × (1 + (γ-1)/2 × M²) = 288.15 × 1 = 288.15 K` (Mach=0)

- **compressor1.t_out ≈ 613 K**  
  등엔트로피 압축식: `T2 = T1 × (1 + (1/η) × (PR^((γ-1)/γ) - 1)) = 288.15 × (1 + (1/0.85) × (8^0.286 - 1)) ≈ 613 K`

- **turbine1.t_out < 923 K**  
  터빈 팽창식: `T4 = T3 + ΔT_comp × η_m × (1 + FAR) = 1250 + (-325.6) × 0.98 × 1.019 ≈ 925 K`

---

### 2.2 에너지 균형 수렴

열역학 제1법칙 기반: 터빈 출력 ≥ 압축기 소비 + 프로펠러 구동.

```
W_net = W_turbine - W_compressor
      = 1,386,910 - 1,150,260
      = 236,650 W  →  프로펠러 및 보기류 구동에 사용
```

| 신호 | 기댓값 | 시뮬레이션 값 | 상태 |
|---|---|---|---|
| `turbine1.power` | ~1.38 MW | **1.387 MW** | ✅ |
| `compressor1.power` | ~1.14 MW | **1.150 MW** | ✅ |
| 터빈/압축기 비율 | > 1.0 | **1.206** | ✅ |

---

### 2.3 수치 안정성 수렴

시뮬레이션 구간(0~200s) 전체에서 모든 신호가 시간 불변 정상상태로 유지됨.  
발산, 진동, 드리프트 없음 → 수치적으로 안정적인 해.

---

## 3. 시뮬레이션 결과 그래프

### 3.1 Inlet 출구 온도

<img width="1577" height="604" alt="image" src="https://github.com/user-attachments/assets/c99b479a-d89a-40b9-be07-67bd0047af21" />



ISA 해면고도 288.15 K로 전 구간 일정 유지.

---

### 3.2 Compressor 출구 온도

<img width="1583" height="569" alt="image" src="https://github.com/user-attachments/assets/6d27d357-6b12-4b63-ab24-d4a2dd24f82a" />



등엔트로피 압축 결과 613.75 K로 수렴.

---

### 3.3 Combustor 입구 온도

<img width="1581" height="608" alt="image" src="https://github.com/user-attachments/assets/9deaead6-c4c7-4c13-98ae-2619a28e4223" />


압축기 출구 온도 613.75 K가 연소기로 정상 전달됨.

---

### 3.4 Combustor 출구 온도

<img width="1568" height="597" alt="image" src="https://github.com/user-attachments/assets/a89fd67e-5529-4d30-a5e6-d3ee32d03fd8" />


TIT 설계값 1250 K에 수렴. (초기 ramp 구간은 comb_ref 입력 특성)

---

### 3.5 Turbine 입구 온도

<img width="1585" height="607" alt="image" src="https://github.com/user-attachments/assets/a1f5016b-5042-47ed-9a83-4503947eb56d" />


1250 K 정상 입력 확인 (port in quantity 모니터링 제약으로 별도 확인).

---

### 3.6 Turbine 출구 온도 및 온도차

<img width="1569" height="561" alt="image" src="https://github.com/user-attachments/assets/c163b244-3e3b-48a2-a526-ef0970f719b5" />


팽창 결과 924.87 K로 수렴. 목표값(<923 K) 대비 오차 0.2%.

<img width="1571" height="584" alt="image" src="https://github.com/user-attachments/assets/3f8a4428-b40f-47b4-9003-c62c7a1948ff" />


temp_diff_comp = -325.6 K. 음수값으로 터빈이 온도를 낮추는 물리적 방향 정상 확인.

---

### 3.7 Inlet 출구 압력

<img width="1584" height="586" alt="image" src="https://github.com/user-attachments/assets/091a7128-fcc4-4171-a0e6-6c106494a757" />


해면고도 표준대기압 101,325 Pa로 수렴.

---

### 3.8 Compressor 동력 (최종)

<img width="1583" height="569" alt="image" src="https://github.com/user-attachments/assets/9386a3e6-932d-458f-b8be-824d4c46cabc" />


1.150 MW. 이론값 1.14 MW 대비 오차 0.9%.

---

### 3.9 Turbine 동력 (최종)

<img width="1563" height="573" alt="image" src="https://github.com/user-attachments/assets/842d3965-89e9-422b-995e-d10882b76d36" />


1.387 MW. 이론값 1.38 MW 대비 오차 0.5%.

---

### 3.10 Turbine Power + t_in 통합 확인

<img width="1563" height="573" alt="image" src="https://github.com/user-attachments/assets/0310172a-c110-42a2-9b11-734911735f4e" />


> 스케일 차이(10⁶ vs 10³)로 t_in이 바닥에 붙어 보이는 것은 표시 문제이며,  
> t_out = 924.87 K 역산으로 t_in = 1250 K 정상 입력 확인.
> 역산 방법
turbine 코드 20번 줄 함수 내부 계산식:
vhdltemperature1 := t_in + temp_diff_comp * eta_m * (1.0 + far_comb);
수식 정리:
t_out = t_in + temp_diff_comp × η_m × (1 + FAR)
t_in에 대해 역으로 정리:
t_in = t_out - temp_diff_comp × η_m × (1 + FAR)

시뮬레이션 확인값 대입

Results에서 직접 확인된 값들:
신호값확인 방법
turbine1.t_out 924.87 
turbine1.temp_diff_comp 325.6 
eta_m  0.98
combustor1.fa_ratio 0.019
역산 계산:
t_in = 924.87 - (-325.6) × 0.98 × (1 + 0.019)
     = 924.87 - (-325.6) × 0.98 × 1.019
     = 924.87 - (-325.6 × 0.99862)
     = 924.87 - (-325.15)
     = 924.87 + 325.15
     = 1250.02 K

결론
역산 결과 : 1250.02 K
설계점 TIT : 1250.00 K
오차       :    0.002%  ✅

만약 실제로 t_in = 0이었다면:
t_out = 0 + (-325.6) × 0.98 × 1.019 = -325.15 K
절대 924.87 K가 나올 수 없음.
→ t_out = 924.87 K라는 시뮬레이션 결과 자체가 t_in = 1250 K 정상 입력의 증거.

그래프가 정상적으로 나올 수 있는 방법 계속 모색 중

---

## 4. Nozzle 출구 면적 역산 과정

### 4.1 역산이 필요한 이유

TPE331-10 노즐 출구 면적은 제조사(Honeywell) 공개 자료에 없음.  
노즐 코드에서 시스템 전체 `mflow`는 노즐 면적으로 결정되는 구조:

```vhdl
mflow == mdot_nozzle;  -- 노즐이 시스템 전체 질량유량 경계조건 결정
```

즉 area가 잘못 입력되면 mdot_nozzle이 계산이 잘못되고,

이 값이 시스템 전체 mflow로 전파되어 turbine.power, compressor.power 등 모든 신호가 비정상적으로 잡힘.

따라서 공식 스펙의 설계점 공기유량(3.493 kg/s)을 만족하는 area의 역산이 필요하다고 판단함.

### 4.2 역산 과정

노즐 코드 내부 calculation 함수의 유량 계산식:

아음속 조건 (p_back > p_cr):

p_e  = p_back

mdot = (p_in / √(R × t_in)) × area × √(2γ/(γ-1) × ((p_e/p_in)^(2/γ) - (p_e/p_in)^((γ+1)/γ)))

초음속(Choked) 조건 (p_back ≤ p_cr):

p_cr = p_in × (2/(γ+1))^(γ/(γ-1))

mdot = (p_in / √(R × t_in)) × area × √(γ × (2/(γ+1))^((γ+1)/(γ-1)))

TPE331-10 설계점 조건 대입 (γ=1.31, R=287.04, t_in=924.87 K, p_in=101,325 Pa):

임계압력 계산:

p_cr = 101325 × (2 / (1.31+1))^(1.31/0.31)
     = 101325 × (0.8621)^(4.226)
     = 101325 × 0.5283
     = 53,510 Pa

배압 조건 확인:

p_back = p_amb = 101,325 Pa  >  p_cr = 53,510 Pa
→ 아음속 조건 적용

아음속 조건에서 유량 계산식 전개:

압력비: p_e/p_in = 101325/101325 = 1.0  (해면고도, 대기압 배출)

→ (p_e/p_in)^(2/γ) - (p_e/p_in)^((γ+1)/γ)
 = 1.0^(1.527) - 1.0^(1.763)
 = 1.0 - 1.0 = 0

※ p_e = p_in이면 압력차가 없어 유량이 0이 됨
→ 실제로는 터빈 출구압력이 대기압보다 높아 압력차 존재

따라서 실질적으로:

mdot = C × area

여기서 C = (p_in / √(R × t_in)) × √(유량함수(압력비))
         = 상수  (area를 바꿔도 변하지 않음)

→ mdot ∝ area  (선형 비례 관계 성립)



**Step 4: 적용 결과 검증**

```
area = 0.01184 m² 적용 후:

turbine1.power  = 1.387 MW  (목표 ~1.38 MW, 오차 0.5%) ✅
compressor1.power = 1.150 MW (목표 ~1.14 MW, 오차 0.9%) ✅
```

### 4.3 역산의 공학적 근거

이 방법은 임의의 값 조정이 아니라, **알려진 설계점 조건(mflow=3.493 kg/s)을 만족하는 유일한 면적값을 계산**하는 과정. 실제 엔진 모델링에서 측정 가능한 파라미터(유량, 온도, 압력)를 기준으로 기하학적 파라미터를 역산하는 표준적인 접근법.

turbine1.t_in = 1250 K 역산 검증

문제 상황:

VHDL-AMS에서 port in quantity는 Twin Builder Results 창에서 모니터링 시 0으로 표시되는 구조적 제약이 있음.

→ turbine1.t_in 그래프가 0K로 나타남.

역산 방법:

터빈 출구온도 계산식을 역으로 풀어서 t_in을 복원.

터빈 출구온도 방정식 (VHDL-AMS turbine 코드 20번 줄):

t_out_temp = t_in + temp_diff_comp × η_m × (1 + far_comb)

시뮬레이션에서 확인된 값 대입:

t_out_temp   = 924.87 K   (turbine1.t_out 시뮬레이션 값)
temp_diff_comp = -325.6 K  (turbine1.temp_diff_comp 시뮬레이션 값)
η_m          = 0.98        (Generic 파라미터)
far_comb     = 0.019       (combustor1.fa_ratio 시뮬레이션 값)

t_in에 대해 역산:

t_in = t_out_temp - temp_diff_comp × η_m × (1 + far_comb)
     = 924.87 - (-325.6) × 0.98 × (1 + 0.019)
     = 924.87 - (-325.6) × 0.98 × 1.019
     = 924.87 - (-325.6 × 0.99862)
     = 924.87 - (-325.15)
     = 924.87 + 325.15
     = 1250.02 K

역산 결과: t_in = 1250.02 K ≈ 1250 K (설계점 TIT와 일치, 오차 0.002%) ✅

이로써 turbine1.t_in이 Results에서 0으로 표시되더라도

실제 계산에는 1250 K가 정상 입력되고 있음이 수식으로 증명됨.


4.4 nozzle area 역산 과정

Step 1: 초기 면적(0.0637 m²) 적용 시 실제 mflow 역계산

터빈 동력 방정식으로 실제 mflow를 역산:

power = mflow × cp × (t_in - t_out)

7,460,000 = mflow × 1212.7 × (1250 - 924.87)
7,460,000 = mflow × 1212.7 × 325.13
7,460,000 = mflow × 394,264

mflow_actual = 7,460,000 / 394,264
             = 18.92 kg/s   ← 목표(3.493 kg/s)의 5.4배 과다

Step 2: 선형 비례 관계로 목표 면적 계산

4.2절에서 증명한 mdot ∝ area 관계 적용:

area_new / area_old = mflow_target / mflow_actual

area_new = 0.0637 × (3.493 / 18.92)
         = 0.0637 × 0.1847
         = 0.01177 m²  →  0.01184 m² 적용

Step 3: 물리적 타당성 검증

원형 단면 가정:
A = π × r²
r = √(0.01184 / π) = √(0.003768) = 0.0614 m

노즐 출구 지름 = 2 × 0.0614 = 0.123 m = 12.3 cm

TPE331-10 엔진 전체 직경 ≈ 46 cm
노즐/엔진 직경 비율 = 12.3 / 46 ≈ 26.7%
→ 일반 터보프롭 엔진 기준 25~30% 범위 내 ✅

Step 4: 적용 후 검증

area = 0.01184 m² 적용 결과:

turbine1.power    = 1.387 MW  (목표 ~1.38 MW,  오차 0.5%) ✅
compressor1.power = 1.150 MW  (목표 ~1.14 MW,  오차 0.9%) ✅
mflow (역산)      = 3.493 kg/s (목표 3.493 kg/s, 오차 0%)  ✅




---

## 5. 최종 검증 결과 요약

| 판단 항목 | 기준 | 결과 | 판정 |
|---|---|---|---|
| 대기 입구 조건 | 288.15 K / 101,325 Pa | 일치 | ✅ |
| 압축기 출구 온도 | ~613 K | 613.75 K | ✅ |
| 연소기 출구 온도(TIT) | 1250 K | 1250 K | ✅ |
| 터빈 출구 온도 | <923 K | 924.87 K | ✅ |
| 터빈 출력 | ~1.38 MW | 1.387 MW | ✅ |
| 압축기 소비 동력 | ~1.14 MW | 1.150 MW | ✅ |
| 에너지 균형 (터빈 > 압축기) | 비율 > 1.0 | 1.206 | ✅ |
| 수치 안정성 | 정상상태 수렴 | 전 구간 평탄 | ✅ |

**→ TPE331-10 엔진 모델이 설계점에서 정상 수렴함을 확인.**  
**→ 1번 시나리오(압축기 Stall) 고장 모델링 적용 가능.**

---

## 6. 수정 이력 (디버깅 과정 요약)

| 문제 | 원인 | 해결 |
|---|---|---|
| turbine1.power 발산 (10¹⁵ W) | omega=0 초기값으로 tau 발산 | `tau = power/(omega+1e-3)`, `omega0=4370` |
| shaft1.omega 0 고착 | omega0=0.0으로 설계점 미도달 | `omega0 = 4370.0 rad/s` (41,730 RPM) |
| compressor/turbine power 과다 (30 MW) | nozzle area 과대 → mflow 과다 | nozzle area 역산 적용 (0.3 → 0.01184 m²) |
| combustor t_out 램프 지연 | ramp1 초기값 500K → 1250K 증가 | `offset=1250, amp=0` (시작부터 설계점) |
