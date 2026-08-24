# 13. Min Select (거버너·제한기 출력 중 최솟값 선택기)

**역할:** ng_governor1(Ng 회전수 제어)과 tit_limiter1(TIT 제한)의 출력 중 더 낮은 값을 선택해 combustor1.comb_ref로 전달하는 최소값 선택기(min-select) + anti-windup 로직. 이 컴포넌트가 저장소의 TIT 설계점(1250K vs 1373K) 논의의 구조적 핵심입니다.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | in1(ng_governor1.out_val), in2(tit_limiter1.out_val) |
| 출력 | out_val(-> combustor1.comb_ref), clamp_val_1/2, clamp_active_1/2 |
| 연결 | NgGovernor, TITLimiter -> MinSelect -> Combustor |

## 핵심 파라미터

이 컴포넌트는 별도의 generic 파라미터가 없는 순수 로직(조합 논리) 컴포넌트입니다.

## 지배 방정식

```
if in1 <= in2:
  out_val = in1          -- Ng governor가 더 낮음 -> Ng 제어가 우선(TIT limiter는 clamp_active=1로 대기)
  clamp_active_1 = 0
  clamp_active_2 = 1
else:
  out_val = in2           -- TIT limiter가 더 낮음 -> TIT 제어가 우선(Ng governor는 clamp_active=1로 대기)
  clamp_active_1 = 1
  clamp_active_2 = 0

clamp_val_1 = out_val
clamp_val_2 = out_val
```

## 근거 및 의의

- 저장소 최상위 README.md의 TIT 설계점 서술(6장)에 따르면, comb_ref는 상수가 아니라 이 min_select1이 매 시점 계산하는 값입니다. 즉 "TIT가 1250K냐 1373K냐"라는 질문은 사실 "이 시점에 out_val=in1(Ng governor)이었는가 out_val=in2(TIT limiter)이었는가"라는 질문과 동치입니다.
- tit_limiter1의 entity generic 기본값이 setpoint=1250.0K이므로(12_TITLimiter 문서 참조), 스키매틱에서 override 없이 두 컴포넌트가 그대로 연결되어 있다면 정상 운전 구간에서는 TIT limiter가 comb_ref를 지배하게 됩니다.
- 상세 근거와 아직 남은 미해결 사항(override 실존 여부 미확인 등)은 12_TITLimiter/README_TITLimiter.md 및 최상위 README.md 4장 [항목1]을 참조하십시오.

## 미해결/확인 필요 사항

- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다.
- 정상 운전 전 구간에서 실제로 어느 쪽(in1/in2)이 선택되고 있는지 Supabase 데이터로 직접 트레이스한 기록은 아직 없습니다(팀 확인 필요).

---
*이 문서는 2026-08-24, GitHub Issue #31 원문 소스코드를 근거로 작성되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31)*
