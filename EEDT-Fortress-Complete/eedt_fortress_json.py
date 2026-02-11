import json
import numpy as np
from datetime import datetime
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, thermal_relaxation_error, depolarizing_error
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

# ============================================================================
# EEDT v3 FORTRESS - JSON Output Version
# ============================================================================

class QuantumFortress:
    """量子トリップワイヤーシステム - パリティ検証版"""
    
    def __init__(self, num_scouts=3):
        self.num_scouts = num_scouts
        self.total_qubits = 2 + num_scouts
        
    def build_circuit(self, simulate_attack=False):
        """量子セキュリティ回路"""
        qr = QuantumRegister(self.total_qubits, 'q')
        cr_scouts = ClassicalRegister(self.num_scouts, 'scouts')
        cr_temp = ClassicalRegister(1, 'temp')
        cr_data = ClassicalRegister(1, 'data')
        
        qc = QuantumCircuit(qr, cr_scouts, cr_temp, cr_data)
        
        qc.h(qr[0])
        qc.barrier(label='Vault')
        
        bus_idx = self.total_qubits - 1
        for i in range(1, self.num_scouts + 1):
            qc.h(qr[i])
            qc.cx(qr[i], qr[bus_idx])
        
        qc.barrier(label='Tripwire')
        
        if simulate_attack:
            qc.measure(qr[bus_idx], cr_temp[0])
            qc.barrier(label='ATTACK')
        else:
            qc.barrier(label='SAFE')
        
        for i in range(self.num_scouts):
            qc.h(qr[i + 1])
            qc.measure(qr[i + 1], cr_scouts[i])
        
        qc.barrier(label='Detection')
        
        qc.cx(qr[0], qr[bus_idx])
        qc.measure(qr[bus_idx], cr_data[0])
        
        return qc
    
    def analyze_detection_rate(self, counts_safe, counts_attack):
        """パリティベース検出"""
        def has_parity_violation(counts):
            total = sum(counts.values())
            violations = 0
            
            for bitstring, count in counts.items():
                parts = bitstring.split()
                
                if len(parts) >= 3:
                    scout_bits = parts[2]
                else:
                    bits = bitstring.replace(' ', '')
                    scout_bits = bits[-self.num_scouts:]
                
                if scout_bits == '0' * self.num_scouts or scout_bits == '1' * self.num_scouts:
                    pass
                else:
                    violations += count
            
            return violations / total if total > 0 else 0
        
        detection_rate = has_parity_violation(counts_attack)
        false_positive_rate = has_parity_violation(counts_safe)
        
        return {
            'detection_rate': detection_rate,
            'false_positive_rate': false_positive_rate,
            'safe_counts': counts_safe,
            'attack_counts': counts_attack
        }

def create_noise_model(t1=75e-6, t2=100e-6):
    """IBM実機ノイズモデル"""
    noise_model = NoiseModel()
    
    gate_times = {
        'h': 0.06e-6,
        'cx': 0.3e-6,
        'x': 0.06e-6,
        'measure': 1.0e-6
    }
    
    for gate in ['h', 'x', 'rz']:
        error = thermal_relaxation_error(t1, t2, gate_times.get(gate, 0.06e-6))
        noise_model.add_all_qubit_quantum_error(error, gate)
    
    cx_error = thermal_relaxation_error(t1, t2, gate_times['cx'])
    depol = depolarizing_error(0.01, 2)
    noise_model.add_all_qubit_quantum_error(cx_error.compose(depol), 'cx')
    
    noise_model.add_all_qubit_readout_error([[0.98, 0.02], [0.03, 0.97]])
    
    return noise_model

# ============================================================================
# JSON OUTPUT FUNCTIONS
# ============================================================================

def run_validation_for_json(num_scouts=3, shots=4000, noise_level='realistic'):
    """JSON出力用の検証実験"""
    fortress = QuantumFortress(num_scouts=num_scouts)
    
    # シミュレーター設定
    if noise_level == 'none':
        simulator = AerSimulator()
        noise_params = {'t1': None, 't2': None}
    elif noise_level == 'realistic':
        noise_model = create_noise_model(t1=75e-6, t2=100e-6)
        simulator = AerSimulator(noise_model=noise_model)
        noise_params = {'t1': 75e-6, 't2': 100e-6}
    elif noise_level == 'degraded':
        noise_model = create_noise_model(t1=3.4e-6, t2=5e-6)
        simulator = AerSimulator(noise_model=noise_model)
        noise_params = {'t1': 3.4e-6, 't2': 5e-6}
    
    # 正常動作
    qc_safe = fortress.build_circuit(simulate_attack=False)
    result_safe = simulator.run(transpile(qc_safe, simulator), shots=shots).result()
    counts_safe = result_safe.get_counts()
    
    # 攻撃
    qc_attack = fortress.build_circuit(simulate_attack=True)
    result_attack = simulator.run(transpile(qc_attack, simulator), shots=shots).result()
    counts_attack = result_attack.get_counts()
    
    # 分析
    analysis = fortress.analyze_detection_rate(counts_safe, counts_attack)
    
    # JSON用データ構造
    result = {
        'num_scouts': num_scouts,
        'shots': shots,
        'noise_level': noise_level,
        'noise_params': noise_params,
        'circuit_depth': qc_attack.depth(),
        'detection_rate': float(analysis['detection_rate']),
        'false_positive_rate': float(analysis['false_positive_rate']),
        'theoretical_detection_rate': float(1 - 0.5**num_scouts),
        'gap': float(abs((1 - 0.5**num_scouts) - analysis['detection_rate'])),
        'safe_distribution': {k: int(v) for k, v in sorted(counts_safe.items(), key=lambda x: -x[1])[:10]},
        'attack_distribution': {k: int(v) for k, v in sorted(counts_attack.items(), key=lambda x: -x[1])[:10]}
    }
    
    return result

