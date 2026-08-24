# 10. Atmospheric Properties (고도·마하수에 따른 대기 상태량)

**역할:** 대기 온도·압력으로부터 비행속도(V)와 공기밀도(rho)를 계산하는 보조 유틸리티 컴포넌트. Propeller의 추력 계산에 필요한 rho를 제공합니다.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | mach, t_amb, p_amb |
| 출력 | V(비행속도, m/s), rho(공기밀도, kg/m^3) |
| 연결 | Inlet(t_amb, p_amb) -> AtmProps -> Propeller(V, rho) |

## 핵심 파라미터 (근거: GitHub Issue #31, 2026-07-29 컴포넌트 코드 공유)

| 파라미터 | 기호 | 값 | 설명 |
|----------|----|----|------|
| 공기 비열비 | gamma | 1.4 | Inlet 컴포넌트와 동일 |
| 공기 기체상수 | r | 287.04 J/(kg*K) | - |

## 지배 방정식

```
V = mach * sqrt(gamma * r * t_amb)
rho = p_amb / (r * t_amb)
```

## 근거 검증

- 이상기체 상태방정식(rho=p/(rT))과 음속식(a=sqrt(gamma*r*T))을 그대로 사용하는 표준 관계식으로, 별도 캘리브레이션 파라미터가 없어 검증 이슈가 발생할 여지가 적습니다.

## 미해결/확인 필요 사항

- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다. 추후 팀 확인 및 이미지 추가가 필요합니다.

---
*이 문서는 2026-08-24, GitHub Issue #31 원문 소스코드를 근거로 작성되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31)*
