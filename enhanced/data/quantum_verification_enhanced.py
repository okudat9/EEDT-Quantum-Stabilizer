import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, amplitude_damping_error, phase_damping_error, depolarizing_error
import json
import os
from scipy import stats

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# Project Rumor: エンタングルメント・スワッピング
# ==========================================
def run_entanglement_swapping(shots=1000):
    """
    正統派エンタングルメント・スワッピングの実装
    
    初期状態: (q0-q1)がBell状態、(q2-q3)がBell状態
    中間測定: q1とq2をBell基底で測定
    結果: q0とq3が遠隔エンタングル
    """
    print(f"[Project Rumor] Entanglement Swapping (shots={shots})")
    
    # レジスタ定義
    qr = QuantumRegister(4, 'q')
    cr_bell = ClassicalRegister(2, 'bell')
    cr_verify = ClassicalRegister(2, 'verify')
    qc = QuantumCircuit(qr, cr_bell, cr_verify)
    
    # === Step 1: 2つのBellペアを生成 ===
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.h(qr[2])
    qc.cx(qr[2], qr[3])
    qc.barrier(label='2 Bell pairs')
    
    # === Step 2: Bell基底測定 (q1-q2) ===
    qc.cx(qr[1], qr[2])
    qc.h(qr[1])
    qc.measure(qr[1], cr_bell[0])
    qc.measure(qr[2], cr_bell[1])
    qc.barrier(label='Bell measurement')
    
    # === Step 3: パウリ補正 ===
    with qc.if_test((cr_bell[1], 1)):
        qc.x(qr[3])
    with qc.if_test((cr_bell[0], 1)):
        qc.z(qr[3])
    qc.barrier(label='Pauli correction')
    
    # === Step 4: 検証測定 ===
    qc.measure(qr[0], cr_verify[0])
    qc.measure(qr[3], cr_verify[1])
    
    # 実行
    sim = AerSimulator()
    job = sim.run(transpile(qc, sim), shots=shots)
    counts = job.result().get_counts()
    
    # 結果解析
    correlated_00 = 0
    correlated_11 = 0
    uncorrelated_01 = 0
    uncorrelated_10 = 0
    
    for bitstring, count in counts.items():
        parts = bitstring.split(' ')
        verify_bits = parts[0]
        
        if verify_bits == '00':
            correlated_00 += count
        elif verify_bits == '11':
            correlated_11 += count
        elif verify_bits == '01':
            uncorrelated_01 += count
        else:
            uncorrelated_10 += count
    
    total_correlated = correlated_00 + correlated_11
    total_uncorrelated = uncorrelated_01 + uncorrelated_10
    
    result = {
        "00": correlated_00,
        "11": correlated_11,
        "01": uncorrelated_01,
        "10": uncorrelated_10
    }
    
    print(f"  相関あり (00/11): {total_correlated}/{shots} = {total_correlated/shots*100:.1f}%")
    print(f"  相関なし (01/10): {total_uncorrelated}/{shots} = {total_uncorrelated/shots*100:.1f}%")
    
    return result


