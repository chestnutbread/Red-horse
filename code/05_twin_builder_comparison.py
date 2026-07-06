"""
05_twin_builder_comparison.py
Python 시뮬레이션 vs Ansys Twin Builder 1D 결과 비교 분석

사용법:
  1. Twin Builder CSV → ../02_시뮬레이션_데이터/twin_builder_data.csv 저장
  2. python 05_twin_builder_comparison.py

필수 컬럼: T2_K, T3_K, T4_K, T5_K, P2_kPa, P3_kPa, P4_kPa, W_net_kW, EGT_K
출력: ../03_이상탐지_결과/fig3_twin_builder_comparison.png, fig4_residual_timeseries.png
      ../03_이상탐지_결과/comparison_summary.csv
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR    = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
RESULTS_DIR = Path(__file__).parent.parent / "03_이상탐지_결과"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FEAT = ['T2_K','T3_K','T4_K','T5_K','P2_kPa','P3_kPa','P4_kPa','W_net_kW','EGT_K']

df_py = pd.read_csv(DATA_DIR / "normal_data.csv")
TB_PATH = DATA_DIR / "twin_builder_data.csv"

if TB_PATH.exists():
    df_tb = pd.read_csv(TB_PATH)
    USE_DUMMY = False
    print(f"Twin Builder 데이터: {len(df_tb):,}샘플 (실제)")
else:
    print("⚠ twin_builder_data.csv 없음 → 더미 데이터로 구조 시연")
    rng = np.random.default_rng(777)
    df_tb = df_py[FEAT].copy()
    for col in FEAT:
        b = rng.uniform(-0.03, 0.03)
        df_tb[col] = df_tb[col] * (1 + b + rng.normal(0, 0.008, size=len(df_tb)))
    USE_DUMMY = True

n = min(len(df_py), len(df_tb))
df_py = df_py.iloc[:n].reset_index(drop=True)
df_tb = df_tb.iloc[:n].reset_index(drop=True)

residuals = {col: df_py[col].values - df_tb[col].values for col in FEAT if col in df_tb.columns}
df_res = pd.DataFrame(residuals)

rmse = {col: np.sqrt(np.mean(residuals[col]**2)) for col in residuals}
mape = {}
for col in residuals:
    d = np.abs(df_py[col].values); d = np.where(d<1e-6,1e-6,d)
    mape[col] = np.mean(np.abs(residuals[col])/d)*100

print("\n=== RMSE / MAPE ===")
for col in FEAT:
    if col in rmse:
        print(f"  {col:12s}: RMSE={rmse[col]:8.3f}  MAPE={mape[col]:.2f}%")

SIGMA = 3
flags = {col: np.abs(df_res[col]-df_res[col].mean()) > SIGMA*df_res[col].std() for col in residuals}
n_anom = pd.DataFrame(flags).any(axis=1).sum()
print(f"\n3σ 이상 플래그: {n_anom}/{n} ({n_anom/n*100:.1f}%)")

suffix = " (DUMMY)" if USE_DUMMY else ""
fig, axes = plt.subplots(3,3,figsize=(16,13))
axes = axes.flatten()
fig.suptitle(f'Python Simulation vs Twin Builder 1D{suffix}\nUAV Turboprop Engine | Plan A',fontsize=11)
for i,col in enumerate(FEAT):
    if col not in residuals: continue
    ax=axes[i]
    ax.scatter(df_py[col],df_tb[col],s=2,alpha=0.3,color='steelblue')
    mn=min(df_py[col].min(),df_tb[col].min()); mx=max(df_py[col].max(),df_tb[col].max())
    ax.plot([mn,mx],[mn,mx],'r--',lw=1,label='y=x')
    ax.set_xlabel(f'Python: {col}',fontsize=8); ax.set_ylabel(f'TB: {col}',fontsize=8)
    ax.set_title(f'{col}\nRMSE={rmse[col]:.2f}, MAPE={mape[col]:.2f}%',fontsize=8)
    ax.legend(fontsize=7)
for j in range(len(FEAT),len(axes)): axes[j].set_visible(False)
plt.tight_layout()
plt.savefig(RESULTS_DIR/'fig3_twin_builder_comparison.png',dpi=150,bbox_inches='tight')

fig2,axes2=plt.subplots(3,1,figsize=(14,10),sharex=True)
for ax,col,lbl in zip(axes2,['T3_K','EGT_K','W_net_kW'],['TIT T3 [K]','EGT T5 [K]','W_net [kW]']):
    if col not in residuals: continue
    ax.plot(np.arange(n),residuals[col],color='steelblue',lw=0.6,label='Residual')
    mu=df_res[col].mean(); sg=df_res[col].std()
    ax.axhline(mu+SIGMA*sg,color='red',lw=1,ls='--',label=f'+{SIGMA}σ')
    ax.axhline(mu-SIGMA*sg,color='red',lw=1,ls='--',label=f'-{SIGMA}σ')
    ax.axhline(0,color='black',lw=0.8,ls=':')
    ax.set_ylabel(f'Residual\n{lbl}',fontsize=9); ax.legend(fontsize=8)
axes2[-1].set_xlabel('Sample Index')
fig2.suptitle(f'Key Parameter Residuals{suffix}',fontsize=11)
plt.tight_layout()
plt.savefig(RESULTS_DIR/'fig4_residual_timeseries.png',dpi=150,bbox_inches='tight')

pd.DataFrame({'feature':list(rmse.keys()),'RMSE':list(rmse.values()),'MAPE_%':list(mape.values())})\
  .to_csv(RESULTS_DIR/'comparison_summary.csv',index=False)
print("✅ 비교 분석 완료 → 03_이상탐지_결과/")
