# 09. FuelTank (연료 공급 계통)

**역할:** 연료 소모에 따른 탱크 내 연료 잔량(fuel_remain)을 적분하고, 상/하한 이탈 시 연료 공급을 차단하는 단순 저장조 모델.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | engine_conn(연료 흐름 단자, mdot_fuel) |
| 출력 | fuel_remain(잔량 비율), fuel_rate(연료 소모율) |
| 연결 | Combustor(fuel) <-> FuelTank(engine_conn) |

## 핵심 파라미터 (근거: GitHub Issue #31, 2026-07-29 컴포넌트 코드 공유)

| 파라미터 | 기호 | 값 | 설명 |
|----------|----|----|------|
| 초기 연료 잔량 | fuel_remain0 | 1.0 | 탱크 가득 참(100%) |
| 연료 밀도 | rho | 719.0 kg/m^3 | 가솔린 밀도 |
| 탱크 총 용적 | v | 0.015 m^3 | - |
| 하한 임계값 | fuel_limit_low | 0.1 | 이 이하로 내려가면 공급 차단 |
| 상한 임계값 | fuel_limit_high | 1.1 | - |

## 지배 방정식 (요약)

```
fuel_remain_intern'dot = (1/(rho*v)) * mdot_fuel   (fuel_limit_low < 잔량 < fuel_limit_high 구간에서만)
fuel_remain = fuel_remain_intern
```

## 근거 검증

- 이 컴포넌트는 순수 저장조(적분기) 모델로, 압력·온도 계열과 직접 연동되지 않습니다. 저장소 최상위 README.md 1-2절의 관찰(압력 계열이 고장 시나리오와 무관하게 baseline과 동일)과 구조적으로 부합합니다.

## 미해결/확인 필요 사항

- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다. 추후 팀 확인 및 이미지 추가가 필요합니다.
- fuel_remain0/rho/v 값이 실제 TPE331-10 연료탱크 제원과 대조 검증된 적은 아직 없습니다(팀 확인 필요).

---
*이 문서는 2026-08-24, GitHub Issue #31 원문 소스코드를 근거로 작성되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31)*