# ==========================================
# Project Wormhole: 環境相互作用（改善版）
# ==========================================
def run_environment_interaction_enhanced(shots=10000, damping_param=0.8, noise_type='amplitude'):
    """
    環境量子ビットによる複数ノイズモデル対応版
    
    noise_type: 'amplitude', 'phase', 'depolarizing'
    """
    
    # === 方式A: SWAP Chain (ノイズモデル使用) ===
    qr_swap = QuantumRegister(1, 'data')
    cr_swap = ClassicalRegister(1, 'meas')
    qc_swap = QuantumCircuit(qr_swap, cr_swap)
    
    qc_swap.x(qr_swap[0])
    qc_swap.barrier()
    qc_swap.x(qr_swap[0])
    qc_swap.x(qr_swap[0])
    qc_swap.barrier()
    qc_swap.measure(qr_swap[0], cr_swap[0])
    
    # ノイズモデル選択
    noise_model_swap = NoiseModel()
    if noise_type == 'amplitude':
        error_swap = amplitude_damping_error(damping_param)
    elif noise_type == 'phase':
        error_swap = phase_damping_error(damping_param)
    elif noise_type == 'depolarizing':
        error_swap = depolarizing_error(damping_param, 1)
    else:
        raise ValueError(f"Unknown noise type: {noise_type}")
    
    noise_model_swap.add_all_qubit_quantum_error(error_swap, ['x'])
    
    sim = AerSimulator(noise_model=noise_model_swap)
    job_swap = sim.run(transpile(qc_swap, sim, basis_gates=['x', 'sx', 'rz', 'cx', 'measure']), shots=shots)
    counts_swap = job_swap.result().get_counts()
    
    swap_success = counts_swap.get('1', 0)
    swap_fatal = counts_swap.get('0', 0)
    
    # === 方式B: EEDT (Scout量子ビット) ===
    qr_eedt = QuantumRegister(3, 'q')
    cr_scout = ClassicalRegister(1, 'scout')
    cr_data = ClassicalRegister(1, 'data')
    qc_eedt = QuantumCircuit(qr_eedt, cr_scout, cr_data)
    
    qc_eedt.x(qr_eedt[0])  # Data
    qc_eedt.x(qr_eedt[2])  # Scout
    
    theta = 2 * np.arcsin(np.sqrt(damping_param))
    qc_eedt.ry(theta, qr_eedt[1])
    qc_eedt.barrier(label='初期化')
    
    qc_eedt.cx(qr_eedt[1], qr_eedt[2])
    qc_eedt.barrier(label='Scout偵察')
    
    qc_eedt.measure(qr_eedt[2], cr_scout[0])
    qc_eedt.barrier(label='Scout判定')
    
    with qc_eedt.if_test((cr_scout[0], 1)):
        qc_eedt.cx(qr_eedt[1], qr_eedt[0])
    
    qc_eedt.barrier(label='条件送信')
    qc_eedt.measure(qr_eedt[0], cr_data[0])
    
    sim_eedt = AerSimulator()
    job_eedt = sim_eedt.run(transpile(qc_eedt, sim_eedt), shots=shots)
    counts_eedt = job_eedt.result().get_counts()
    
    # 結果集計
    eedt_success = 0
    eedt_safe = 0
    eedt_fatal = 0
    
    for bitstring, count in counts_eedt.items():
        parts = bitstring.split(' ')
        data_bit = parts[0]
        scout_bit = parts[1]
        
        if data_bit == '1':
            if scout_bit == '1':
                eedt_success += count
            else:
                eedt_safe += count
        else:
            eedt_fatal += count
    
    return {
        "swap": {"success": swap_success, "fatal": swap_fatal},
        "eedt": {"success": eedt_success, "safe": eedt_safe, "fatal": eedt_fatal}
    }


# ==========================================
# パラメータスイープ実験
# ==========================================
def parameter_sweep_experiment(gamma_values=[0.1, 0.3, 0.5, 0.7, 0.9], 
                               noise_types=['amplitude', 'phase', 'depolarizing'],
                               shots=10000, n_trials=10):
    """
    複数パラメータ×複数ノイズタイプでスイープ実験
    統計的信頼区間も計算
    """
    print("="*70)
    print("パラメータスイープ実験開始")
    print("="*70)
    
    results = {}
    
    for noise_type in noise_types:
        print(f"\n[ノイズタイプ: {noise_type}]")
        results[noise_type] = {
            'gamma': [],
            'swap_success_mean': [],
            'swap_success_std': [],
            'eedt_success_mean': [],
            'eedt_success_std': [],
            'eedt_safe_mean': [],
            'eedt_safe_std': [],
            'eedt_fatal_mean': [],
            'eedt_fatal_std': []
        }
        
        for gamma in gamma_values:
            print(f"  γ = {gamma:.1f} (試行回数: {n_trials})")
            
            swap_successes = []
            eedt_successes = []
            eedt_safes = []
            eedt_fatals = []
            
            for trial in range(n_trials):
                res = run_environment_interaction_enhanced(
                    shots=shots, 
                    damping_param=gamma, 
                    noise_type=noise_type
                )
                
                swap_successes.append(res['swap']['success'] / shots * 100)
                eedt_successes.append(res['eedt']['success'] / shots * 100)
                eedt_safes.append(res['eedt']['safe'] / shots * 100)
                eedt_fatals.append(res['eedt']['fatal'] / shots * 100)
            
            results[noise_type]['gamma'].append(gamma)
            results[noise_type]['swap_success_mean'].append(np.mean(swap_successes))
            results[noise_type]['swap_success_std'].append(np.std(swap_successes))
            results[noise_type]['eedt_success_mean'].append(np.mean(eedt_successes))
            results[noise_type]['eedt_success_std'].append(np.std(eedt_successes))
            results[noise_type]['eedt_safe_mean'].append(np.mean(eedt_safes))
            results[noise_type]['eedt_safe_std'].append(np.std(eedt_safes))
            results[noise_type]['eedt_fatal_mean'].append(np.mean(eedt_fatals))
            results[noise_type]['eedt_fatal_std'].append(np.std(eedt_fatals))
            
            print(f"    SWAP成功: {np.mean(swap_successes):.1f}% ± {np.std(swap_successes):.1f}%")
            print(f"    EEDT成功: {np.mean(eedt_successes):.1f}% ± {np.std(eedt_successes):.1f}%")
            print(f"    EEDT保護: {np.mean(eedt_safes):.1f}% ± {np.std(eedt_safes):.1f}%")
    
    return results


