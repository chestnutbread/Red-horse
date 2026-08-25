# 08. Nozzle (배기 노즐 및 추력 계산)

**역할:** 터빈 출구 유동을 받아 배기 질량유량, 배기속도, 추력을 계산. 아음속(subsonic) 배압조건과 초킹(choked) 조건을 분기 처리하는 준1차원 등엔트로피 노즐 모델.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | pressure_in, t_in |
| 출력 | air_vel, mdot_nozzle, thrust |
| 연결 | Turbine(cfluid_b) -> Nozzle |

## 핵심 파라미터 (근거: GitHub Issue #31, 2026-07-29 컴포넌트 코드 공유)

| 파라미터 | 기호 | 값 | 설명 |
|----------|----|----|------|
| 노즐 면적 | area | 0.3 m^2 | generic 기본값 |

## 지배 방정식 (요약)

```
p_cr = ((2/(gamma+1))^(gamma/(gamma-1))) * p_in   -- 임계압력

if p_back > p_cr:  -- 아음속(비초킹)
  p_e = p_back
  mdot, thrust, air_vel 계산 (등엔트로피 팽창)
else:               -- 초킹
  p_e = p_cr
  mdot = 초킹 질량유량식
  thrust = mdot * sqrt(2*cp*t_in*ratio_term) + area * (p_cr - p_back)   -- [2026-08-25] 수정안, 아래 참조
```

## ✅ 버그 수정안 확정 (Issue #36, 코드는 아직 미반영 — Twin Builder 반영 필요)

저장소 최상위 README.md 4장 [항목5]와 Issue #36(2026-08-24)에서 "확정된 버그"로 기록된 사항에 대해, 2026-08-25 세션에서 수정안을 도출했습니다.

- **문제(원본 코드)**: 초킹(choked) 분기에서 `p_e := p_cr`로 재정의한 직후 추력식에서 `(p_cr - p_e)` 항을 사용해 이 항이 **항등적으로 0**이 됩니다. 초킹 상태에서 발생해야 할 압력 추력항(pressure thrust term)이 실제로는 전혀 반영되지 않는 문제입니다.
  ```
  p_e := p_cr;
  ...
  thrust_n := mdot * sqrt(2.0 * cp * t_in_safe * sqrt_arg2) + area * (p_cr - p_e);
  ```
- **근거(원본 소스)**: Issue #31(2026-07-29) 공개 소스코드.
- **수정안 도출 근거**: 표준 초킹 노즐 추력식(Mattingly, *Elements of Gas Turbine Propulsion*)은 F = ṁ·V_e + A_e·(P_e − P_amb) 형태입니다. 코드에서 초킹 시 출구정압 P_e는 p_cr(임계압)로 포화되고, 배압(ambient) P_amb는 이미 코드에 `p_back == pressure_in`으로 정의되어 있는 변수입니다. 비초킹 분기(p_e:=p_back으로 두어 압력추력항이 자연스럽게 0이 되는 구조 — 배압과 출구압이 같으므로 물리적으로 타당)와 대조하면, 초킹 분기는 출구압(p_cr)이 배압(p_back)보다 항상 높으므로 압력추력항이 남아야 합니다.
- **수정안**:
  ```
  p_e := p_cr;   -- 유지 (초킹 시 출구정압이 임계압으로 포화되는 것은 물리적으로 타당하며 p_exit 출력에도 필요)
  ...
  thrust_n := mdot * sqrt(2.0 * cp * t_in_safe * sqrt_arg2) + area * (p_cr - p_back);   -- (p_cr - p_e) -> (p_cr - p_back)
  ```
- **적용 상태**: git 저장소에는 VHDL-AMS 원본(.vhd)이 없어(Twin Builder .aedt 프로젝트 내부에만 존재) 이 문서 갱신만으로는 실제 시뮬레이션에 반영되지 않습니다. **Twin Builder nozzle1 엔티티에 팀이 직접 적용해야 합니다.**
- **영향 범위**: 초킹 조건(고출력/고고도 등 배압이 임계압 이하인 구간)에서 추력이 실제보다 과소평가되고 있었으며, 수정 적용 시 해당 구간 추력값이 상향 보정됩니다.

## 추가 미해결 항목

- **면적 비현실성**: 저장소 최상위 README.md 4장 [항목6]에 따르면 area=0.3 m^2는 질량연속성 기준 역산값(약 0.0096 m^2)과 약 31배 차이가 납니다. 실제 스키매틱 인스턴스에서 override된 값인지 미확인 상태입니다.
- 이 컴포넌트의 Twin Builder 실제 시뮬레이션 결과(그래프/이미지)는 이 문서 작성 시점 기준 저장소에 별도로 첨부되어 있지 않습니다.

---
*이 문서는 2026-08-24 GitHub Issue #31 원문 소스코드 및 최상위 README.md 4장을 근거로 최초 작성되었고, 2026-08-25 Issue #36 수정안 도출 결과를 반영해 갱신되었습니다. (https://github.com/chestnutbread/Red-horse/issues/31, https://github.com/chestnutbread/Red-horse/issues/36)*
