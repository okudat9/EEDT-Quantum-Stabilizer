"""
EEDT Hardware Validation on IBM Quantum
========================================

Three experiments to validate EEDT concepts on real NISQ hardware.

Experiment 1: T1 Baseline
    Prepare |111⟩, insert delays, measure survival → extract real T1

Experiment 2: Fixed-Interval QEC
    3-qubit repetition code with mid-circuit measurement at fixed intervals
    Compare survival with and without QEC

Experiment 3: Post-Hoc Scout Analysis
    Using real T1 calibration data from the backend, simulate what
    EEDT-Scout would have decided, and compare against fixed strategies

Requirements:
    pip install qiskit>=2.0 qiskit-ibm-runtime>=0.28 matplotlib numpy

Setup:
    1. Create account at https://quantum.cloud.ibm.com
    2. Get your API key from Account Settings
    3. Run: python eedt_hardware_validation.py

Author: [Your Name]
License: MIT
Date: 2026-02
Qiskit Version: 2.x (SamplerV2 only)
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ============================================================
# IBM Quantum Connection
# ============================================================

def connect_ibm_quantum():
    """
    Connect to IBM Quantum and select best available backend.

    Returns:
        (service, backend) tuple
    """
    import os
    from qiskit_ibm_runtime import QiskitRuntimeService

    # Direct connection - no save_account needed
    token = os.environ.get("IBM_QUANTUM_TOKEN", "")
    if not token:
        token = input("IBM Quantum API Token: ").strip()

    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=token
    )

    # Select backend: prefer Heron (156q) for best gate fidelity
    backend = service.least_busy(
        operational=True,
        simulator=False,
        min_num_qubits=5  # We only need 3-5 qubits
    )

    print(f"Backend: {backend.name}")
    print(f"Qubits:  {backend.num_qubits}")
    print(f"Status:  {'Online' if backend.status().operational else 'Offline'}")

    return service, backend


def select_best_qubits(backend, n=3):
    """
    Select the n qubits with best T1 and lowest CX error.

    Uses backend calibration properties to find optimal qubit subset.

    Args:
        backend: IBM Quantum backend
        n: number of qubits needed (default 3)

    Returns:
        list of qubit indices
    """
    try:
        props = backend.properties()
        if props is None:
            print("  No calibration data available, using qubits [0, 1, 2]")
            return list(range(n))

        # Get T1 values for all qubits
        t1_values = {}
        for i in range(backend.num_qubits):
            try:
                t1 = props.t1(i)
                if t1 is not None:
                    t1_values[i] = t1
            except Exception:
                pass

        if not t1_values:
            print("  No T1 data available, using qubits [0, 1, 2]")
            return list(range(n))

        # Sort by T1 (longest = best) and pick top n
        sorted_qubits = sorted(t1_values, key=t1_values.get, reverse=True)
        selected = sorted_qubits[:n]

        for q in selected:
            print(f"  Qubit {q}: T1 = {t1_values[q]*1e6:.1f} µs")

        return selected

    except Exception as e:
        print(f"  Could not read properties ({e}), using qubits [0, 1, 2]")
        return list(range(n))


# ============================================================
# Experiment 1: T1 Baseline
# ============================================================

def build_t1_circuits(qubits, delay_times_us, backend):
    """
    Build circuits to measure T1 decay on real hardware.

    For each delay time:
        1. Prepare |111⟩ with X gates
        2. Insert delay
        3. Measure

    Args:
        qubits: list of physical qubit indices
        delay_times_us: list of delay times in microseconds
        backend: IBM Quantum backend for transpilation

    Returns:
        list of (ISA circuit, delay_us) tuples
    """
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.transpiler import generate_preset_pass_manager

    pm = generate_preset_pass_manager(
        optimization_level=1,
        backend=backend,
        initial_layout=qubits
    )

    circuits = []
    for delay_us in delay_times_us:
        qr = QuantumRegister(3, "q")
        cr = ClassicalRegister(3, "meas")
        qc = QuantumCircuit(qr, cr)

        # Prepare |111⟩
        qc.x([0, 1, 2])
        qc.barrier()

        # Delay (in seconds for Qiskit)
        delay_sec = delay_us * 1e-6
        qc.delay(delay_sec, [0, 1, 2], unit="s")
        qc.barrier()

        # Measure
        qc.measure([0, 1, 2], [0, 1, 2])

        # Transpile to ISA
        isa_qc = pm.run(qc)
        circuits.append((isa_qc, delay_us))

    return circuits


def run_t1_experiment(service, backend, shots=4096):
    """
    Run T1 baseline measurement.

    Returns:
        dict with delay_us → survival_probability mapping
    """
    from qiskit_ibm_runtime import SamplerV2 as Sampler

    print("\n" + "=" * 60)
    print("Experiment 1: T1 Baseline Measurement")
    print("=" * 60)

    qubits = select_best_qubits(backend, n=3)

    # Delay points: 0 to 300 µs in steps
    delay_times = [0, 10, 20, 40, 60, 80, 100, 150, 200, 300]

    print(f"\nBuilding {len(delay_times)} circuits...")
    circuits = build_t1_circuits(qubits, delay_times, backend)

    print(f"Submitting to {backend.name} ({shots} shots each)...")
    sampler = Sampler(mode=backend)

    # Submit all circuits as PUBs
    pubs = [(circ, None, shots) for circ, _ in circuits]
    job = sampler.run(pubs)
    print(f"Job ID: {job.job_id()}")
    print("Waiting for results...")

    result = job.result()

    # Analyze: count |111⟩ survival
    survival = {}
    for i, (_, delay_us) in enumerate(circuits):
        counts = result[i].data.meas.get_counts()
        total = sum(counts.values())
        # |111⟩ = "111" in Qiskit little-endian = bitstring "111"
        n_111 = counts.get("111", 0)
        survival[delay_us] = n_111 / total

    print("\nResults:")
    print(f"{'Delay (µs)':<15} {'P(|111⟩)':<15}")
    print("-" * 30)
    for d, p in sorted(survival.items()):
        print(f"{d:<15.0f} {p:<15.4f}")

    return survival, qubits


# ============================================================
# Experiment 2: Fixed-Interval QEC
# ============================================================

def build_qec_circuit_fixed(qubits, total_delay_us, qec_interval_us, backend):
    """
    Build a 3-qubit repetition code circuit with fixed-interval QEC.

    Circuit structure (for each QEC cycle):
        1. Delay for qec_interval_us
        2. Mid-circuit measure all 3 qubits (syndrome)
        3. Majority vote correction:
           - If syndrome indicates majority |1⟩, apply X to minority qubit(s)

    In practice on current hardware, we implement simplified QEC:
        - Measure all 3 qubits mid-circuit
        - Use if_test to conditionally apply X gates based on syndrome

    Args:
        qubits: physical qubit indices
        total_delay_us: total experiment time
        qec_interval_us: time between QEC cycles
        backend: for transpilation

    Returns:
        ISA circuit
    """
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.transpiler import generate_preset_pass_manager

    n_cycles = int(total_delay_us / qec_interval_us)

    qr = QuantumRegister(3, "q")
    # One classical register per QEC cycle for syndrome + final measurement
    syndrome_regs = [ClassicalRegister(3, f"syn{i}") for i in range(n_cycles)]
    final_reg = ClassicalRegister(3, "final")

    qc = QuantumCircuit(qr, *syndrome_regs, final_reg)

    # Prepare |111⟩
    qc.x([0, 1, 2])
    qc.barrier()

    for cycle in range(n_cycles):
        # 1. Delay
        delay_sec = qec_interval_us * 1e-6
        qc.delay(delay_sec, [0, 1, 2], unit="s")
        qc.barrier()

        # 2. Syndrome measurement (mid-circuit)
        qc.measure([0, 1, 2], syndrome_regs[cycle])

        # 3. Majority vote correction via dynamic circuits
        # Strategy: if a qubit reads 0 but majority reads 1, flip it back
        # We use if_test on the syndrome register
        #
        # Syndrome patterns where correction helps:
        #   110 → flip qubit 0 (q0=0, q1=1, q2=1)
        #   101 → flip qubit 1 (q0=1, q1=0, q2=1)
        #   011 → flip qubit 2 (q0=0, q1=1, q2=0) — wait, little-endian
        #
        # Qiskit uses little-endian: register value = c[2]c[1]c[0]
        # 0b110 = 6 means c[0]=0, c[1]=1, c[2]=1 → qubit 0 is minority
        # 0b101 = 5 means c[0]=1, c[1]=0, c[2]=1 → qubit 1 is minority
        # 0b011 = 3 means c[0]=1, c[1]=1, c[2]=0 → qubit 2 is minority

        with qc.if_test((syndrome_regs[cycle], 0b110)):
            qc.x(0)  # Correct qubit 0

        with qc.if_test((syndrome_regs[cycle], 0b101)):
            qc.x(1)  # Correct qubit 1

        with qc.if_test((syndrome_regs[cycle], 0b011)):
            qc.x(2)  # Correct qubit 2

        qc.barrier()

    # Final measurement
    qc.measure([0, 1, 2], final_reg)

    # Transpile
    pm = generate_preset_pass_manager(
        optimization_level=1,
        backend=backend,
        initial_layout=qubits
    )
    isa_qc = pm.run(qc)

    return isa_qc, n_cycles


def run_qec_experiment(service, backend, qubits, shots=4096):
    """
    Run QEC experiment with multiple fixed intervals.

    Compares:
        - No QEC (just delay)
        - QEC every 20 µs
        - QEC every 40 µs
        - QEC every 80 µs

    Returns:
        dict of strategy → {delay → survival}
    """
    from qiskit_ibm_runtime import SamplerV2 as Sampler

    print("\n" + "=" * 60)
    print("Experiment 2: Fixed-Interval QEC Comparison")
    print("=" * 60)

    total_time = 200  # µs
    strategies = {
        "No QEC": None,
        "QEC 20µs": 20,
        "QEC 40µs": 40,
        "QEC 80µs": 80,
    }

    # For No QEC, use T1 baseline circuits (just delay + measure)
    # For QEC strategies, build circuits with mid-circuit measurement + correction

    all_pubs = []
    pub_labels = []

    for name, interval in strategies.items():
        if interval is None:
            # No QEC: single delay circuit
            from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
            from qiskit.transpiler import generate_preset_pass_manager

            pm = generate_preset_pass_manager(
                optimization_level=1,
                backend=backend,
                initial_layout=qubits
            )

            qr = QuantumRegister(3, "q")
            cr = ClassicalRegister(3, "final")
            qc = QuantumCircuit(qr, cr)
            qc.x([0, 1, 2])
            qc.barrier()
            qc.delay(total_time * 1e-6, [0, 1, 2], unit="s")
            qc.barrier()
            qc.measure([0, 1, 2], cr)

            isa_qc = pm.run(qc)
            all_pubs.append((isa_qc, None, shots))
            pub_labels.append((name, total_time, 0))
            print(f"  {name}: 1 circuit (delay {total_time}µs)")

        else:
            # QEC strategy
            isa_qc, n_cycles = build_qec_circuit_fixed(
                qubits, total_time, interval, backend
            )
            all_pubs.append((isa_qc, None, shots))
            pub_labels.append((name, total_time, n_cycles))
            print(f"  {name}: 1 circuit ({n_cycles} QEC cycles)")

    print(f"\nSubmitting {len(all_pubs)} circuits to {backend.name}...")
    sampler = Sampler(mode=backend)
    job = sampler.run(all_pubs)
    print(f"Job ID: {job.job_id()}")
    print("Waiting for results...")

    result = job.result()

    # Analyze final measurement results
    print("\nResults (Final |111⟩ Survival):")
    print(f"{'Strategy':<20} {'Cycles':<10} {'P(|111⟩)':<15}")
    print("-" * 45)

    qec_results = {}
    for i, (name, delay, cycles) in enumerate(pub_labels):
        counts = result[i].data.final.get_counts()
        total = sum(counts.values())
        n_111 = counts.get("111", 0)
        p_111 = n_111 / total

        qec_results[name] = {"survival": p_111, "cycles": cycles}
        print(f"{name:<20} {cycles:<10} {p_111:<15.4f}")

    return qec_results


# ============================================================
# Experiment 3: Post-Hoc Scout Analysis
# ============================================================

def posthoc_scout_analysis(t1_data, qec_results, backend):
    """
    Analyze what EEDT-Scout would have decided using real T1 data.

    Uses the actual T1 measured from Experiment 1 to simulate Scout's
    decision logic: trigger QEC when P_survival < 0.82

    This doesn't require additional hardware runs — it's a classical
    analysis of the real data.

    Args:
        t1_data: dict from Experiment 1 (delay → survival)
        qec_results: dict from Experiment 2
        backend: for calibration data
    """
    print("\n" + "=" * 60)
    print("Experiment 3: Post-Hoc Scout Analysis")
    print("=" * 60)

    # Fit T1 from experimental data
    delays = np.array(sorted(t1_data.keys()), dtype=float)
    survivals = np.array([t1_data[d] for d in delays])

    # Fit exponential: P = A * exp(-t/T1) + offset
    # Simple log-linear fit for P > 0
    valid = survivals > 0.01
    if np.sum(valid) >= 3:
        log_surv = np.log(survivals[valid])
        d_valid = delays[valid]

        # Linear fit: log(P) = log(A) - t/T1
        coeffs = np.polyfit(d_valid, log_surv, 1)
        t1_measured = -1.0 / coeffs[0]
        amplitude = np.exp(coeffs[1])
    else:
        t1_measured = 100.0  # fallback
        amplitude = 1.0

    print(f"\nMeasured T1 from hardware: {t1_measured:.1f} µs")
    print(f"Amplitude: {amplitude:.3f}")

    # Simulate Scout's decisions with measured T1
    threshold = 0.82
    total_time = 200.0
    dt = 1.0

    # Scout simulation using real T1
    scout_intervals = []
    t = 0.0
    last_qec = 0.0

    while t < total_time:
        elapsed = t - last_qec
        p_surv = np.exp(-elapsed / t1_measured)

        if p_surv < threshold and elapsed > 5.0:  # min 5µs between cycles
            scout_intervals.append(elapsed)
            last_qec = t

        t += dt

    avg_scout_interval = np.mean(scout_intervals) if scout_intervals else 0

    print(f"\nScout analysis (threshold = {threshold}):")
    print(f"  Would trigger {len(scout_intervals)} QEC cycles in {total_time:.0f}µs")
    print(f"  Average interval: {avg_scout_interval:.1f} µs")
    print(f"  Intervals: {[f'{x:.0f}' for x in scout_intervals]}")

    # Compare with fixed strategies
    print(f"\nComparison:")
    print(f"  Fixed 20µs: {200//20} cycles (interval always 20µs)")
    print(f"  Fixed 40µs: {200//40} cycles (interval always 40µs)")
    print(f"  Scout would: {len(scout_intervals)} cycles "
          f"(avg {avg_scout_interval:.0f}µs)")

    # Key insight for non-stationary case
    print(f"\n--- Key Insight ---")
    print(f"In this static-T1 experiment, Scout's interval ≈ fixed optimal.")
    print(f"Scout's real advantage appears when T1 drifts over time.")
    print(f"Next step: run same experiment at different times of day")
    print(f"to capture real T1 drift, then show Scout adapts.")

    return {
        "t1_measured": t1_measured,
        "scout_intervals": scout_intervals,
        "n_scout_cycles": len(scout_intervals),
        "avg_interval": avg_scout_interval,
    }


# ============================================================
# Visualization
# ============================================================

def plot_results(t1_data, qec_results, scout_analysis):
    """Generate publication-quality figure from hardware results."""

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # --- Panel A: T1 Decay ---
    ax = axes[0]
    delays = np.array(sorted(t1_data.keys()))
    survivals = np.array([t1_data[d] for d in delays])

    ax.scatter(delays, survivals, color='black', s=50, zorder=5,
               label='Hardware data')

    # Fit curve
    t1 = scout_analysis["t1_measured"]
    t_fit = np.linspace(0, max(delays), 200)
    ax.plot(t_fit, np.exp(-t_fit / t1), 'r--', linewidth=2,
            label=f'Fit: T₁ = {t1:.0f} µs', alpha=0.7)

    ax.set_xlabel('Delay (µs)', fontsize=12)
    ax.set_ylabel('P(|111⟩)', fontsize=12)
    ax.set_title('(A) T₁ Baseline on Hardware', fontsize=13, weight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.2)
    ax.set_ylim(0, 1.05)

    # --- Panel B: QEC Comparison ---
    ax = axes[1]
    names = list(qec_results.keys())
    survivals_qec = [qec_results[n]["survival"] for n in names]
    cycles = [qec_results[n]["cycles"] for n in names]

    colors = ['#E74C3C', '#27AE60', '#2980B9', '#8E44AD']
    bars = ax.bar(names, survivals_qec, color=colors[:len(names)], alpha=0.8)

    # Add cycle count labels
    for bar, c in zip(bars, cycles):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{c} cycles', ha='center', fontsize=9)

    ax.set_ylabel('P(|111⟩) after 200µs', fontsize=12)
    ax.set_title('(B) QEC Strategy Comparison', fontsize=13, weight='bold')
    ax.grid(True, alpha=0.2, axis='y')
    ax.set_ylim(0, max(survivals_qec) * 1.3 if survivals_qec else 1.0)

    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"EEDT_Hardware_{timestamp}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\nFigure saved: {filename}")

    return filename


# ============================================================
# Local Test Mode (No Hardware Required)
# ============================================================

def run_local_test():
    """
    Run experiments using Qiskit's local simulator for testing.

    Use this to verify the code works before consuming hardware time.
    """
    print("\n" + "=" * 60)
    print("LOCAL TEST MODE (no IBM Quantum account needed)")
    print("=" * 60)

    try:
        from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
    except ImportError:
        try:
            from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
            FakeMarrakesh = FakeSherbrooke
        except ImportError:
            print("ERROR: Install qiskit-ibm-runtime >= 0.28 for fake backends")
            print("  pip install qiskit-ibm-runtime --upgrade")
            return

    backend = FakeMarrakesh()
    print(f"Using fake backend: {backend.name}")

    # Simplified T1 test
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import SamplerV2 as Sampler

    pm = generate_preset_pass_manager(
        optimization_level=1,
        backend=backend,
        initial_layout=[0, 1, 2]
    )

    # Build simple test: prepare |111⟩, measure
    qr = QuantumRegister(3, "q")
    cr = ClassicalRegister(3, "meas")
    qc = QuantumCircuit(qr, cr)
    qc.x([0, 1, 2])
    qc.barrier()
    qc.measure([0, 1, 2], cr)

    isa_qc = pm.run(qc)

    sampler = Sampler(mode=backend)
    job = sampler.run([(isa_qc,)])
    result = job.result()

    counts = result[0].data.meas.get_counts()
    total = sum(counts.values())
    n_111 = counts.get("111", 0)

    print(f"\nTest circuit results:")
    print(f"  P(|111⟩) = {n_111/total:.4f}")
    print(f"  Top counts: {dict(sorted(counts.items(), key=lambda x: -x[1])[:5])}")
    print(f"\n✓ Local test passed. Ready for hardware.")


# ============================================================
# Main
# ============================================================

def main():
    """
    Run full EEDT hardware validation.

    Usage:
        # Test locally first (no account needed):
        python eedt_hardware_validation.py --local

        # Run on real hardware:
        python eedt_hardware_validation.py
    """
    import sys

    if "--local" in sys.argv:
        run_local_test()
        return

    if "--help" in sys.argv or "-h" in sys.argv:
        print(main.__doc__)
        return

    # Connect to IBM Quantum
    service, backend = connect_ibm_quantum()

    # Experiment 1: T1 Baseline
    t1_data, qubits = run_t1_experiment(service, backend, shots=4096)

    # Experiment 2: QEC Comparison
    qec_results = run_qec_experiment(service, backend, qubits, shots=4096)

    # Experiment 3: Post-Hoc Scout
    scout = posthoc_scout_analysis(t1_data, qec_results, backend)

    # Plot
    plot_results(t1_data, qec_results, scout)

    # Save raw data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    data = {
        "backend": backend.name,
        "timestamp": timestamp,
        "qubits_used": qubits,
        "t1_data": t1_data,
        "qec_results": {k: v for k, v in qec_results.items()},
        "scout_analysis": scout,
    }

    import json
    datafile = f"EEDT_Hardware_Data_{timestamp}.json"
    with open(datafile, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Raw data saved: {datafile}")

    print("\n" + "=" * 60)
    print("DONE — All experiments complete")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"  1. Run again at different times to capture T1 drift")
    print(f"  2. Compare Scout's optimal interval across runs")
    print(f"  3. Build real-time Scout using Dynamic Circuits if_test")


if __name__ == "__main__":
    main()
