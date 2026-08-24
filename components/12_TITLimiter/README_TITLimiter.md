# 12. TIT Limiter (터빈 입구 온도 제한)

**역할:** 터빈입구온도(TIT, T4)를 안전 한계 이내로 제한하는 PI 제어기. Ng Governor와 함께 min_select1에 입력되어, 두 제어기 중 더 낮은 출력이 실제 comb_ref(연소기 목표온도)로 사용됩니다(min-select 구조). 이 저장소의 TIT 설계점 논쟁(1250K vs 1373K)의 핵심 컴포넌트입니다.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | fb(피드백=T4 실측), clamp_val, clamp_active |
| 출력 | out_val |
| 연결 | tit_limiter1.out_val -> min_select1.in2 -> combustor1.comb_ref |

## 핵심 파라미터 (근거: GitHub Issue #31, 2026-07-29 컴포넌트 코드 공유)

| 파라미터 | 기호 | 값 | 설명 |
|----------|----|----|------|
| 비례 게인 | Kp | 0.3 | - |
| 적분 게인 | Ki | 0.02 | - |
| **온도 설정값(entity generic 기본값)** | **setpoint** | **1250.0 K** | **엔티티 선언의 기본값. 실제 인스턴스에서 override 가능(아래 참조)** |
| 출력 하한 | out_min | 500.0 | - |
| 출력 상한 | out_max | 1400.0 | - |

## 지배 방정식 (요약, anti-windup 포함 PI 제어기)

```
err = setpoint - fb
raw_out = Kp * err + integ
out_val = clamp(raw_out, out_min, out_max)
```

## TIT 설계점 1250K vs 1373K — 근거와 남은 확인 필요 사항

이 항목은 저장소 최상위 README.md 4장 [항목1]에 정리된 미해결 사항과 직결됩니다. 2026-08-24 재검토로 아래를 정리합니다.

1. **entity generic 기본값은 1250.0K가 맞습니다** (Issue #31 원문 코드 재확인 완료). 이는 VHDL 엔티티 선언 자체에 박힌 기본값이며, 스키매틱 인스턴스에서 별도로 setpoint를 지정하지 않으면 이 값이 적용됩니다.
2. **Supabase 데이터 근거**: 최상위 README.md가 직접 SQL로 조회한 결과, 접미사 없는 구버전 테이블(ENGINE_STABLE 등)은 T4가 1250.0K에서 평탄화되고, **`_1373K` 접미사가 붙은 4개 테이블(ENGINE_STABLE_1373K/EFF_1373K/FUELFAULT_1373K/ALL_1373K)은 T4 max=1372.99...K(≈1373K)이며 행수도 APISAT 논문 Table 4와 정확히 일치**합니다.
3. **구조적 설명(이번 문서에서 추가 근거로 제시)**: min_select1은 ng_governor1과 tit_limiter1의 출력 중 더 낮은 값을 combustor1.comb_ref로 전달하는 구조입니다. 따라서 `_1373K` 테이블은 스키매틱 인스턴스에서 tit_limiter1의 setpoint를 1373으로 **override**하여 실행한 결과로 판단하는 것이 구조적으로 타당합니다. 이 1373K는 매뉴얼상 TIT(T4) 한계 1100 degC = 1373.15K(TSG134 §1)에 해당하는 값이며, 설계점 comb_ref=1365K는 이 한계 대비 8.15K 여유를 둔 값입니다(근거: TPE33110_Research_Parameters_v3.xlsx 시트5).
4. **아직 팀 확인이 필요한 부분**: 위 3번의 "override" 설명은 min_select1의 회로 구조상 합리적인 추론이지만, 실제 스키매틱 파일에서 setpoint override 배선이 존재하는지를 이번 문서화 세션에서 직접 눈으로 확인하지는 못했습니다. 또한 구버전(접미사 없는) 테이블이 왜 아직도 1250K로 남아 있는지(재시뮬레이션이 언제 이뤄졌는지)도 여전히 팀 확인이 필요합니다.

## 미해결/확인 필요 사항

- 위 4번 참조.
- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다.

---
*이 문서는 2026-08-24, GitHub Issue #31 원문 소스코드 및 최상위 README.md 4장/6장을 근거로 작성되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31)*
