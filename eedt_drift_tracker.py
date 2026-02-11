"""
EEDT Drift Tracker: Lightweight T1 Monitoring
==============================================

Run this script MULTIPLE TIMES at different hours/days.
Each run measures current T1 and computes Scout's optimal
QEC interval. Comparing across runs demonstrates that:

  - T1 drifts over time (hardware fact)
  - Scout adapts its recommendation (EEDT's value)
  - Fixed strategy cannot adapt (its weakness)

Designed for minimal QPU time (~1 min per run).

Usage:
  python eedt_drift_tracker.py           # IBM Quantum
  python eedt_drift_tracker.py --local   # Local test
"""

import argparse
import json
import numpy as np
import os
from datetime import datetime


def connect(local=False):
    if local:
        from qiskit_aer import AerSimulator
        backend = AerSimulator()
        print("Mode: LOCAL")
        return None, backend
    else:
        from qiskit_ibm_runtime import QiskitRuntimeService
        token = os.environ.get("IBM_QUANTUM_TOKEN", "")
        if not token:
            token = input("IBM Quantum API Token: ").strip()
        service = QiskitRuntimeService(
            channel="ibm_quantum_platform", token=token)
        backends = service.backends(operational=True, min_num_qubits=3)
        backend = min(backends, key=lambda b: b.status().pending_jobs)
        print(f"Backend: {backend.name} ({backend.num_qubits}q)")
        return service, backend


def select_best_qubits(backend, local=False):
    """Pick 3 qubits with longest T1."""
    if local:
        return [0, 1, 2], [100e-6, 100e-6, 100e-6]

    target = backend.target
    t1_map = {}
    for i in range(backend.num_qubits):
        try:
            t1 = target.qubit_properties[i].t1
            if t1 and t1 > 0:
                t1_map[i] = t1
        except:
            pass

    sorted_q = sorted(t1_map, key=t1_map.get, reverse=True)[:3]
    t1_vals = [t1_map[q] * 1e6 for q in sorted_q]  # to µs

    for q, t in zip(sorted_q, t1_vals):
        print(f"  Qubit {q}: T1 = {t:.1f} µs")

    return sorted_q, t1_vals


def build_t1_circuits(qubits, delays_us):
    """T1 measurement: prepare |111>, delay, measure. Minimal set."""
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

    circuits = []
    for d in delays_us:
        qr = QuantumRegister(max(qubits) + 1, 'q')
        cr = ClassicalRegister(3, 'meas')
        qc = QuantumCircuit(qr, cr)

        for i, q in enumerate(qubits):
            qc.x(q)

        if d > 0:
            dt_val = int(d * 1e3 / 0.222)  # µs to dt
            for q in qubits:
                qc.delay(dt_val, q, unit='dt')

        for i, q in enumerate(qubits):
            qc.measure(q, i)

        circuits.append(qc)
    return circuits


def build_qec_circuit(qubits, interval_us, total_us=200):
    """3-qubit repetition code with mid-circuit measurement."""
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

    n_cycles = max(1, int(total_us / interval_us))
    delay_dt = int(interval_us * 1e3 / 0.222)

    qr = QuantumRegister(max(qubits) + 1, 'q')
    syn = ClassicalRegister(3, 'syn')
    out = ClassicalRegister(3, 'out')
    qc = QuantumCircuit(qr, syn, out)

    # Prepare |111>
    for q in qubits:
        qc.x(q)

    for _ in range(n_cycles):
        # Wait
        for q in qubits:
            qc.delay(delay_dt, q, unit='dt')

        # Syndrome measurement
        qc.measure(qubits[0], syn[0])
        qc.measure(qubits[1], syn[1])
        qc.measure(qubits[2], syn[2])

        # Majority vote correction
        with qc.if_test((syn, 0b110)):
            qc.x(qubits[0])
        with qc.if_test((syn, 0b101)):
            qc.x(qubits[1])
        with qc.if_test((syn, 0b011)):
            qc.x(qubits[2])

    # Final measurement
    qc.measure(qubits[0], out[0])
    qc.measure(qubits[1], out[1])
    qc.measure(qubits[2], out[2])

    return qc, n_cycles


