"""
08_upload_to_supabase.py
combustor_real_normal_data.csv / fuel_fault_data.csv를
Supabase Postgres 테이블(public.fuel_fault_samples)에 업로드.

⚠ 이 스크립트는 로컬에서 직접 실행해야 합니다. (Claude 쪽 샌드박스 셸이 이번 세션에
   비활성화되어 있어서 6,000행을 채팅 컨텍스트로 옮겨 SQL을 만드는 방식은 비효율적이라
   로컬 Python이 직접 DB에 붓는 방식을 택했습니다.)

⚠ 직접 연결(db.<ref>.supabase.co:5432)은 IPv6 전용이라 IPv6 미지원 네트워크에서는
  "could not translate host name" 에러가 납니다. 이 경우 Connection Pooler(Supavisor)를
  써야 하며, 이 스크립트는 기본값을 Pooler로 맞춰뒀습니다. 그래도 안 되면 아래 순서로
  정확한 값을 대시보드에서 그대로 복사하세요:
    Supabase 대시보드 → 프로젝트 Red-horse → 상단 "Connect" 버튼 → "Connection string"
    탭에서 "Transaction pooler" 선택 → 거기 나오는 Host/Port/User를 아래 환경변수로 지정.

사전 준비:
  1) pip install psycopg2-binary pandas --break-system-packages   (또는 그냥 pip install)
  2) Supabase 대시보드에서 DB 비밀번호 확인/재설정 (Project Settings → Database)
  3) 환경변수 설정 (코드에 직접 쓰지 말 것):
     Windows CMD:
       set SUPABASE_DB_PASSWORD=여기에_비밀번호
       (Pooler 기본 추정값이 안 맞으면 아래도 설정)
       set SUPABASE_DB_HOST=대시보드에서_복사한_host
       set SUPABASE_DB_PORT=6543
       set SUPABASE_DB_USER=대시보드에서_복사한_user   (보통 postgres.프로젝트ref 형태)
     PowerShell: $env:SUPABASE_DB_PASSWORD="여기에_비밀번호"  (나머지도 동일하게 $env: 로)

실행:
  python 08_upload_to_supabase.py

테이블 스키마(이미 생성 완료, project: Red-horse / cbakdduteipgpycrtrmf):
  public.fuel_fault_samples — CSV 컬럼을 그대로 담는 wide 포맷 테이블.
  (팀 기존 테이블 engine_runs/engine_measurements는 "run 1개 = 요약 1건" 구조라
   3,000샘플급 벌크 데이터에는 안 맞아서, 이 데이터 전용으로 새 테이블을 만들었습니다.)
"""

import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DATA_DIR = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
NORMAL_CSV = DATA_DIR / "combustor_real_normal_data.csv"
FAULT_CSV  = DATA_DIR / "fuel_fault_data.csv"

# ── Supabase 연결 정보 ──────────────────────────────────────────
PROJECT_REF = "cbakdduteipgpycrtrmf"
PROJECT_REGION = "ap-northeast-2"  # Supabase 프로젝트 리전 (Seoul)

# 기본값: Transaction Pooler (IPv4 지원, 대부분의 네트워크에서 direct보다 안정적으로 연결됨)
# ⚠ "aws-0-ap-northeast-2" 부분은 추정값입니다 — 연결이 안 되면 대시보드 Connect 화면의
#   Transaction pooler 탭에 나온 정확한 host를 SUPABASE_DB_HOST 환경변수로 넣어 덮어쓰세요.
DB_HOST = os.environ.get("SUPABASE_DB_HOST", f"aws-0-{PROJECT_REGION}.pooler.supabase.com")
DB_PORT = int(os.environ.get("SUPABASE_DB_PORT", "6543"))
DB_NAME = os.environ.get("SUPABASE_DB_NAME", "postgres")
DB_USER = os.environ.get("SUPABASE_DB_USER", f"postgres.{PROJECT_REF}")
DB_PASSWORD = os.environ.get("SUPABASE_DB_PASSWORD")

if not DB_PASSWORD:
    sys.exit(
        "❌ 환경변수 SUPABASE_DB_PASSWORD가 설정되어 있지 않습니다.\n"
        "   Supabase 대시보드 > Project Settings > Database에서 비밀번호를 확인한 뒤\n"
        "   set SUPABASE_DB_PASSWORD=... (CMD) 또는 $env:SUPABASE_DB_PASSWORD=\"...\" (PowerShell) 실행 후 다시 시도하세요."
    )

print(f"연결 시도: host={DB_HOST} port={DB_PORT} user={DB_USER}")
print("  (연결 실패 시 대시보드 Connect > Transaction pooler 값으로 SUPABASE_DB_HOST/PORT/USER 재설정)")

# CSV 컬럼명(snake+units, e.g. T1_K) → DB 컬럼명(snake_case, e.g. t1_k) 매핑
COLUMN_MAP = {
    'T1_K': 't1_k', 'P1_Pa': 'p1_pa', 'T2_K': 't2_k', 'P2_Pa': 'p2_pa',
    'comb_ref_K': 'comb_ref_k', 'T3_K': 't3_k', 'P3_Pa': 'p3_pa',
    'T4_K': 't4_k', 'P4_Pa': 'p4_pa',
    'FAR_demand': 'far_demand', 'FAR_actual': 'far_actual',
    'faultFactor_fuel': 'fault_factor_fuel',
    'compressor_power_kW': 'compressor_power_kw', 'turbine_power_kW': 'turbine_power_kw',
    'TIT_error_K': 'tit_error_k',
    'sample_id': 'sample_id', 'label': 'label', 'fault_type': 'fault_type',
    'fault_stage': 'fault_stage', 'twin_builder_case': 'twin_builder_case',
    'source_issue': 'source_issue',
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


def main():
    if not NORMAL_CSV.exists() or not FAULT_CSV.exists():
        sys.exit(f"❌ CSV가 없습니다. 먼저 python 07_fuel_fault_generator.py 실행하세요.\n"
                  f"   찾는 경로: {NORMAL_CSV}\n            {FAULT_CSV}")

    df_normal = load_and_prepare(NORMAL_CSV)
    df_fault  = load_and_prepare(FAULT_CSV)
    df_all = pd.concat([df_normal, df_fault], ignore_index=True)
    print(f"업로드 대상: 정상 {len(df_normal):,}행 + 고장 {len(df_fault):,}행 = 총 {len(df_all):,}행")

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, sslmode='require',
    )
    try:
        with conn.cursor() as cur:
            insert_sql = f"""
                INSERT INTO public.fuel_fault_samples ({', '.join(DB_COLUMNS)})
                VALUES %s
            """
            rows = [tuple(r) for r in df_all[DB_COLUMNS].itertuples(index=False, name=None)]
            execute_values(cur, insert_sql, rows, page_size=500)
        conn.commit()
        print(f"✅ Supabase 업로드 완료: public.fuel_fault_samples ({len(df_all):,}행)")

        with conn.cursor() as cur:
            cur.execute("SELECT label, fault_stage, count(*) FROM public.fuel_fault_samples "
                        "GROUP BY label, fault_stage ORDER BY label, fault_stage;")
            print("\n검증(DB에 실제로 들어간 행수):")
            for row in cur.fetchall():
                print(f"  label={row[0]:<8} fault_stage={str(row[1]):<10} count={row[2]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
