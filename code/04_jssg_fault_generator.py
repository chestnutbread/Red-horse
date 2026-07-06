"""
04_jssg_fault_generator.py
JSSG-2007A §3.2.2.3.5 / §3.2.2.6 기반 연소실 실화(Flameout) 데이터 생성
- onset  (초기): η_b = 0.65~0.80  [JSSG §3.2.2.3.5]
- partial(부분): η_b = 0.35~0.65  [보간 추정]
- full   (완전): η_b = 0.05~0.35  [JSSG §3.2.2.6]
각 단계 1,000샘플 → 총 3,000샘플

출력: ../02_시뮬레이션_데이터/jssg_fault_data.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from turboprop_simulator_utils import brayton_cycle, add_sensor_noise, DEFAULTS, RANGES

N_PER_STAGE = 1000
NOISE_LEVEL = 0.005
SEED        = 99

OUTPUT_DIR  = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "jssg_fault_data.csv"

STAGES = [
    ('onset',   0.65, 0.80),
    ('partial', 0.35, 0.65),
    ('full',    0.05, 0.35),
]

rng = np.random.default_rng(SEED)
records = []; sample_id = 0
for stage_name, lo, hi in STAGES:
    for _ in range(N_PER_STAGE):
        params = dict(DEFAULTS)
        params['T1']    = rng.uniform(*RANGES['T1'])
        params['pi_c']  = rng.uniform(*RANGES['pi_c'])
        params['FAR']   = rng.uniform(*RANGES['FAR'])
        params['eta_t'] = rng.uniform(*RANGES['eta_t'])
        params['eta_pt']= rng.uniform(*RANGES['eta_pt'])
        params['dp_b']  = rng.uniform(*RANGES['dp_b'])
        params['eta_b'] = rng.uniform(lo, hi)

        result = brayton_cycle(**params)
        result = add_sensor_noise(result, noise_level=NOISE_LEVEL, rng=rng)

        records.append({'sample_id':sample_id,'label':'fault','fault_type':'FF-FLAMEOUT',
            'fault_stage':stage_name,'jssg_ref':'§3.2.2.3.5/3.2.2.6',
            'T1_K':result['T1'],'T2_K':result['T2'],'T3_K':result['T3'],
            'T4_K':result['T4'],'T5_K':result['T5'],
            'P1_kPa':result['P1'],'P2_kPa':result['P2'],'P3_kPa':result['P3'],
            'P4_kPa':result['P4'],'P5_kPa':result['P5'],
            'W_net_kW':result['W_net'],'EGT_K':result['EGT'],
            'SFC':result['SFC'],'eta_thermal':result['eta_thermal'],
            'eta_b':params['eta_b'],'pi_c':params['pi_c'],'FAR':params['FAR']})
        sample_id += 1

df = pd.DataFrame(records)
df.to_csv(OUTPUT_PATH, index=False)
print(f"✅ 실화 고장 데이터 {len(df):,}샘플 → {OUTPUT_PATH}")
print(df.groupby('fault_stage')[['eta_b','T3_K','EGT_K','W_net_kW']].mean().round(2))
