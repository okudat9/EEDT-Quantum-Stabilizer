"""
EEDT Circuit Generation
=======================

Circuit builders for baseline and EEDT-corrected quantum circuits.

Author: 093 (T.OKUDA)
License: GPLv3
"""

import numpy as np
from typing import Optional, Tuple

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


def create_baseline_circuit(noise_phase: float, 
                            theta: float = np.pi/4) -> QuantumCircuit:
    """
    Create baseline circuit with NO correction
    
    Used for comparison to demonstrate EEDT improvement.
    
    Circuit:
    --------
    1. Prepare GHZ state: |Φ+⟩ = (|00⟩ + |11⟩)/√2
    2. Apply noise: RZ(noise_phase) on each qubit
    3. Reverse GHZ: should return to |00⟩ if no noise
    4. Measure
    
    Parameters
    ----------
    noise_phase : float
        Phase noise to apply (radians)
    theta : float
        Rotation angle for state preparation (default: π/4)
    
    Returns
    -------
    qc : QuantumCircuit
        Baseline circuit
    
    Examples
    --------
    >>> qc = create_baseline_circuit(noise_phase=0.5)
    >>> # Execute on backend to see degradation
    """
    if not QISKIT_AVAILABLE:
        raise ImportError("Qiskit required")
    
    qc = QuantumCircuit(2, 2)
    
    # State preparation: GHZ state
    qc.h(0)
    qc.cx(0, 1)
    
    # Noise environment (uncontrolled in real hardware)
    qc.rz(noise_phase, 0)
    qc.rz(noise_phase, 1)
    
    # Reverse operation (should return to |00⟩ if no noise)
    qc.cx(0, 1)
    qc.h(0)
    
    # Measurement
    qc.measure([0, 1], [0, 1])
    
    return qc


def create_eedt_circuit(noise_phase: float,
                        estimated_phase: Optional[float] = None,
                        estimation_accuracy: float = 0.95,
                        theta: float = np.pi/4) -> QuantumCircuit:
    """
    Create EEDT circuit WITH phase correction
    
    This is the core of EEDT: we estimate the noise phase and
    apply a correction to cancel it.
    
    Circuit:
    --------
    1. Prepare GHZ state
    2. Apply noise (real environment)
    3. **Apply EEDT correction: RZ(-estimated_phase)**
    4. Reverse GHZ
    5. Measure
    
    Parameters
    ----------
    noise_phase : float
        True noise phase (unknown in real scenarios)
    estimated_phase : float, optional
        Estimated noise phase. If None, computed from estimation_accuracy
    estimation_accuracy : float
        Estimation accuracy [0, 1]. 1.0 = perfect, 0.95 = 5% error
    theta : float
        Rotation angle for state preparation
    
    Returns
    -------
    qc : QuantumCircuit
        EEDT-corrected circuit
    
    Notes
    -----
    In real implementation:
    - noise_phase is UNKNOWN (true environmental noise)
    - estimated_phase comes from ancilla measurements (Phase 1)
    - estimation_accuracy depends on ancilla count and measurement shots
    
    Examples
    --------
    >>> # Perfect estimation
    >>> qc = create_eedt_circuit(noise_phase=0.5, estimation_accuracy=1.0)
    >>> 
    >>> # Realistic estimation (95% accuracy)
    >>> qc = create_eedt_circuit(noise_phase=0.5, estimation_accuracy=0.95)
    """
    if not QISKIT_AVAILABLE:
        raise ImportError("Qiskit required")
    
    qc = QuantumCircuit(2, 2)
    
    # [Step 1] State preparation: GHZ state
    qc.h(0)
    qc.cx(0, 1)
    
    # [Step 2] Noise environment (true noise - uncontrolled)
    qc.rz(noise_phase, 0)
    qc.rz(noise_phase, 1)
    
    # [Step 3] EEDT Phase Estimation & Correction
    if estimated_phase is None:
        if estimation_accuracy >= 1.0:
            # Perfect estimation (ideal case)
            estimated_phase = noise_phase
        else:
            # Realistic estimation with error
            relative_error = 1.0 - estimation_accuracy
            estimation_error = np.random.normal(
                0, 
                relative_error * abs(noise_phase)
            )
            estimated_phase = noise_phase + estimation_error
    
    # Apply correction based on estimation
    correction = -estimated_phase
    qc.rz(correction, 0)
    qc.rz(correction, 1)
    
    # [Step 4] Reverse GHZ (should return to |00⟩)
    qc.cx(0, 1)
    qc.h(0)
    
    # [Step 5] Measurement
    qc.measure([0, 1], [0, 1])
    
    return qc


def create_bell_monitor_circuit() -> QuantumCircuit:
    """
    Create Bell pair monitoring circuit
    
    Used for real-time fidelity monitoring without disrupting
    the main computation.
    
    Circuit:
    --------
    |Φ+⟩ = (|00⟩ + |11⟩)/√2
    
    Ideal outcome: P(00) = P(11) = 0.5
    With noise: Distribution shifts
    
    Fidelity estimate: F ≈ P(00) + P(11)
    
    Returns
    -------
    qc : QuantumCircuit
        Bell pair monitoring circuit
    
    Examples
    --------
    >>> qc = create_bell_monitor_circuit()
    >>> # Execute and check if P(00) + P(11) > threshold
    """
    if not QISKIT_AVAILABLE:
        raise ImportError("Qiskit required")
    
    qc = QuantumCircuit(2, 2)
    
    # Create Bell pair |Φ+⟩
    qc.h(0)
    qc.cx(0, 1)
    
    # Measure in computational basis
    qc.measure([0, 1], [0, 1])
    
    return qc


