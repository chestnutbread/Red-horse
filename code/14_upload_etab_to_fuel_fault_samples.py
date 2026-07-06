"""
14_upload_etab_to_fuel_fault_samples.py
10_combustion_efficiency_fault_generator.py(시나리오1, 방안B, 실제모델) 결과인
etab_flameout_fault_data.csv를 Supabase public.fuel_fault_samples 테이블의
eta_b 컬럼에 업로드한다.

왜 flameout_fault_samples가 아니라 fuel_fault_samples에 올리는가:
  flameout_fault_samples(11번이 업로드)는 04(Plan A) 데이터 전용 테이블이다.
  10번은 07번과 동일한 real_engine_model_utils.py 물리모델을 공유하므로(Issue #7),
  07번의 결과가 이미 들어있는 fuel_fault_samples 테이블에 같이 담아야
  두 시나리오가 "같은 물리 모델·같은 피처 스키마"라는 전제가 DB 구조에도 반영된다.
  eta_b 컬럼은 이미 add_eta_b_to_fuel_fault_samples 마이그레이션으로 추가되어
  있고, fault_factor_fuel과 상호배타적으로 채워지도록 설계되었다(마이그레이션
  코멘트 참조) — 이 스크립트가 그 eta_b 쪽을 채운다.

⚠ 정상(label=normal) 데이터는 다시 올리지 않는다 — combustor_real_normal_data.csv는
  07/08이 이미 업로드한 공통 정상 베이스라인과 동일하므로 중복 삽입을 피하기 위해
  이 스크립트는 고장(label=fault, fault_type=FF-FLAMEOUT) 행만 추가한다.

사전 준비:
  1) pip install supabase pandas --break-system-packages
  2) 환경변수 SUPABASE_SERVICE_ROLE_KEY 설정 (08/11과 동일)
  3) python 07_fuel_fault_generator.py            (아직 없다면 — 공통 정상 베이스라인)
     python 10_combustion_efficiency_fault_generator.py   (etab_flameout_fault_data.csv 생성)
     python 14_upload_etab_to_fuel_fault_samples.py

fuel_fault_samples 실제 스키마(2026-07-08 확인, project: Red-horse/cbakdduteipgpycrtrmf):
  id, source, label, fault_type, fault_stage, twin_builder_case, sample_id,
  t1_k, p1_pa, t2_k, p2_pa, comb_ref_k, t3_k, p3_pa, t4_k, p4_pa,
  far_demand, far_actual, fault_factor_fuel, compressor_power_kw, turbine_power_kw,
  tit_error_k, source_issue, created_at, eta_b
  (twin_builder_case, fault_factor_fuel은 이 스크립트가 올리는 행에서는 NULL로 둔다
   — eta_b 쪽 행이므로. jssg_ref/correction_scheme은 CSV에는 있지만 이 테이블
   컬럼에는 없어 source_issue 문자열에 함께 적어 넣는다.)
"""

import os
import sys
import math
from pathlib import Path

import pandas as pd
from supabase import create_client

DATA_DIR = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
FAULT_CSV = DATA_DIR / "etab_flameout_fault_data.csv"

SUPABASE_URL = "https://cbakdduteipgpycrtrmf.supabase.co"  # 공개 정보 (비밀 아님)
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_KEY:
    sys.exit(
        "❌ 환경변수 SUPABASE_SERVICE_ROLE_KEY가 설정되어 있지 않습니다.\n"
        "   대시보드 > Project Settings > API > service_role 키를 복사한 뒤\n"
        "   set SUPABASE_SERVICE_ROLE_KEY=... (CMD) 또는 $env:SUPABASE_SERVICE_ROLE_KEY=\"...\" (PowerShell)\n"
        "   실행 후 다시 시도하세요."
    )

TABLE_NAME = "fuel_fault_samples"
BATCH_SIZE = 500

# CSV 컬럼명 → DB 컬럼명
COLUMN_MAP = {
    'T1_K': 't1_k', 'P1_Pa': 'p1_pa', 'T2_K': 't2_k', 'P2_Pa': 'p2_pa',
    'comb_ref_K': 'comb_ref_k', 'T3_K': 't3_k', 'P3_Pa': 'p3_pa',
    'T4_K': 't4_k', 'P4_Pa': 'p4_pa',
    'FAR_demand': 'far_demand', 'FAR_actual': 'far_actual', 'eta_b': 'eta_b',
    'compressor_power_kW': 'compressor_power_kw', 'turbine_power_kW': 'turbine_power_kw',
    'TIT_error_K': 'tit_error_k',
    'sample_id': 'sample_id', 'label': 'label', 'fault_type': 'fault_type',
    'fault_stage': 'fault_stage',
}