def run_circuits(backend, circuits, shots, local=False):
    """Run circuits, return list of counts."""
    if local:
        from qiskit import transpile
        results = []
        for qc in circuits:
            t_qc = transpile(qc, backend)
            job = backend.run(t_qc, shots=shots)
            results.append(job.result().get_counts())
        return results
    else:
        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import SamplerV2 as Sampler

        sampler = Sampler(mode=backend)
        pm = generate_preset_pass_manager(
            optimization_level=1, backend=backend)

        results = []
        # Submit all as one batch for speed
        pubs = []
        for qc in circuits:
            isa = pm.run(qc)
            pubs.append((isa, None, shots))

        job = sampler.run(pubs)
        print(f"  Job: {job.job_id()} ({len(pubs)} circuits), waiting...")
        result = job.result()

        for i in range(len(circuits)):
            pub = result[i]
            counts = None
            for attr in sorted(dir(pub.data)):
                if attr.startswith('_'):
                    continue
                try:
                    reg = getattr(pub.data, attr)
                    c = reg.get_counts()
                    if isinstance(c, dict) and len(c) > 0:
                        counts = c
                        break
                except:
                    continue
            if counts is None:
                counts = {}
            results.append(counts)
        return results


def fit_t1(delays, survivals):
    """Fit A * exp(-t/T1) to survival data."""
    from scipy.optimize import curve_fit

    def exp_decay(t, A, T1):
        return A * np.exp(-t / T1)

    try:
        p0 = [max(survivals), 80.0]
        popt, _ = curve_fit(exp_decay, delays, survivals,
                            p0=p0, maxfev=5000)
        return popt[1], popt[0]  # T1, amplitude
    except:
        return None, None


