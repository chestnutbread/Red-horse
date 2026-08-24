# 06. Gearbox (감속 기어박스)

**역할:** 가스제너레이터 축(gg_shaft)의 고속 회전을 프로펠러 축(prop_shaft)에 맞는 저속·고토크로 감속 전달.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | gg_shaft (rotational_velocity terminal) |
| 출력 | prop_shaft (rotational_velocity terminal) |
| 연결 | Shaft(gg_shaft) -> Gearbox -> Propeller(prop_shaft) |

## 핵심 파라미터 (근거: GitHub Issue #31, 2026-07-29 컴포넌트 코드 공유)

| 파라미터 | 기호 | 값 | 설명 |
|----------|----|----|------|
| 기어비 | GR | 26.229 | omega_prop = omega_gg / GR |
| 기어 효율 | eta_gear | 0.98 | tau_prop = tau_gg * GR * eta_gear |

## 지배 방정식

```
omega_prop = omega_gg / GR
tau_prop = tau_gg * GR * eta_gear
```

## 근거 검증

- GR=26.229는 FAA TCDS E4WE 기어비(41,730 / 1,591 = 26.229)와 일치 확인됨 (검증 근거: TPE33110_Research_Parameters_v3.xlsx 시트5).
- 실측 검증: N_prop 계산값 1590.99 RPM vs TCDS Table1 1,591 RPM (오차 0.013 RPM) — 저장소 최상위 README.md 4장 [항목8] 참조.

## 미해결/확인 필요 사항

- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다. 추후 팀 확인 및 이미지 추가가 필요합니다.

---
*이 문서는 2026-08-24, GitHub Issue #31 원문 소스코드를 근거로 작성되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31)*
