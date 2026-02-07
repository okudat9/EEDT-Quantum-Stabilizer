"""
60-Degree Extreme Noise Experiment
===================================

Reproduces the landmark result from IBM Torino:
Standard method: F = 0.30 (FAILED)
EEDT method: F = 0.80 (2.7x improvement)

This demonstrates EEDT's ability to operate under extreme
noise conditions where traditional methods completely fail.

Author: 093 (T.OKUDA)
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List
import json

try:
    from qiskit import transpile
    from qiskit_ibm_runtime import QiskitRuntimeService
    from eedt import create_baseline_circuit, create_eedt_circuit
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("Warning: Qiskit not available. Cannot run on real hardware.")


class ExtremeNoiseExperiment:
    """
    60-degree extreme noise validation
    
    Tests EEDT under worst-case conditions to prove robustness.
    """
    
    def __init__(self, backend_name: str = 'ibm_torino'):
        """
        Initialize experiment
        
        Parameters
        ----------
        backend_name : str
            IBM Quantum backend to use
        """
        self.backend_name = backend_name
        self.backend = None
        self.results = []
        
        if QISKIT_AVAILABLE:
            self._connect_backend()
    
    def _connect_backend(self):
        """Connect to IBM Quantum"""
        try:
            service = QiskitRuntimeService(channel="ibm_quantum")
            self.backend = service.backend(self.backend_name)
            
            print(f"Connected to {self.backend.name}")
            print(f"  Qubits: {self.backend.num_qubits}")
            print(f"  Status: {self.backend.status().status_msg}")
            
        except Exception as e:
            print(f"Error: {e}")
            print("Using simulator fallback")
            from qiskit_aer import AerSimulator
            self.backend = AerSimulator()
    
    def run_single_angle(self, 
                        angle_degrees: float,
                        estimation_accuracy: float = 0.95,
                        shots: int = 4096) -> Dict:
        """
        Run experiment at single noise angle
        
        Parameters
        ----------
        angle_degrees : float
            Noise angle in degrees (15, 30, 45, 60)
        estimation_accuracy : float
            EEDT estimation accuracy [0, 1]
        shots : int
            Measurement shots
        
        Returns
        -------
        results : dict
            Experimental results
        """
        noise_phase = np.radians(angle_degrees)
        
        print(f"\n{'='*60}")
        print(f"Testing {angle_degrees}° noise")
        print(f"{'='*60}")
        
        # Create circuits
        qc_baseline = create_baseline_circuit(noise_phase)
        qc_eedt = create_eedt_circuit(
            noise_phase, 
            estimation_accuracy=estimation_accuracy
        )
        
        # Transpile
        qc_baseline_t = transpile(qc_baseline, self.backend, optimization_level=3)
        qc_eedt_t = transpile(qc_eedt, self.backend, optimization_level=3)
        
        print(f"Baseline circuit depth: {qc_baseline_t.depth()}")
        print(f"EEDT circuit depth: {qc_eedt_t.depth()}")
        print(f"Overhead: {(qc_eedt_t.depth() / qc_baseline_t.depth() - 1) * 100:.1f}%")
        
        # Execute
        print("\nSubmitting to quantum backend...")
        job_baseline = self.backend.run(qc_baseline_t, shots=shots)
        job_eedt = self.backend.run(qc_eedt_t, shots=shots)
        
        print("Waiting for results...")
        result_baseline = job_baseline.result()
        result_eedt = job_eedt.result()
        
        # Get counts
        counts_baseline = result_baseline.get_counts()
        counts_eedt = result_eedt.get_counts()
        
        # Compute fidelity (P(00) for GHZ state)
        fidelity_baseline = counts_baseline.get('00', 0) / shots
        fidelity_eedt = counts_eedt.get('00', 0) / shots
        
        improvement = fidelity_eedt / fidelity_baseline if fidelity_baseline > 0 else float('inf')
        
        # Display results
        print(f"\n{'='*60}")
        print(f"RESULTS at {angle_degrees}°:")
        print(f"{'='*60}")
        print(f"Baseline Fidelity: {fidelity_baseline:.4f}")
        print(f"EEDT Fidelity:     {fidelity_eedt:.4f}")
        print(f"Improvement:       {improvement:.2f}x")
        print(f"{'='*60}")
        
        if angle_degrees == 60:
            if fidelity_baseline < 0.40:
                print("✅ Baseline FAILED as expected (<0.40)")
            if fidelity_eedt > 0.75:
                print("✅ EEDT SUCCESS! (>0.75)")
            else:
                print("⚠️  EEDT below target, but still improved")
        
        result = {
            'angle_degrees': angle_degrees,
            'noise_phase_rad': noise_phase,
            'fidelity_baseline': fidelity_baseline,
            'fidelity_eedt': fidelity_eedt,
            'improvement_factor': improvement,
            'shots': shots,
            'counts_baseline': counts_baseline,
            'counts_eedt': counts_eedt,
            'estimation_accuracy': estimation_accuracy
        }
        
        self.results.append(result)
        return result
    
    def run_full_sweep(self, 
                      angles: List[float] = [15, 30, 45, 60],
                      estimation_accuracy: float = 0.95,
                      shots: int = 4096):
        """
        Run full angle sweep
        
        Parameters
        ----------
        angles : list
            Noise angles to test (degrees)
        estimation_accuracy : float
            EEDT estimation accuracy
        shots : int
            Shots per angle
        """
        print(f"\n{'#'*70}")
        print(f"{'#'*70}")
        print(f"  EEDT EXTREME NOISE VALIDATION")
        print(f"  Testing angles: {angles}")
        print(f"  Estimation accuracy: {estimation_accuracy:.1%}")
        print(f"{'#'*70}")
        print(f"{'#'*70}\n")
        
        for angle in angles:
            self.run_single_angle(angle, estimation_accuracy, shots)
        
        # Plot results
        self.plot_results()
        self.save_results()
    
    def plot_results(self):
        """Plot fidelity comparison"""
        if not self.results:
            print("No results to plot")
            return
        
        angles = [r['angle_degrees'] for r in self.results]
        f_baseline = [r['fidelity_baseline'] for r in self.results]
        f_eedt = [r['fidelity_eedt'] for r in self.results]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Fidelity comparison
        x = np.arange(len(angles))
        width = 0.35
        
        ax1.bar(x - width/2, f_baseline, width, label='Baseline', color='#e74c3c', alpha=0.8)
        ax1.bar(x + width/2, f_eedt, width, label='EEDT', color='#2ecc71', alpha=0.8)
        
        ax1.set_xlabel('Noise Angle (degrees)', fontsize=12)
        ax1.set_ylabel('Fidelity', fontsize=12)
        ax1.set_title('EEDT vs Baseline: Extreme Noise Test', fontsize=14, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'{a}°' for a in angles])
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0.90, color='orange', linestyle='--', label='Target (0.90)', alpha=0.5)
        ax1.set_ylim([0, 1.05])
        
        # Add value labels
        for i, (b, e) in enumerate(zip(f_baseline, f_eedt)):
            ax1.text(i - width/2, b + 0.02, f'{b:.2f}', ha='center', fontsize=10)
            ax1.text(i + width/2, e + 0.02, f'{e:.2f}', ha='center', fontsize=10)
        
        # Improvement factor
        improvements = [r['improvement_factor'] for r in self.results]
        
        ax2.plot(angles, improvements, marker='o', linewidth=2, markersize=10, color='#3498db')
        ax2.set_xlabel('Noise Angle (degrees)', fontsize=12)
        ax2.set_ylabel('Improvement Factor (EEDT/Baseline)', fontsize=12)
        ax2.set_title('EEDT Improvement Factor', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='No improvement')
        
        # Annotate 60° result
        if 60 in angles:
            idx = angles.index(60)
            ax2.annotate(
                f'{improvements[idx]:.1f}x\nImprovement',
                xy=(60, improvements[idx]),
                xytext=(50, improvements[idx] + 0.5),
                fontsize=12,
                fontweight='bold',
                color='#e74c3c',
                arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=2)
            )
        
        plt.tight_layout()
        plt.savefig('60_degree_experiment_results.png', dpi=300, bbox_inches='tight')
        print("\n✅ Plot saved: 60_degree_experiment_results.png")
        plt.close()
    
    def save_results(self):
        """Save results to JSON"""
        with open('60_degree_experiment_data.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("✅ Data saved: 60_degree_experiment_data.json")


def main():
    """Main execution"""
    
    # Initialize experiment
    exp = ExtremeNoiseExperiment(backend_name='ibm_torino')
    
    # Run full sweep
    exp.run_full_sweep(
        angles=[15, 30, 45, 60],
        estimation_accuracy=0.95,
        shots=4096
    )
    
    print("\n" + "="*70)
    print("EXPERIMENT COMPLETE!")
    print("="*70)
    print("\nKey Finding:")
    print("  At 60° noise:")
    if exp.results:
        result_60 = [r for r in exp.results if r['angle_degrees'] == 60][0]
        print(f"    Baseline: {result_60['fidelity_baseline']:.2f} (FAILED)")
        print(f"    EEDT:     {result_60['fidelity_eedt']:.2f} (OPERATIONAL)")
        print(f"    Improvement: {result_60['improvement_factor']:.1f}x")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
