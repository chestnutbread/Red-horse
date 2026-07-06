"""
11_upload_flameout_to_supabase.py
normal_data.csv / jssg_fault_data.csv(시나리오1: 실화, Plan A)를
Supabase 테이블(public.flameout_fault_samples)에 업로드.

08_upload_to_supabase.py(시나리오2)와 동일한 REST(PostgREST) 방식 — Postgres
직접연결(IPv6)/Transaction Pooler 모두 이 프로젝트 네트워크 환경에서 실패했던
전례가 있어 처음부터 HTTPS 기반으로 작성했다.

사전 준비 (08과 동일):
  1) pip install supabase pandas --break-system-packages
  2) Supabase 대시보드 → Red-horse 프로젝트 → Project Settings(톱니바퀴) → API
     → "Project API keys" 섹션에서 **service_role** 키 복사
     (⚠ anon 키 아님 — flameout_fault_samples도 RLS가 authenticated만 허용하도록
      되어 있어 anon 키로는 insert 실패함. service_role은 절대 커밋/공유 금지,
      로컬 환경변수로만 사용)
  3) 환경변수 설정:
     Windows CMD:  set SUPABASE_SERVICE_ROLE_KEY=여기에_service_role_키
     PowerShell:   $env:SUPABASE_SERVICE_ROLE_KEY="여기에_service_role_키"

실행:
  python 01_turboprop_simulator.py      (normal_data.csv 생성, 아직 없다면)
  python 04_jssg_fault_generator.py     (jssg_fault_data.csv 생성, 아직 없다면)
  python 11_upload_flameout_to_supabase.py

테이블 스키마(2026-07-08 신설, project: Red-horse / cbakdduteipgpycrtrmf):
  public.flameout_fault_samples — 01/04 CSV 컬럼을 그대로 담는 wide 포맷 테이블.
  fuel_fault_samples(시나리오2)와 물리모델/스케일이 달라 별도 테이블로 분리했다.
"""

import os
import sys
import math
from pathlib import Path

import pandas as pd
from supabase import create_client

DATA_DIR = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
NORMAL_CSV = DATA_DIR / "normal_data.csv"
FAULT_CSV  = DATA_DIR / "jssg_fault_data.csv"

SUPABASE_URL = "https://cbakdduteipgpycrtrmf.supabase.co"  # 공개 정보 (비밀 아님)
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_KEY:
    sys.exit(
        "❌ 환경변수 SUPABASE_SERVICE_ROLE_KEY가 설정되어 있지 않습니다.\n"
        "   대시보드 > Project Settings > API > service_role 키를 복사한 뒤\n"
        "   set SUPABASE_SERVICE_ROLE_KEY=... (CMD) 또는 $env:SUPABASE_SERVICE_ROLE_KEY=\"...\" (PowerShell)\n"
        "   실행 후 다시 시도하세요."
    )

TABLE_NAME = "flameout_fault_samples"
BATCH_SIZE = 500   # PostgREST 한 요청에 너무 큰 payload 안 보내려고 청크 단위 insert

# CSV 컬럼명(예: T1_K) → DB 컬럼명(예: t1_k) 매핑
COLUMN_MAP = {
    'T1_K': 't1_k', 'T2_K': 't2_k', 'T3_K': 't3_k', 'T4_K': 't4_k', 'T5_K': 't5_k',
    'P1_kPa': 'p1_kpa', 'P2_kPa': 'p2_kpa', 'P3_kPa': 'p3_kpa',
    'P4_kPa': 'p4_kpa', 'P5_kPa': 'p5_kpa',
    'W_net_kW': 'w_net_kw', 'EGT_K': 'egt_k', 'SFC': 'sfc', 'eta_thermal': 'eta_thermal',
    'eta_b': 'eta_b', 'eta_t': 'eta_t', 'eta_pt': 'eta_pt', 'dp_b': 'dp_b',
    'pi_c': 'pi_c', 'FAR': 'far',
}

DB_COLUMNS = [
    'source', 'label', 'fault_type', 'fault_stage', 'jssg_ref', 'sample_id',
    't1_k', 't2_k', 't3_k', 't4_k', 't5_k',
    'p1_kpa', 'p2_kpa', 'p3_kpa', 'p4_kpa', 'p5_kpa',
    'w_net_kw', 'egt_k', 'sfc', 'eta_thermal',
    'eta_b', 'eta_t', 'eta_pt', 'dp_b', 'pi_c', 'far',
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
            elif hasattr(v, "item"):
                new_rec[k] = v.item()
            else:
                new_rec[k] = v
        cleaned.append(new_rec)
    return cleaned


def main():
    if not NORMAL_CSV.exists() or not FAULT_CSV.exists():
        sys.exit(f"❌ CSV가 없습니다. 먼저 python 01_turboprop_simulator.py / "
                  f"python 04_jssg_fault_generator.py 실행하세요.\n"
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

    def count_rows(**filters) -> int:
        q = supabase.table(TABLE_NAME).select("id", count="exact")
        for k, v in filters.items():
            q = q.eq(k, v)
        return q.execute().count

    print("\n검증(DB에 실제로 들어간 행수, count=exact 기준):")
    print(f"  전체            : {count_rows():,}")
    print(f"  label=normal    : {count_rows(label='normal'):,}  (기대값 3,000)")
    print(f"  label=fault     : {count_rows(label='fault'):,}  (기대값 3,000)")
    print(f"    fault_stage=onset   : {count_rows(label='fault', fault_stage='onset'):,}  (기대값 1,000)")
    print(f"    fault_stage=partial : {count_rows(label='fault', fault_stage='partial'):,}  (기대값 1,000)")
    print(f"    fault_stage=full    : {count_rows(label='fault', fault_stage='full'):,}  (기대값 1,000)")


if __name__ == "__main__":
    main()