def scout_optimal_interval(t1_us, threshold=0.82):
    """Scout's recommendation: optimal QEC interval based on T1."""
    if t1_us is None or t1_us <= 0:
        return 20.0  # fallback
    # Interval where survival drops to threshold
    interval = -t1_us * np.log(threshold)
    return max(5.0, min(interval, 100.0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--shots', type=int, default=4096)
    args = parser.parse_args()

    SHOTS = args.shots
    TOTAL_US = 200  # total experiment time

    print("=" * 60)
    print("EEDT Drift Tracker")
    print("=" * 60)

    service, backend = connect(local=args.local)
    qubits, cal_t1 = select_best_qubits(backend, local=args.local)

    # ========================================
    # Experiment 1: Quick T1 (5 points only)
    # ========================================
    print("\n--- T1 Measurement (5 points) ---")
    delays_us = [0, 20, 50, 100, 200]
    t1_circuits = build_t1_circuits(qubits, delays_us)

    t1_counts = run_circuits(backend, t1_circuits, SHOTS, local=args.local)

    survivals = []
    for counts in t1_counts:
        target_key = '111'
        total = sum(counts.values())
        surv = counts.get(target_key, 0) / max(total, 1)
        survivals.append(surv)
        
    for d, s in zip(delays_us, survivals):
        print(f"  {d:>5} µs: P(|111⟩) = {s:.4f}")

    t1_measured, amplitude = fit_t1(
        np.array(delays_us, dtype=float),
        np.array(survivals, dtype=float))

    if t1_measured:
        print(f"  Fitted T1 = {t1_measured:.1f} µs")
    else:
        print("  T1 fit failed, using default 80 µs")
        t1_measured = 80.0

    # ========================================
    # Experiment 2: QEC with 2 strategies
    # ========================================
    print("\n--- QEC Comparison ---")

    # Fixed 20µs
    qc_20, n20 = build_qec_circuit(qubits, 20, TOTAL_US)
    # Fixed 40µs
    qc_40, n40 = build_qec_circuit(qubits, 40, TOTAL_US)
    # No QEC (just wait)
    qc_none = build_t1_circuits(qubits, [TOTAL_US])[0]

    qec_counts = run_circuits(
        backend, [qc_none, qc_20, qc_40], SHOTS, local=args.local)

    results = {}
    labels = ['No QEC', 'QEC 20µs', 'QEC 40µs']
    cycles = [0, n20, n40]

    for label, counts, nc in zip(labels, qec_counts, cycles):
        total = sum(counts.values())
        surv = counts.get('111', 0) / max(total, 1)
        # Also check 'out' register format
        if surv == 0 and label != 'No QEC':
            # Try different key formats for multi-register
            for k, v in counts.items():
                bits = k.replace(' ', '')
                if bits[-3:] == '111' or bits[:3] == '111':
                    surv += v
            surv = surv / max(total, 1) if surv > 0 else 0

        results[label] = {'survival': surv, 'cycles': nc}
        print(f"  {label:<12}: P(|111⟩) = {surv:.4f} ({nc} cycles)")

    # ========================================
    # Scout Analysis
    # ========================================
    print("\n--- Scout Recommendation ---")
    scout_interval = scout_optimal_interval(t1_measured)
    scout_cycles = max(1, int(TOTAL_US / scout_interval))

    print(f"  Current T1 = {t1_measured:.1f} µs")
    print(f"  Scout recommends: {scout_interval:.1f} µs interval "
          f"({scout_cycles} cycles in {TOTAL_US} µs)")

    # ========================================
    # Load previous runs for comparison
    # ========================================
    history_file = "eedt_drift_history.json"
    if os.path.exists(history_file):
        with open(history_file) as f:
            history = json.load(f)
    else:
        history = []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    backend_name = getattr(backend, 'name', 'aer_simulator')

    run_data = {
        "timestamp": timestamp,
        "backend": backend_name,
        "qubits": qubits,
        "t1_measured": t1_measured,
        "scout_interval": scout_interval,
        "scout_cycles": scout_cycles,
        "qec_results": {k: v for k, v in results.items()},
        "t1_curve": {
            "delays_us": delays_us,
            "survivals": survivals
        }
    }
    history.append(run_data)

    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    print(f"\nRun #{len(history)} saved to {history_file}")

    # ========================================
    # Multi-run comparison (if we have history)
    # ========================================
    if len(history) >= 2:
        print("\n" + "=" * 60)
        print("T1 DRIFT ACROSS RUNS — EEDT's Value Proposition")
        print("=" * 60)
        print(f"{'Run':<5} {'Time':<18} {'T1 (µs)':<12} "
              f"{'Scout (µs)':<14} {'Fixed 20µs':<14}")
        print("-" * 63)

        for i, h in enumerate(history):
            t1 = h['t1_measured']
            si = h['scout_interval']
            fixed_surv = h['qec_results'].get('QEC 20µs', {}).get(
                'survival', 'N/A')
            if isinstance(fixed_surv, float):
                fixed_str = f"{fixed_surv:.4f}"
            else:
                fixed_str = str(fixed_surv)
            print(f"{i+1:<5} {h['timestamp']:<18} {t1:<12.1f} "
                  f"{si:<14.1f} {fixed_str:<14}")

        t1_values = [h['t1_measured'] for h in history]
        scout_intervals = [h['scout_interval'] for h in history]
        t1_range = max(t1_values) - min(t1_values)
        scout_range = max(scout_intervals) - min(scout_intervals)

        print(f"\nT1 drift range: {t1_range:.1f} µs")
        print(f"Scout interval adaptation: {scout_range:.1f} µs")
        print(f"Fixed strategy: always 20 µs (cannot adapt)")

        if t1_range > 10:
            print("\n⚡ Significant T1 drift detected!")
            print("   Fixed 20µs is suboptimal for at least one run.")
            print("   Scout adapts interval to match current conditions.")
        else:
            print("\n⏳ T1 relatively stable so far.")
            print("   Run again later to capture drift.")

    else:
        print("\n⏳ First run recorded. Run again at a different time")
        print("   to capture T1 drift and demonstrate EEDT adaptation.")
        print(f"\n   Previous data from 2/10: T1=75.3µs, Scout=15.0µs")
        print(f"   This run:               T1={t1_measured:.1f}µs, "
              f"Scout={scout_interval:.1f}µs")

    # ========================================
    # Plot
    # ========================================
    import matplotlib.pyplot as plt

    if len(history) >= 2:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # (A) T1 over time
        times = list(range(1, len(history) + 1))
        t1s = [h['t1_measured'] for h in history]
        axes[0].plot(times, t1s, 'ko-', markersize=10, linewidth=2)
        axes[0].set_xlabel('Run #', fontsize=12)
        axes[0].set_ylabel('T₁ (µs)', fontsize=12)
        axes[0].set_title('(A) T₁ Drift Over Time', fontsize=14)
        axes[0].grid(True, alpha=0.3)

        # (B) Scout interval adapts
        scouts = [h['scout_interval'] for h in history]
        axes[1].plot(times, scouts, 'rs-', markersize=10, linewidth=2,
                     label='Scout (adaptive)')
        axes[1].axhline(y=20, color='blue', linestyle='--', linewidth=2,
                        label='Fixed 20µs')
        axes[1].set_xlabel('Run #', fontsize=12)
        axes[1].set_ylabel('QEC Interval (µs)', fontsize=12)
        axes[1].set_title('(B) Scout Adapts, Fixed Cannot', fontsize=14)
        axes[1].legend(fontsize=11)
        axes[1].grid(True, alpha=0.3)

        # (C) T1 vs Scout interval correlation
        axes[2].scatter(t1s, scouts, c='red', s=100, zorder=5)
        axes[2].set_xlabel('Measured T₁ (µs)', fontsize=12)
        axes[2].set_ylabel('Scout Interval (µs)', fontsize=12)
        axes[2].set_title('(C) Scout Tracks T₁', fontsize=14)
        axes[2].grid(True, alpha=0.3)
        # Add trend line
        if len(t1s) >= 2:
            z = np.polyfit(t1s, scouts, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(t1s) * 0.9, max(t1s) * 1.1, 50)
            axes[2].plot(x_line, p(x_line), 'r--', alpha=0.5)

        plt.suptitle(f'EEDT Drift Tracker — {backend_name}',
                     fontsize=15, fontweight='bold')
        plt.tight_layout()
    else:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # T1 curve
        ax1.scatter(delays_us, survivals, c='black', s=60, zorder=5)
        if t1_measured and amplitude:
            t_fit = np.linspace(0, max(delays_us), 100)
            y_fit = amplitude * np.exp(-t_fit / t1_measured)
            ax1.plot(t_fit, y_fit, 'r--', label=f'T₁ = {t1_measured:.1f} µs')
        ax1.set_xlabel('Delay (µs)', fontsize=12)
        ax1.set_ylabel('P(|111⟩)', fontsize=12)
        ax1.set_title('(A) T₁ Baseline', fontsize=14)
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)

        # QEC comparison
        labels_plot = list(results.keys())
        survs = [results[l]['survival'] for l in labels_plot]
        colors = ['salmon', 'green', 'steelblue']
        ax2.bar(labels_plot, survs, color=colors, alpha=0.7)
        ax2.set_ylabel('P(|111⟩) after 200µs', fontsize=12)
        ax2.set_title('(B) QEC Strategy Comparison', fontsize=14)
        ax2.grid(axis='y', alpha=0.3)

        plt.suptitle(
            f'EEDT Drift Tracker Run #1 — {backend_name}\n'
            f'T₁={t1_measured:.1f}µs → Scout: {scout_interval:.1f}µs',
            fontsize=14, fontweight='bold')
        plt.tight_layout()

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fig_path = f"EEDT_Drift_{ts}.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\nFigure: {fig_path}")
    plt.show()


if __name__ == "__main__":
    main()