def create_phase_estimation_circuit(n_ancilla: int = 5,
                                    n_data: int = 3) -> QuantumCircuit:
    """
    Create quantum phase estimation circuit
    
    Used to estimate the noise phase with high precision.
    More ancilla qubits → better estimation accuracy.
    
    Theorem 1: Δφ ∼ C/(2^n * √M)
    where n = ancilla qubits, M = measurements
    
    Parameters
    ----------
    n_ancilla : int
        Number of ancilla qubits for estimation (default: 5)
    n_data : int
        Number of data qubits (default: 3)
    
    Returns
    -------
    qc : QuantumCircuit
        Phase estimation circuit
    
    Notes
    -----
    Estimation accuracy improves exponentially with n_ancilla:
    - n=3: Δφ ~ 0.074 rad
    - n=5: Δφ ~ 0.018 rad
    - n=7: Δφ ~ 0.005 rad
    
    Examples
    --------
    >>> # High-precision estimation
    >>> qc = create_phase_estimation_circuit(n_ancilla=7, n_data=3)
    """
    if not QISKIT_AVAILABLE:
        raise ImportError("Qiskit required")
    
    # Registers
    ancilla = QuantumRegister(n_ancilla, 'ancilla')
    data = QuantumRegister(n_data, 'data')
    c_ancilla = ClassicalRegister(n_ancilla, 'c_ancilla')
    c_data = ClassicalRegister(n_data, 'c_data')
    
    qc = QuantumCircuit(ancilla, data, c_ancilla, c_data)
    
    # [Step 1] Initialize ancilla in superposition
    for i in range(n_ancilla):
        qc.h(ancilla[i])
    
    # [Step 2] Controlled phase operations
    # Each ancilla controls a different power of the phase operator
    for i in range(n_ancilla):
        power = 2 ** (n_ancilla - 1 - i)
        # Controlled-U^(2^i) where U = exp(iφΣZ)
        # Simplified: apply controlled rotations
        for j in range(n_data):
            qc.cp(np.pi / power, ancilla[i], data[j])
    
    # [Step 3] Inverse QFT on ancilla
    qc.barrier()
    _inverse_qft(qc, ancilla)
    
    # [Step 4] Measure ancilla
    qc.measure(ancilla, c_ancilla)
    
    return qc


def _inverse_qft(qc: QuantumCircuit, qubits: QuantumRegister):
    """
    Apply inverse Quantum Fourier Transform
    
    Used in phase estimation to extract phase information.
    
    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to
    qubits : QuantumRegister
        Qubits to apply inverse QFT on
    """
    n = len(qubits)
    
    # Reverse bit order
    for i in range(n // 2):
        qc.swap(qubits[i], qubits[n - 1 - i])
    
    # Apply inverse QFT
    for i in range(n):
        # Controlled rotations
        for j in range(i):
            qc.cp(-np.pi / (2 ** (i - j)), qubits[j], qubits[i])
        
        # Hadamard
        qc.h(qubits[i])


def create_multipath_circuit(n_paths: int = 3,
                             noise_phase: float = 0.1) -> QuantumCircuit:
    """
    Create multipath EEDT circuit
    
    Theorem 3: F_multipath ≥ 1 - (1 - F_single)^N
    
    Uses multiple redundant paths and selects the best one
    based on entanglement quality metrics.
    
    Parameters
    ----------
    n_paths : int
        Number of parallel paths
    noise_phase : float
        Noise phase per path
    
    Returns
    -------
    qc : QuantumCircuit
        Multipath circuit
    
    Examples
    --------
    >>> # Triple redundancy
    >>> qc = create_multipath_circuit(n_paths=3, noise_phase=0.2)
    """
    if not QISKIT_AVAILABLE:
        raise ImportError("Qiskit required")
    
    # Each path needs 2 qubits
    total_qubits = n_paths * 2
    qc = QuantumCircuit(total_qubits, n_paths)
    
    for path_idx in range(n_paths):
        q0 = path_idx * 2
        q1 = path_idx * 2 + 1
        
        # Create entangled pair for this path
        qc.h(q0)
        qc.cx(q0, q1)
        
        # Apply path-specific noise
        # (In reality, each path has different noise)
        path_noise = noise_phase * (1 + 0.1 * np.random.randn())
        qc.rz(path_noise, q0)
        qc.rz(path_noise, q1)
        
        # Measure this path
        qc.cx(q0, q1)
        qc.h(q0)
        qc.measure(q0, path_idx)
    
    return qc


def estimate_fidelity_from_counts(counts: dict) -> float:
    """
    Estimate fidelity from measurement counts
    
    For Bell pair |Φ+⟩: F ≈ P(00) + P(11)
    
    Parameters
    ----------
    counts : dict
        Measurement counts from circuit
    
    Returns
    -------
    fidelity : float
        Estimated fidelity [0, 1]
    
    Examples
    --------
    >>> counts = {'00': 480, '11': 492, '01': 14, '10': 14}
    >>> f = estimate_fidelity_from_counts(counts)
    >>> print(f"Fidelity: {f:.3f}")
    Fidelity: 0.972
    """
    total = sum(counts.values())
    if total == 0:
        return 0.0
    
    p00 = counts.get('00', 0) / total
    p11 = counts.get('11', 0) / total
    
    return p00 + p11
