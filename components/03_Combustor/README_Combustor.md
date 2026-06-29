# 03. Combustor (연소기)

**역할:** 압축 공기에 연료를 공급하여 연소. 열에너지를 추가하고 연소가스를 Turbine으로 전달.

---

## 모델 개요

| 항목 | 내용 |
|------|------|
| 모델링 언어 | VHDL-AMS |
| 입력 | t_in [K] (Compressor 출구), cfluid_a, fuel |
| 출력 | t_out [K], fa_ratio (연료공기비), cfluid_b → Turbine |
| 연소실 형식 | 단일 환형(annular) 역류식 |

## 핵심 파라미터

| 파라미터 | 값 | 설명 |
|----------|----|------|
| γ (gamma) | 1.31 | 연소가스 비열비 (공기 1.4와 다름) |
| cp | 1212.5 J/(kg·K) | γR/(γ-1) |
| eff (연소 효율) | 0.94 ~ 0.98 | 압력 손실 반영: p_out = eff × p_in |

---

## 시뮬레이션 결과

### 연소기 입구 온도 (combustor1.t_in)

![combustor t_in](images/08_combustor_t_in.png)

- 정상 상태 수렴값: **613.75 K** (약 340°C)
- Compressor 출구 온도와 일치 — 컴포넌트 간 연결 정상 확인 ✅

### 연소기 출구 온도 (combustor1.t_out)

![combustor t_out](images/09_combustor_t_out.png)

- 초기값 500 K → 약 25초 내 **1,250 K** 수렴
- 연소 시작 후 빠르게 온도 상승, 정상 상태 유지 ✅
- 1,250 K = Turbine 입구 온도(TIT) 기준값으로 사용

---

## 고장 주입 계획

| 항목 | 내용 |
|------|------|
| 주입 변수 | eff (연소실 효율) |
| 주입 범위 | 기준 → -2% → -5% 단계 sweep |
| 예상 영향 | fa_ratio ↑, t_out 변화 → 점진적 열화 시 Flameout 근사 가능 |
| 상태 | 🔲 예정 |
