# 07. Propeller (프로펠러 부하 모델)

**역할:** 감속기어(Gearbox)로부터 전달받은 회전력을 받아 반작용 토크와 추력을 발생시키는 프로펠러 부하 모델. 저속(V<=V_th)에서는 정지 추력(static thrust) 상관식을, 고속에서는 운동량 이론 기반 추력식을 사용하는 2영역(piecewise) 모델.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | V(비행속도), pitch_factor, rho(공기밀도) |
| 출력 | thrust, mech_rv(회전단자) |
| 연결 | Gearbox(prop_shaft) -> Propeller |

## 핵심 파라미터 (근거: GitHub Issue #31, 2026-07-29 컴포넌트 코드 공유)

| 파라미터 | 기호 | 값 | 설명 |
|----------|----|----|------|
| 프로펠러 직경 | D | 2.74 m | - |
| 디스크 면적 | A | 5.90 m^2 | - |
| 프로펠러 효율 | eta_p | 0.82 | 고속(V>V_th) 영역 |
| 디스크 효율 | eta_disk | 0.80 | 저속(V<=V_th) 영역 |
| 저속/고속 전환 임계속도 | V_th | 10.0 m/s | - |
| 부하토크계수 | K_tau | 0.0512 | tau = pitch_factor * K_tau * omega^2 |

## 지배 방정식

```
tau = pitch_factor * K_tau * omega^2

if V > V_th:
  thrust = eta_p * (tau * omega) / (V + 0.001)
else:
  thrust = eta_disk * (2 * rho * A * (tau * omega)^2)^(1/3)
```

## 근거 검증 및 상충 이력

- K_tau 값 정정 이력: 저장소 최상위 README.md 4장 [항목8]에 따르면, 과거 문서상 K_tau=0.16으로 기록된 적이 있었으나 이는 chestnutbread가 정격 축출력 재현을 목표로 자체 역산한 미검증 메모였습니다. Issue #31에 공개된 실제 propeller1 인스턴스 코드를 직접 확인한 결과 K_tau=0.0512가 맞으며, 이 값과 gearbox GR=26.229, eta_gear=0.98을 함께 사용해 재검증한 결과 N_prop 계산값이 1590.99 RPM으로 FAA TCDS Table1의 1,591 RPM과 오차 0.013 RPM 이내로 일치했습니다. 이 문서는 K_tau=0.0512를 최종값으로 채택합니다(2026-08-24 재확인).
- junslee02의 Twin Builder 실측 대조는 이 문서 작성 시점 기준 아직 없어(추후 팀 확인 필요), 위 검증은 Python 역계산(propeller_gearbox_model.py) 기준입니다.

## 미해결/확인 필요 사항

- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다. 추후 팀 확인 및 이미지 추가가 필요합니다.

---
*이 문서는 2026-08-24, GitHub Issue #31 원문 소스코드 및 최상위 README.md 4장을 근거로 작성되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31)*
