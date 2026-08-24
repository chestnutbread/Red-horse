# 11. Ng Governor (가스제너레이터 회전수 제어)

**역할:** 가스제너레이터(Ng) 회전수를 목표 setpoint로 유지하는 PI 제어기. TIT Limiter와 함께 min_select1에 입력되어, 두 제어기 중 더 낮은 출력이 실제 연소기 목표온도(comb_ref)로 사용됩니다(min-select 구조).

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | setpoint, fb(피드백), clamp_val, clamp_active |
| 출력 | out_val |
| 연결 | ng_governor1.out_val -> min_select1.in1 |

## 핵심 파라미터 (근거: GitHub Issue #31, 2026-07-29 컴포넌트 코드 공유)

| 파라미터 | 기호 | 값 | 설명 |
|----------|----|----|------|
| 비례 게인 | Kp | 0.15 | - |
| 적분 게인 | Ki | 0.02 | - |
| 출력 하한 | out_min | 500.0 | - |
| 출력 상한 | out_max | 1400.0 | - |

## 지배 방정식 (요약, anti-windup 포함 PI 제어기)

```
err = setpoint - fb
raw_out = Kp * err + integ
out_val = clamp(raw_out, out_min, out_max)
(포화 시 적분 정지, min_select에 의해 clamp_active면 clamp_val로 적분 강제 추종 - anti-windup)
```

## 근거 검증

- 이 컴포넌트는 TIT Limiter(12번, 동일한 PI 구조)와 구조적으로 완전히 동일한 클래스이며, min_select1(13번)을 통해 서로 anti-windup 커플링됩니다. 세 컴포넌트(NgGovernor, TITLimiter, MinSelect)는 반드시 함께 이해해야 하는 3-컴포넌트 제어 루프입니다. 상세 근거는 최상위 README.md의 TIT 설계점 서술을 참고하십시오.

## 미해결/확인 필요 사항

- setpoint의 실제 override 값(Ng 목표 회전수)은 스키매틱 인스턴스 파라미터로, 이 문서 작성 시점 기준 저장소에 별도 확인 자료가 없습니다(팀 확인 필요).
- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다.

---
*이 문서는 2026-08-24, GitHub Issue #31 원문 소스코드를 근거로 작성되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31)*
