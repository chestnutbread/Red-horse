"""
08_upload_to_supabase.py
combustor_real_normal_data.csv / fuel_fault_data.csv를
Supabase 테이블(public.fuel_fault_samples)에 업로드.

[2026-07-04 재작성 — psycopg2 직접연결 → supabase-py REST 방식으로 전환]
직접 Postgres 연결(db.<ref>.supabase.co:5432, IPv6 전용)도, Transaction Pooler
(aws-0-<region>.pooler.supabase.com:6543)도 네트워크/tenant 설정 문제로 계속
실패해서, Postgres 프로토콜을 아예 안 쓰는 방식으로 바꿨습니다. Supabase의 REST
API(PostgREST)는 그냥 HTTPS(443 포트)라 방화벽/IPv6 문제에서 자유롭습니다.

사전 준비:
  1) pip install supabase pandas --break-system-packages
  2) Supabase 대시보드 → Red-horse 프로젝트 → 좌측 하단 Project Settings(톱니바퀴)
     → API → "Project API keys" 섹션에서 **service_role** 키 복사
     (⚠ anon/publishable 키 아님 — anon 키는 이 테이블의 RLS 정책(authenticated만 허용)에
      막혀서 insert가 실패함. service_role은 RLS를 무시하고 쓸 수 있는 관리자 키라
      로컬 스크립트에서만 쓰고 절대 GitHub 등에 커밋하면 안 됨)
  3) 환경변수로 설정 (코드에 직접 쓰지 말 것):
     Windows CMD:  set SUPABASE_SERVICE_ROLE_KEY=여기에_service_role_키
     PowerShell:   $env:SUPABASE_SERVICE_ROLE_KEY="여기에_service_role_키"

실행:
  python 08_upload_to_supabase.py

테이블 스키마(이미 생성 완료, project: Red-horse / cbakdduteipgpycrtrmf):
  public.fuel_fault_samples — CSV 컬럼을 그대로 담는 wide 포맷 테이블.
  (팀 기존 테이블 engine_runs/engine_measurements는 "run 1개 = 요약 1건" 구조라
   3,000샘플급 벌크 데이터에는 안 맞아서, 이 데이터 전용으로 새 테이블을 만들었습니다.)
"""

import os
import sys
import math
from pathlib import Path

import pandas as pd
from supabase import create_client

DATA_DIR = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
NORMAL_CSV = DATA_DIR / "combustor_real_normal_data.csv"
FAULT_CSV  = DATA_DIR / "fuel_fault_data.csv"

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
BATCH_SIZE = 500   # PostgREST 한 요청에 너무 큰 payload 안 보내려고 청크 단위 insert

# CSV 컬럼명(e.g. T1_K) → DB 컬럼명(e.g. t1_k) 매핑
COLUMN_MAP = {
    'T1_K': 't1_k', 'P1_Pa': 'p1_pa', 'T2_K': 't2_k', 'P2_Pa': 'p2_pa',
    'comb_ref_K': 'comb_ref_k', 'T3_K': 't3_k', 'P3_Pa': 'p3_pa',
    'T4_K': 't4_k', 'P4_Pa': 'p4_pa',
    'FAR_demand': 'far_demand', 'FAR_actual': 'far_actual',
    'faultFactor_fuel': 'fault_factor_fuel',
    'compressor_power_kW': 'compressor_power_kw', 'turbine_power_kW': 'turbine_power_kw',
    'TIT_error_K': 'tit_error_k',
}

DB_COLUMNS = [
    'source', 'label', 'fault_type', 'fault_stage', 'twin_builder_case', 'sample_id',
    't1_k', 'p1_pa', 't2_k', 'p2_pa', 'comb_ref_k', 't3_k', 'p3_pa', 't4_k', 'p4_pa',
    'far_demand', 'far_actual', 'fault_factor_fuel',
    'compressor_power_kw', 'turbine_power_kw', 'tit_error_k', 'source_issue',
]


def load_and_prepare(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns=COLUMN_MAP)
    for col in DB_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df['source'] = 'python_synthetic'
    return df[DB_COLUMNS]


def clean_for_json(records: list[dict]) -> list[dict]:
    """numpy/NaN 값을 JSON 직렬화 가능한 순수 파이썬 타입으로 변환."""
    cleaned = []
    for rec in records:
        new_rec = {}
        for k, v in rec.items():
            if v is None:
                new_rec[k] = None
            elif isinstance(v, float) and math.isnan(v):
                new_rec[k] = None
            elif hasattr(v, "item"):   # numpy int64/float64 등 → 순수 파이썬 타입
                new_rec[k] = v.item()
            else:
                new_rec[k] = v
        cleaned.append(new_rec)
    return cleaned


def main():
    if not NORMAL_CSV.exists() or not FAULT_CSV.exists():
        sys.exit(f"❌ CSV가 없습니다. 먼저 python 07_fuel_fault_generator.py 실행하세요.\n"
                  f"   찾는 경로: {NORMAL_CSV}\n            {FAULT_CSV}")

    df_normal = load_and_prepare(NORMAL_CSV)
    df_fault  = load_and_prepare(FAULT_CSV)
    df_all = pd.concat([df_normal, df_fault], ignore_index=True)
    print(f"업로드 대상: 정상 {len(df_normal):,}행 + 고장 {len(df_fault):,}행 = 총 {len(df_all):,}행")

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    total_inserted = 0
    for start in range(0, len(df_all), BATCH_SIZE):
        chunk = df_all.iloc[start:start + BATCH_SIZE]
        records = clean_for_json(chunk.to_dict(orient="records"))
        supabase.table(TABLE_NAME).insert(records).execute()
        total_inserted += len(records)
        print(f"  ...{total_inserted:,}/{len(df_all):,}행 업로드")

    print(f"✅ Supabase 업로드 완료: public.{TABLE_NAME} ({total_inserted:,}행)")

    # 검증: label/fault_stage별 개수 재조회
    result = supabase.table(TABLE_NAME).select("label, fault_stage").execute()
    df_check = pd.DataFrame(result.data)
    print("\n검증(DB에 실제로 들어간 행수):")
    print(df_check.groupby(['label', 'fault_stage'], dropna=False).size())


if __name__ == "__main__":
    main()
