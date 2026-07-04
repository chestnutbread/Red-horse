"""
02_anomaly_detector.py
PCA Autoencoder 기반 이상탐지

입력: ../02_시뮬레이션_데이터/normal_data.csv, jssg_fault_data.csv               (시나리오1: 실화, Plan A 물리모델)
      (있으면) ../02_시뮬레이션_데이터/combustor_real_normal_data.csv,
               fuel_fault_data.csv                                              (시나리오2: 연료계통 고장, 실제 Twin Builder VHDL-AMS 물리모델)
출력: ../03_이상탐지_결과/fig1_flameout_detection.png, fig2_eta_b_vs_error.png
      (fuel_fault_data.csv 있으면) fig5_fault_type_comparison.png

※ [2026-07-04] 시나리오1(실화, Plan A: pi_c=9.6/η_c=0.80 등)과 시나리오2(연료계통
  고장, 실제 Twin Builder 값: PR=10.55/comb_ref=1365K 등, GitHub Issue #6/#3 근거)는
  물리 모델 자체가 서로 다르고 변수/스케일도 다르므로(예: T3_K의 절대값 기준이 다름),
  같은 PCA/scaler로 섞어서 비교하면 안 된다. 그래서 시나리오2는 07_fuel_fault_generator.py가
  만드는 전용 정상 베이스라인(combustor_real_normal_data.csv)으로 별도 PCA를 학습해
  독립적으로 평가한다 (시나리오1의 normal_data.csv/PCA와는 완전히 분리된 파이프라인).
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score, classification_report

try:
    import koreanize_matplotlib
except ImportError:
    pass

DATA_DIR    = Path(__file__).parent.parent / "02_시뮬레이션_데이터"
RESULTS_DIR = Path(__file__).parent.parent / "03_이상탐지_결과"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = ['T2_K','T3_K','T4_K','T5_K',
            'P2_kPa','P3_kPa','P4_kPa',
            'W_net_kW','EGT_K','SFC','eta_thermal']

df_normal = pd.read_csv(DATA_DIR / "normal_data.csv")
df_fault  = pd.read_csv(DATA_DIR / "jssg_fault_data.csv")

# 시나리오2(연료계통 고장, 실제 Twin Builder 물리모델) — 반드시 자체 베이스라인과 짝지어야 함
FUEL_FAULT_PATH  = DATA_DIR / "fuel_fault_data.csv"
FUEL_NORMAL_PATH = DATA_DIR / "combustor_real_normal_data.csv"
df_fuel_fault  = pd.read_csv(FUEL_FAULT_PATH)  if FUEL_FAULT_PATH.exists()  else None
df_fuel_normal = pd.read_csv(FUEL_NORMAL_PATH) if FUEL_NORMAL_PATH.exists() else None

# 시나리오2 전용 피처 (실제 Combustor/Turbine 모델 출력 컬럼 — 시나리오1 FEATURES와 다름)
FEATURES_FUEL = ['T2_K','T3_K','T4_K','P2_Pa','P3_Pa','P4_Pa',
                  'compressor_power_kW','turbine_power_kW','FAR_actual']

scaler = StandardScaler()
X_normal_s = scaler.fit_transform(df_normal[FEATURES].values)
X_fault_s  = scaler.transform(df_fault[FEATURES].values)

pca = PCA(n_components=6)   # arXiv:2505.24044 — scree plot 99% 분산 기준
pca.fit(X_normal_s)

def recon_err(X):
    return np.mean((X - pca.inverse_transform(pca.transform(X))) ** 2, axis=1)

err_normal = recon_err(X_normal_s)
err_fault  = recon_err(X_fault_s)
threshold  = np.percentile(err_normal, 95)   # 오경보율 5% 목표

print(f"임계값(95th pct): {threshold:.6f}")
y_true = np.concatenate([np.zeros(len(err_normal)), np.ones(len(err_fault))])
y_sc   = np.concatenate([err_normal, err_fault])
auc    = roc_auc_score(y_true, y_sc)
y_pred = (y_sc > threshold).astype(int)
print(f"ROC-AUC: {auc:.3f}")
print(classification_report(y_true, y_pred, target_names=['normal','fault']))

df_fault = df_fault.copy()
df_fault['recon_error'] = err_fault
df_fault['detected']    = err_fault > threshold
print("\n단계별 탐지율 (시나리오1: 실화, η_b↓):")
print(df_fault.groupby('fault_stage')[['detected','eta_b']].agg(
    탐지율=('detected', lambda x: f"{x.mean()*100:.1f}%"),
    eta_b_평균=('eta_b','mean')))

# ─────────────────────────────────────────────
# 시나리오2: 연료계통 고장 — 독립된 PCA 파이프라인 (실제 Twin Builder 물리모델,
# GitHub Issue #6/#3 기준. combustor_real_normal_data.csv/fuel_fault_data.csv 둘 다 있을 때만)
# ─────────────────────────────────────────────
if df_fuel_fault is not None and df_fuel_normal is not None:
    scaler_fuel = StandardScaler()
    X_fnorm_s = scaler_fuel.fit_transform(df_fuel_normal[FEATURES_FUEL].values)
    X_ffault_s = scaler_fuel.transform(df_fuel_fault[FEATURES_FUEL].values)

    pca_fuel = PCA(n_components=min(4, len(FEATURES_FUEL)))
    pca_fuel.fit(X_fnorm_s)

    def recon_err_fuel(X):
        return np.mean((X - pca_fuel.inverse_transform(pca_fuel.transform(X))) ** 2, axis=1)

    err_fnorm  = recon_err_fuel(X_fnorm_s)
    err_ffault = recon_err_fuel(X_ffault_s)
    threshold_fuel = np.percentile(err_fnorm, 95)

    df_fuel_fault = df_fuel_fault.copy()
    df_fuel_fault['recon_error'] = err_ffault
    df_fuel_fault['detected']    = err_ffault > threshold_fuel

    print(f"\n[시나리오2: 연료계통 고장 — 독립 PCA, 실제 Twin Builder 물리모델]")
    print(f"정상 베이스라인: {len(df_fuel_normal):,}샘플 ({FUEL_NORMAL_PATH.name}), "
          f"고장: {len(df_fuel_fault):,}샘플 ({FUEL_FAULT_PATH.name})")
    print(f"임계값(95th pct): {threshold_fuel:.6f}")
    print("단계별 탐지율 (comb_ref 명령 대비 실제 TIT 괴리 = TIT_error_K가 핵심 고장 시그니처):")
    print(df_fuel_fault.groupby('fault_stage')[['detected','faultFactor_fuel','TIT_error_K']].agg(
        탐지율=('detected', lambda x: f"{x.mean()*100:.1f}%"),
        faultFactor_fuel=('faultFactor_fuel','mean'),
        TIT_error_K_평균=('TIT_error_K','mean')))

    y_true_fuel = np.concatenate([np.zeros(len(err_fnorm)), np.ones(len(err_ffault))])
    y_sc_fuel   = np.concatenate([err_fnorm, err_ffault])
    auc_fuel    = roc_auc_score(y_true_fuel, y_sc_fuel)
    print(f"ROC-AUC (정상 vs 연료계통 고장, 독립 PCA): {auc_fuel:.3f}")
    print("\n※ 시나리오1과 시나리오2는 물리 모델이 달라 위 두 ROC-AUC를 하나로 합산하지 않음.")
    print("   (예: 시나리오1 PCA 입력의 T3_K와 시나리오2 PCA 입력의 T3_K는 절대값 기준이 다름)")
else:
    missing = []
    if df_fuel_normal is None: missing.append(FUEL_NORMAL_PATH.name)
    if df_fuel_fault is None: missing.append(FUEL_FAULT_PATH.name)
    print(f"\n⚠ {', '.join(missing)} 없음 → 시나리오2(연료계통 고장) 미평가.")
    print("   생성하려면: python 07_fuel_fault_generator.py")

colors = {'onset':'#FFA500','partial':'#FF4500','full':'#8B0000'}
fig, axes = plt.subplots(2,2,figsize=(14,10))
fig.suptitle('UAV 터보프롭 엔진 실화(Flameout) 이상탐지\nPCA Autoencoder | JSSG-2007A §3.2.2.3.5/3.2.2.6',fontsize=13)

ax=axes[0,0]
ax.hist(err_normal,bins=50,alpha=0.6,label='Normal',color='steelblue')
ax.hist(err_fault, bins=50,alpha=0.6,label='Flameout',color='crimson')
ax.axvline(threshold,color='orange',lw=2,ls='--',label=f'Threshold={threshold:.4f}')
ax.set_title('Reconstruction Error Distribution'); ax.legend()

ax=axes[0,1]
for s,g in df_fault.groupby('fault_stage'):
    ax.scatter(g['eta_b'],g['recon_error'],s=5,alpha=0.5,color=colors.get(s,'gray'),label=s)
ax.axhline(threshold,color='black',lw=1.5,ls='--',label='Threshold')
ax.set_title('η_b vs Reconstruction Error')
ax.set_xlabel('η_b'); ax.set_ylabel('Recon Error'); ax.legend(markerscale=3)

ax=axes[1,0]
ax.hist(df_normal['EGT_K'],bins=50,alpha=0.6,label='Normal',color='steelblue')
ax.hist(df_fault['EGT_K'], bins=50,alpha=0.6,label='Fault',color='crimson')
ax.set_title('EGT Distribution [K]'); ax.legend()

ax=axes[1,1]
stages=['onset','partial','full']
rates=[df_fault[df_fault['fault_stage']==s]['detected'].mean()*100 for s in stages]
bars=ax.bar(stages,rates,color=['#FFA500','#FF4500','#8B0000'])
ax.set_ylim(0,115); ax.set_title('Detection Rate by Stage (%)')
for b,r in zip(bars,rates):
    ax.text(b.get_x()+b.get_width()/2,b.get_height()+1,f'{r:.1f}%',ha='center',fontweight='bold')

plt.tight_layout()
plt.savefig(RESULTS_DIR/'fig1_flameout_detection.png',dpi=150,bbox_inches='tight')

fig2,ax2=plt.subplots(figsize=(8,5))
for s,g in df_fault.groupby('fault_stage'):
    ax2.scatter(g['eta_b'],g['recon_error'],s=8,alpha=0.6,color=colors.get(s,'gray'),label=s)
ax2.axhline(threshold,color='black',lw=1.5,ls='--',label='Threshold')
ax2.set_title('η_b vs Reconstruction Error (MSE)')
ax2.set_xlabel('η_b'); ax2.set_ylabel('Recon Error'); ax2.legend(markerscale=2)
plt.tight_layout()
fig2.savefig(RESULTS_DIR/'fig2_eta_b_vs_error.png',dpi=150,bbox_inches='tight')

if df_fuel_fault is not None and df_fuel_normal is not None:
    fig5, ax5 = plt.subplots(figsize=(8,5))
    labels, rates_all, bar_colors = [], [], []
    for s in ['onset','partial','full']:
        labels.append(f'실화\n{s}')
        rates_all.append(df_fault[df_fault['fault_stage']==s]['detected'].mean()*100)
        bar_colors.append(colors.get(s,'gray'))
    fuel_colors = {'moderate':'#1E90FF','severe':'#00008B'}
    for s in ['moderate','severe']:
        labels.append(f'연료계통\n{s}')
        rates_all.append(df_fuel_fault[df_fuel_fault['fault_stage']==s]['detected'].mean()*100)
        bar_colors.append(fuel_colors.get(s,'gray'))
    bars5 = ax5.bar(labels, rates_all, color=bar_colors)
    ax5.set_ylim(0,115)
    ax5.set_title('시나리오별 탐지율 비교: 실화 vs 연료계통 고장 (%)')
    for b,r in zip(bars5, rates_all):
        ax5.text(b.get_x()+b.get_width()/2, b.get_height()+1, f'{r:.1f}%', ha='center', fontweight='bold')
    plt.tight_layout()
    fig5.savefig(RESULTS_DIR/'fig5_fault_type_comparison.png', dpi=150, bbox_inches='tight')
    print("✅ 그래프 저장 완료 → 03_이상탐지_결과/ (fig1, fig2, fig5)")
else:
    print("✅ 그래프 저장 완료 → 03_이상탐지_결과/ (fig1, fig2)")