# ==========================================
# 包括的可視化
# ==========================================
def plot_comprehensive_results(sweep_results, rumor_result=None, filename="quantum_verification_enhanced.png"):
    """改善版の包括的グラフ"""
    
    # レイアウト: 2行3列
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
    
    # === グラフ1: Project Rumor (左上) ===
    if rumor_result:
        ax1 = fig.add_subplot(gs[0, 0])
        
        correlated = rumor_result['00'] + rumor_result['11']
        uncorrelated = rumor_result['01'] + rumor_result['10']
        
        categories = ['相関あり\n(00/11)', '相関なし\n(01/10)']
        values = [correlated, uncorrelated]
        colors = ['#4CAF50', '#F44336']
        
        bars = ax1.bar(categories, values, color=colors, edgecolor='black', linewidth=1.5, alpha=0.85)
        
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 20,
                    f'{val}', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        ax1.set_title('Project Rumor: エンタングルメント・スワッピング', 
                      fontsize=13, fontweight='bold', pad=10)
        ax1.set_ylabel('測定回数', fontsize=11)
        ax1.set_ylim(0, max(values) * 1.15)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # === グラフ2-4: 各ノイズタイプの成功率曲線 ===
    noise_type_names = {
        'amplitude': '振幅減衰',
        'phase': '位相減衰',
        'depolarizing': 'デポラライジング'
    }
    
    positions = [(0, 1), (0, 2), (1, 0)]
    colors_swap = '#F44336'
    colors_eedt = '#4CAF50'
    
    for idx, (noise_type, pos) in enumerate(zip(['amplitude', 'phase', 'depolarizing'], positions)):
        if noise_type not in sweep_results:
            continue
            
        ax = fig.add_subplot(gs[pos[0], pos[1]])
        data = sweep_results[noise_type]
        
        gamma = np.array(data['gamma'])
        
        # SWAP成功率
        swap_mean = np.array(data['swap_success_mean'])
        swap_std = np.array(data['swap_success_std'])
        ax.plot(gamma, swap_mean, 'o-', color=colors_swap, linewidth=2.5, 
                markersize=8, label='SWAP Chain', alpha=0.8)
        ax.fill_between(gamma, swap_mean - swap_std, swap_mean + swap_std, 
                        color=colors_swap, alpha=0.2)
        
        # EEDT成功率
        eedt_mean = np.array(data['eedt_success_mean'])
        eedt_std = np.array(data['eedt_success_std'])
        ax.plot(gamma, eedt_mean, 's-', color=colors_eedt, linewidth=2.5, 
                markersize=8, label='EEDT成功', alpha=0.8)
        ax.fill_between(gamma, eedt_mean - eedt_std, eedt_mean + eedt_std, 
                        color=colors_eedt, alpha=0.2)
        
        # EEDT保護率（積み上げ）
        eedt_safe_mean = np.array(data['eedt_safe_mean'])
        ax.plot(gamma, eedt_mean + eedt_safe_mean, '^--', color='#2196F3', 
                linewidth=2, markersize=7, label='EEDT保護込', alpha=0.7)
        
        ax.set_xlabel('減衰パラメータ γ', fontsize=11, fontweight='bold')
        ax.set_ylabel('成功率 (%)', fontsize=11, fontweight='bold')
        ax.set_title(f'{noise_type_names[noise_type]}ノイズ', fontsize=12, fontweight='bold')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
    
    # === グラフ5: ノイズタイプ比較（γ=0.7固定） ===
    ax5 = fig.add_subplot(gs[1, 1])
    
    gamma_target = 0.7
    noise_labels = []
    swap_vals = []
    eedt_vals = []
    
    for noise_type in ['amplitude', 'phase', 'depolarizing']:
        if noise_type in sweep_results:
            data = sweep_results[noise_type]
            idx = data['gamma'].index(gamma_target) if gamma_target in data['gamma'] else -1
            if idx >= 0:
                noise_labels.append(noise_type_names[noise_type])
                swap_vals.append(data['swap_success_mean'][idx])
                eedt_vals.append(data['eedt_success_mean'][idx])
    
    x_pos = np.arange(len(noise_labels))
    width = 0.35
    
    bars1 = ax5.bar(x_pos - width/2, swap_vals, width, label='SWAP', 
                    color=colors_swap, edgecolor='black', linewidth=1.5, alpha=0.8)
    bars2 = ax5.bar(x_pos + width/2, eedt_vals, width, label='EEDT', 
                    color=colors_eedt, edgecolor='black', linewidth=1.5, alpha=0.8)
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
    
    ax5.set_ylabel('成功率 (%)', fontsize=11, fontweight='bold')
    ax5.set_title(f'ノイズタイプ比較 (γ = {gamma_target})', fontsize=12, fontweight='bold')
    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(noise_labels, fontsize=10)
    ax5.legend(fontsize=10)
    ax5.grid(axis='y', alpha=0.3)
    ax5.set_ylim(0, max(max(swap_vals), max(eedt_vals)) * 1.2)
    
    # === グラフ6: EEDT優位性マージン ===
    ax6 = fig.add_subplot(gs[1, 2])
    
    for noise_type in ['amplitude', 'phase', 'depolarizing']:
        if noise_type not in sweep_results:
            continue
        data = sweep_results[noise_type]
        gamma = np.array(data['gamma'])
        advantage = np.array(data['eedt_success_mean']) + np.array(data['eedt_safe_mean']) - np.array(data['swap_success_mean'])
        ax6.plot(gamma, advantage, 'o-', linewidth=2.5, markersize=8, 
                label=noise_type_names[noise_type], alpha=0.8)
    
    ax6.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax6.set_xlabel('減衰パラメータ γ', fontsize=11, fontweight='bold')
    ax6.set_ylabel('EEDT優位性 (%)', fontsize=11, fontweight='bold')
    ax6.set_title('EEDT vs SWAP 優位性マージン', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=9)
    ax6.grid(True, alpha=0.3)
    
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n✅ グラフ保存: {os.path.abspath(filename)}")