def run_comprehensive_validation():
    """包括的検証を実行してJSON出力"""
    
    print("="*70)
    print("🔐 Running Comprehensive EEDT v3 FORTRESS Validation")
    print("="*70)
    
    # タイムスタンプ
    timestamp = datetime.now().isoformat()
    
    # 実験設定
    scout_configs = [1, 2, 3, 4, 5]
    noise_levels = ['none', 'realistic', 'degraded']
    
    # 全結果を格納
    all_results = {
        'metadata': {
            'timestamp': timestamp,
            'version': 'EEDT v3 FORTRESS',
            'description': 'Parity-based quantum intrusion detection validation',
            'author': '093',
            'framework': 'Qiskit Aer',
        },
        'experiments': {}
    }
    
    # 各ノイズレベルで実験
    for noise_level in noise_levels:
        print(f"\n{'='*70}")
        print(f"Testing with noise_level: {noise_level}")
        print('='*70)
        
        all_results['experiments'][noise_level] = []
        
        for num_scouts in scout_configs:
            print(f"  Running {num_scouts} scout(s)...", end=' ')
            
            try:
                result = run_validation_for_json(
                    num_scouts=num_scouts,
                    shots=4000,
                    noise_level=noise_level
                )
                all_results['experiments'][noise_level].append(result)
                print(f"✅ Det={result['detection_rate']*100:.1f}% FP={result['false_positive_rate']*100:.1f}%")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    # JSON保存
    output_file = f'eedt_fortress_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"💾 Results saved to: {output_file}")
    print('='*70)
    
    # サマリー表示
    print_summary(all_results)
    
    return output_file, all_results

def print_summary(results):
    """結果サマリーを表示"""
    print("\n" + "="*70)
    print("📊 VALIDATION SUMMARY")
    print("="*70)
    
    for noise_level, experiments in results['experiments'].items():
        print(f"\n### {noise_level.upper()} Environment ###\n")
        print("Scouts | Detection | False Pos | Theoretical | Gap")
        print("-" * 60)
        
        for exp in experiments:
            print(f"  {exp['num_scouts']}    | "
                  f"{exp['detection_rate']*100:6.1f}%   | "
                  f"{exp['false_positive_rate']*100:6.1f}%   | "
                  f"{exp['theoretical_detection_rate']*100:6.1f}%    | "
                  f"{exp['gap']*100:5.1f}%")
    
    print("\n" + "="*70)
    print("✅ Validation Complete!")
    print("="*70)

def create_comparison_plot(results):
    """比較プロット作成"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    noise_levels = ['none', 'realistic', 'degraded']
    
    for idx, noise_level in enumerate(noise_levels):
        ax = axes[idx]
        
        if noise_level not in results['experiments']:
            continue
        
        experiments = results['experiments'][noise_level]
        
        scouts = [exp['num_scouts'] for exp in experiments]
        detection = [exp['detection_rate'] * 100 for exp in experiments]
        false_pos = [exp['false_positive_rate'] * 100 for exp in experiments]
        theoretical = [exp['theoretical_detection_rate'] * 100 for exp in experiments]
        
        ax.plot(scouts, detection, 'o-', label='Detection Rate', 
                linewidth=2, markersize=8, color='blue')
        ax.plot(scouts, false_pos, 's-', label='False Positive', 
                linewidth=2, markersize=8, color='orange')
        ax.plot(scouts, theoretical, '--', label='Theoretical', 
                linewidth=2, alpha=0.7, color='green')
        
        ax.set_xlabel('Number of Scouts', fontsize=12)
        ax.set_ylabel('Rate (%)', fontsize=12)
        ax.set_title(f'{noise_level.upper()} Environment', fontsize=14)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(scouts)
        ax.set_ylim([0, 105])
    
    plt.tight_layout()
    filename = f'eedt_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n💾 Comparison plot saved to: {filename}")
    plt.show()
    
    return filename

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🛡️ "*25)
    print("EEDT v3 FORTRESS - JSON Output Mode")
    print("🛡️ "*25 + "\n")
    
    # 包括的検証実行
    output_file, results = run_comprehensive_validation()
    
    # 比較プロット作成
    plot_file = create_comparison_plot(results)
    
    # 最終メッセージ
    print("\n" + "="*70)
    print("🎯 FINAL OUTPUT")
    print("="*70)
    print(f"📄 JSON Data: {output_file}")
    print(f"📊 Comparison Plot: {plot_file}")
    print("\nYou can now:")
    print(f"  1. Load JSON in Python: json.load(open('{output_file}'))")
    print("  2. Analyze in Jupyter Notebook")
    print("  3. Share results with collaborators")
    print("  4. Submit to GitHub repository")
    print("="*70)
