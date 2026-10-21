"""Generate Publication-Quality Visual Assets for DATA_UNDERSTANDING_GUIDE.md.
Uses verified metrics from diagnostics/outputs/d4_diversity_metrics.json and
d5_reward_reconstruction.json.
Outputs saved directly to 02_DATA_UNDERSTANDING/assets/.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
OUTPUTS_DIR = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "diagnostics" / "outputs"
ASSETS_DIR = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Styling
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9

def generate_figure_4_1_thermal_diversity():
    """Figure 4.1: Building Thermal Inertia and Envelope Properties."""
    metrics_path = OUTPUTS_DIR / "d4_diversity_metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    bldgs_dict = data["buildings_diversity"]
    bldgs = list(bldgs_dict.values())
    
    names = [b["name"].replace("building_train_", "Bldg ") for b in bldgs]
    u_vals = [b["derived_facade_U_W_per_m2_K"] for b in bldgs]
    caps = [b["derived_envelope_capacity_J_per_m3_K"] / 1e6 for b in bldgs] # MJ/(m^3 K)
    tau_vals = [b["relative_time_constant_index"] for b in bldgs]
    zones = [b["num_zones_V"] for b in bldgs]
    ahus = [b["num_ahus_K"] for b in bldgs]
    
    # Sort by tau
    sorted_indices = np.argsort(tau_vals)
    names = [names[i] for i in sorted_indices]
    u_vals = [u_vals[i] for i in sorted_indices]
    caps = [caps[i] for i in sorted_indices]
    tau_vals = [tau_vals[i] for i in sorted_indices]
    zones = [zones[i] for i in sorted_indices]
    ahus = [ahus[i] for i in sorted_indices]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8), dpi=200)
    
    # Plot 1: Thermal Inertia Index tau
    bars = ax1.barh(names, tau_vals, color='#1f77b4', edgecolor='black', alpha=0.85)
    ax1.set_xlabel(r'Relative Thermal Inertia Index $\tau \propto C_{\mathrm{env}} / U$ (dimensionless)')
    ax1.set_title('Building Thermal Inertia Spectrum (7.4× Spread)')
    ax1.grid(True, linestyle='--', alpha=0.5)
    
    for bar, tau in zip(bars, tau_vals):
        ax1.text(bar.get_width() + 0.25, bar.get_y() + bar.get_height()/2, 
                 f'{tau:.2f}', va='center', ha='left', fontweight='bold', color='#1f77b4')
    ax1.set_xlim(0, 16.5)
    
    # Plot 2: Scatter of U-value vs Heat Capacity
    scatter = ax2.scatter(u_vals, caps, s=[z * 7 for z in zones], c=tau_vals, 
                          cmap='viridis', edgecolor='black', linewidth=1.5, alpha=0.85)
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label(r'Thermal Inertia Index $\tau$')
    
    for i, name in enumerate(names):
        ax2.annotate(f"{name}\n({zones[i]} zones, {ahus[i]} AHUs)", (u_vals[i], caps[i]),
                     textcoords="offset points", xytext=(8, -4), ha='left', fontsize=8.5)
                     
    ax2.set_xlabel(r'Facade Heat Transmission $U$ [$\mathrm{W}/(\mathrm{m}^2\cdot\mathrm{K})$]')
    ax2.set_ylabel(r'Envelope Volumetric Heat Capacity $C_{\mathrm{env}}$ [$\mathrm{MJ}/(\mathrm{m}^3\cdot\mathrm{K})$]')
    ax2.set_title('Envelope Heat Transmission vs. Storage Capacity')
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.set_xlim(1.0, 2.3)
    ax2.set_ylim(0.3, 2.05)
    
    plt.tight_layout()
    out_file = ASSETS_DIR / "figure_4_1_thermal_diversity.png"
    plt.savefig(out_file, bbox_inches='tight')
    plt.close()
    print(f"Generated {out_file}")

def generate_figure_5_1_climate_regimes():
    """Figure 5.1: Meteorological Diversity Across the 5 Climates."""
    metrics_path = OUTPUTS_DIR / "d4_diversity_metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    summary = data["station_summary"]
    stations = list(summary.keys())
    min_temps = [summary[s]["absolute_min_C"] for s in stations]
    max_temps = [summary[s]["absolute_max_C"] for s in stations]
    mean_temps = [summary[s]["average_mean_C"] for s in stations]
    swings = [summary[s]["average_diurnal_swing_C"] for s in stations]
    hdds = [summary[s]["average_hdd_18C"] for s in stations]
    cdds = [summary[s]["average_cdd_18C"] for s in stations]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8), dpi=200)
    
    # Plot 1: Temperature Ranges (Min, Mean, Max)
    y_pos = np.arange(len(stations))
    ax1.barh(y_pos, [max_t - min_t for min_t, max_t in zip(min_temps, max_temps)], 
             left=min_temps, color='#3498db', alpha=0.6, edgecolor='black', label='Historical Temp Span')
    ax1.scatter(mean_temps, y_pos, color='#e74c3c', s=60, zorder=5, label='Mean Temp (°C)')
    ax1.axvline(21.0, color='#27ae60', linestyle='--', linewidth=1.3, label='Comfort Lower (21°C)')
    ax1.axvline(24.0, color='#27ae60', linestyle=':', linewidth=1.3, label='Comfort Upper (24°C)')
    
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels([s.title() for s in stations], fontweight='bold')
    ax1.set_xlabel('Outdoor Dry-Bulb Temperature [°C]')
    ax1.set_title('Meteorological Temperature Spans vs. Comfort Band')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='lower right', fontsize=8.5)
    
    # Annotate swings
    for i, (mn, mx, sw) in enumerate(zip(min_temps, max_temps, swings)):
        ax1.text(mx + 1.2, i, f"Swing: {sw:.1f}°C", va='center', fontsize=8.5, color='#2c3e50')
    ax1.set_xlim(-48, 58)
    
    # Plot 2: Degree Days (HDD vs CDD)
    x = np.arange(len(stations))
    width = 0.35
    ax2.bar(x - width/2, hdds, width, label='Heating Degree Days (HDD)', color='#e67e22', edgecolor='black', alpha=0.85)
    ax2.bar(x + width/2, cdds, width, label='Cooling Degree Days (CDD)', color='#2980b9', edgecolor='black', alpha=0.85)
    
    ax2.set_xticks(x)
    ax2.set_xticklabels([s.title() for s in stations], rotation=20, fontweight='bold')
    ax2.set_ylabel('Degree Days (Base 18.3°C / 65°F) [°C-days]')
    ax2.set_title('Heating vs. Cooling Thermodynamic Demand')
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='upper right', fontsize=8.5)
    
    plt.tight_layout()
    out_file = ASSETS_DIR / "figure_5_1_climate_regimes.png"
    plt.savefig(out_file, bbox_inches='tight')
    plt.close()
    print(f"Generated {out_file}")

def generate_figure_6_1_comfort_penalty():
    """Figure 6.1: Piecewise Quadratic Comfort Shortfall Penalty Function."""
    fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=200)
    
    deviations = np.linspace(0.0, 10.0, 300)
    penalties = []
    for d in deviations:
        if d <= 0.0:
            penalties.append(0.0)
        elif d <= 5.0:
            penalties.append(d / 5.0)
        else:
            penalties.append(1.0 + ((d - 5.0) / 5.0) ** 2)
            
    ax.plot(deviations, penalties, color='#c0392b', linewidth=2.8, label=r'Shortfall Penalty $f(d)$')
    ax.axvline(5.0, color='black', linestyle='--', linewidth=1.2, label=r'Quadratic Threshold ($d = 5.0^\circ\mathrm{C}$)')
    
    # Shading
    ax.axvspan(0.0, 5.0, color='#2ecc71', alpha=0.15, label='Linear Penalty Regime ($f(d) = d/5.0$)')
    ax.axvspan(5.0, 10.0, color='#e74c3c', alpha=0.15, label=r'Quadratic Escalation ($f(d) = 1 + [(d-5)/5]^2$)')
    
    # Annotate critical points
    ax.scatter([0.0, 5.0, 10.0], [0.0, 1.0, 2.0], color='#c0392b', s=45, zorder=5)
    ax.annotate(r'$d=0^\circ\mathrm{C} \rightarrow f(d)=0.0$', (0.0, 0.0), xytext=(0.4, 0.22),
                arrowprops=dict(arrowstyle='->', color='black', lw=0.8), fontsize=9)
    ax.annotate(r'$d=5^\circ\mathrm{C} \rightarrow f(d)=1.0$', (5.0, 1.0), xytext=(3.0, 1.35),
                arrowprops=dict(arrowstyle='->', color='black', lw=0.8), fontsize=9)
    ax.annotate(r'$d=10^\circ\mathrm{C} \rightarrow f(d)=2.0$' + '\n(Discomfort Cliff)', (10.0, 2.0), xytext=(6.5, 2.2),
                arrowprops=dict(arrowstyle='->', color='black', lw=0.8), fontsize=9)
                
    ax.set_xlabel(r'Zone Temperature Deviation $d_v = \max(0, T_{\mathrm{low}} - T_v, T_v - T_{\mathrm{high}})$ [${}^\circ\mathrm{C}$]')
    ax.set_ylabel(r'Normalized Zone Comfort Shortfall $f(d_v)$')
    ax.set_title(r'Piecewise Quadratic Comfort Shortfall Penalty Function $f(d)$')
    ax.set_xlim(0, 10.5)
    ax.set_ylim(-0.1, 2.6)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper left', fontsize=8.5)
    
    plt.tight_layout()
    out_file = ASSETS_DIR / "figure_6_1_comfort_penalty.png"
    plt.savefig(out_file, bbox_inches='tight')
    plt.close()
    print(f"Generated {out_file}")

if __name__ == "__main__":
    generate_figure_4_1_thermal_diversity()
    generate_figure_5_1_climate_regimes()
    generate_figure_6_1_comfort_penalty()
    print("All visual assets successfully generated!")