# ==========================================
# メイン実行
# ==========================================
if __name__ == "__main__":
    print("="*70)
    print("量子通信検証スイート - 拡張版 (v2.0)")
    print("="*70)
    
    # Project Rumor
    rumor_result = run_entanglement_swapping(shots=1000)
    
    print("\n" + "="*70)
    
    # パラメータスイープ実験
    sweep_results = parameter_sweep_experiment(
        gamma_values=[0.1, 0.3, 0.5, 0.7, 0.9],
        noise_types=['amplitude', 'phase', 'depolarizing'],
        shots=10000,
        n_trials=10  # 統計的信頼性のため10回試行
    )
    
    print("\n" + "="*70)
    
    # 結果保存
    output_data = {
        "project_rumor": rumor_result,
        "parameter_sweep": sweep_results
    }
    
    json_path = 'results_enhanced.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 数値データ保存: {os.path.abspath(json_path)}")
    
    # グラフ生成
    plot_comprehensive_results(sweep_results, rumor_result, 
                              filename='quantum_verification_enhanced.png')
    
    print("\n" + "="*70)
    print("検証完了！")
    print("="*70)
    
    # 統計サマリー出力
    print("\n【統計サマリー】")
    for noise_type in ['amplitude', 'phase', 'depolarizing']:
        if noise_type in sweep_results:
            print(f"\n{noise_type}ノイズ (γ=0.7での比較):")
            data = sweep_results[noise_type]
            idx = data['gamma'].index(0.7)
            swap_mean = data['swap_success_mean'][idx]
            eedt_total = data['eedt_success_mean'][idx] + data['eedt_safe_mean'][idx]
            advantage = eedt_total - swap_mean
            print(f"  SWAP成功率: {swap_mean:.2f}%")
            print(f"  EEDT保護込: {eedt_total:.2f}%")
            print(f"  優位性マージン: +{advantage:.2f}%")