DB_COLUMNS = [
    'source', 'label', 'fault_type', 'fault_stage', 'twin_builder_case', 'sample_id',
    't1_k', 'p1_pa', 't2_k', 'p2_pa', 'comb_ref_k', 't3_k', 'p3_pa', 't4_k', 'p4_pa',
    'far_demand', 'far_actual', 'fault_factor_fuel', 'compressor_power_kw',
    'turbine_power_kw', 'tit_error_k', 'source_issue', 'eta_b',
]


def load_and_prepare(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # jssg_ref/correction_scheme은 DB 컬럼이 없으므로 source_issue에 합쳐 넣는다
    if 'jssg_ref' in df.columns or 'correction_scheme' in df.columns:
        jssg = df['jssg_ref'] if 'jssg_ref' in df.columns else ''
        scheme = df['correction_scheme'] if 'correction_scheme' in df.columns else ''
        base = df['source_issue'] if 'source_issue' in df.columns else ''
        df['source_issue'] = (
            base.astype(str) + ' | jssg_ref=' + jssg.astype(str) +
            ' | scheme=' + scheme.astype(str)
        )

    df = df.rename(columns=COLUMN_MAP)
    df['fault_factor_fuel'] = None   # eta_b 행이므로 상호배타적으로 비움
    df['twin_builder_case'] = None   # 10번 CSV에는 해당 개념 없음

    for col in DB_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df['source'] = 'python_synthetic'
    return df[DB_COLUMNS]


def clean_for_json(records: list[dict]) -> list[dict]:
    cleaned = []
    for rec in records:
        new_rec = {}
        for k, v in rec.items():
            if v is None:
                new_rec[k] = None
            elif isinstance(v, float) and math.isnan(v):
                new_rec[k] = None
            elif hasattr(v, "item"):
                new_rec[k] = v.item()
            else:
                new_rec[k] = v
        cleaned.append(new_rec)
    return cleaned


def main():
    if not FAULT_CSV.exists():
        sys.exit(
            f"❌ {FAULT_CSV.name}가 없습니다. 먼저 아래를 실행하세요.\n"
            f"   python 07_fuel_fault_generator.py   (공통 정상 베이스라인, 아직 없다면)\n"
            f"   python 10_combustion_efficiency_fault_generator.py\n"
            f"   찾는 경로: {FAULT_CSV}"
        )

    df_fault = load_and_prepare(FAULT_CSV)
    print(f"업로드 대상: 시나리오1(방안B, eta_b) 고장 {len(df_fault):,}행")
    print("정상 데이터는 07/08이 이미 올린 공통 베이스라인과 동일하므로 다시 올리지 않습니다.")

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    total_inserted = 0
    for start in range(0, len(df_fault), BATCH_SIZE):
        chunk = df_fault.iloc[start:start + BATCH_SIZE]
        records = clean_for_json(chunk.to_dict(orient="records"))
        supabase.table(TABLE_NAME).insert(records).execute()
        total_inserted += len(records)
        print(f"  ...{total_inserted:,}/{len(df_fault):,}행 업로드")

    print(f"✅ Supabase 업로드 완료: public.{TABLE_NAME}에 {total_inserted:,}행 추가")

    def count_rows(**filters) -> int:
        q = supabase.table(TABLE_NAME).select("id", count="exact")
        for k, v in filters.items():
            q = q.eq(k, v)
        return q.execute().count

    print("\n검증(DB에 실제로 들어간 행수, count=exact 기준):")
    print(f"  전체                        : {count_rows():,}")
    print(f"  fault_type=FF-FLAMEOUT      : {count_rows(fault_type='FF-FLAMEOUT'):,}  (기대값 3,000)")
    print(f"    fault_stage=onset         : {count_rows(fault_type='FF-FLAMEOUT', fault_stage='onset'):,}  (기대값 1,000)")
    print(f"    fault_stage=partial       : {count_rows(fault_type='FF-FLAMEOUT', fault_stage='partial'):,}  (기대값 1,000)")
    print(f"    fault_stage=full          : {count_rows(fault_type='FF-FLAMEOUT', fault_stage='full'):,}  (기대값 1,000)")
    print(f"  fault_type=FS-FUELSTARV(기존, 변동 없어야 함) : {count_rows(fault_type='FS-FUELSTARV'):,}  (기대값 3,000)")

    print("\n이제 12_export_pca_artifacts.py를 다시 실행하면 시나리오1 PCA가 이 데이터로 학습됩니다.")


if __name__ == "__main__":
    main()
