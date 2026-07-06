"""
01_turboprop_simulator.py
Plan A 정상 운전 데이터 생성 — 3,000 샘플

출력: ../02_시뮬레이션_데이터/normal_data.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from turboprop_simulator_utils import brayton_cycle, add_sensor_noise, DEFAULTS, RANGES

N_SAMPLES   = 3000
NOISE_LEVEL = 0.005
SEED        = 42

OUTPUT_DIR = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "normal_data.csv"

rng = np.random.default_rng(SEED)
records = []
for i in range(N_SAMPLES):
    params = dict(DEFAULTS)
    params['T1']    = rng.uniform(*RANGES['T1'])
    params['pi_c']  = rng.uniform(*RANGES['pi_c'])
    params['FAR']   = rng.uniform(*RANGES['FAR'])
    params['eta_b'] = rng.uniform(*RANGES['eta_b'])
    params['eta_t'] = rng.uniform(*RANGES['eta_t'])
    params['eta_pt']= rng.uniform(*RANGES['eta_pt'])
    params['dp_b']  = rng.uniform(*RANGES['dp_b'])

    result = brayton_cycle(**params)
    result = add_sensor_noise(result, noise_level=NOISE_LEVEL, rng=rng)

    records.append({'sample_id':i,'label':'normal','fault_type':'none',
        'T1_K':result['T1'],'T2_K':result['T2'],'T3_K':result['T3'],
        'T4_K':result['T4'],'T5_K':result['T5'],
        'P1_kPa':result['P1'],'P2_kPa':result['P2'],'P3_kPa':result['P3'],
        'P4_kPa':result['P4'],'P5_kPa':result['P5'],
        'W_net_kW':result['W_net'],'EGT_K':result['EGT'],
        'SFC':result['SFC'],'eta_thermal':result['eta_thermal'],
        'eta_b':params['eta_b'],'eta_t':params['eta_t'],
        'eta_pt':params['eta_pt'],'dp_b':params['dp_b'],
        'pi_c':params['pi_c'],'FAR':params['FAR']})

df = pd.DataFrame(records)
df.to_csv(OUTPUT_PATH, index=False)
print(f"✅ 정상 데이터 {len(df):,}샘플 → {OUTPUT_PATH}")
print(df[['T3_K','T5_K','W_net_kW','EGT_K']].describe().round(2))
