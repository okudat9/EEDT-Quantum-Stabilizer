"""
EEDT Test Suite
===============

Basic tests for EEDT functionality.

Run with: pytest tests/test_eedt.py
"""

import pytest
import numpy as np

try:
    from eedt import (
        AdaptiveEEDT,
        EEDTConfig,
        KalmanFilter,
        FidelityMonitor,
        create_baseline_circuit,
        create_eedt_circuit,
        create_bell_monitor_circuit,
        estimate_fidelity_from_counts
    )
    EEDT_AVAILABLE = True
except ImportError:
    EEDT_AVAILABLE = False
    pytest.skip("EEDT not installed", allow_module_level=True)


class TestKalmanFilter:
    """Test Kalman filter functionality"""
    
    def test_initialization(self):
        """Test Kalman filter initializes correctly"""
        kf = KalmanFilter(process_noise=0.01, measurement_noise=0.05)
        
        assert kf.x == 0.0
        assert kf.P == 1.0
        assert kf.Q == 0.01
        assert kf.R == 0.05
    
    def test_prediction(self):
        """Test prediction step"""
        kf = KalmanFilter()
        x_pred, P_pred = kf.predict()
        
        assert x_pred == 0.0  # Random walk
        assert P_pred > kf.P  # Uncertainty increases
    
    def test_update(self):
        """Test update with measurement"""
        kf = KalmanFilter()
        
        measurement = 0.1
        x_updated = kf.update(measurement)
        
        assert len(kf.history) == 1
        assert kf.history[0]['measurement'] == measurement
        assert abs(x_updated - measurement) < measurement  # Should move toward measurement
    
    def test_convergence(self):
        """Test filter converges to true value"""
        kf = KalmanFilter(process_noise=0.001, measurement_noise=0.01)
        
        true_phase = 0.5
        measurements = [true_phase + np.random.normal(0, 0.01) for _ in range(100)]
        
        for m in measurements:
            kf.update(m)
        
        # After 100 measurements, should be close to true value
        assert abs(kf.x - true_phase) < 0.05


class TestFidelityMonitor:
    """Test fidelity monitoring"""
    
    def test_initialization(self):
        """Test monitor initializes correctly"""
        monitor = FidelityMonitor(threshold=0.90, hysteresis=0.02)
        
        assert monitor.threshold == 0.90
        assert monitor.hysteresis == 0.02
        assert monitor.current_mode == 0
    
    def test_fidelity_measurement(self):
        """Test fidelity computation from counts"""
        monitor = FidelityMonitor()
        
        # High fidelity case
        counts_good = {'00': 480, '11': 492, '01': 14, '10': 14}
        f_good = monitor.measure_fidelity(counts_good)
        assert f_good > 0.95
        
        # Low fidelity case
        counts_bad = {'00': 250, '11': 250, '01': 250, '10': 250}
        f_bad = monitor.measure_fidelity(counts_bad)
        assert f_bad < 0.55
    
    def test_mode_switching(self):
        """Test mode 0/1 switching with hysteresis"""
        monitor = FidelityMonitor(threshold=0.90, hysteresis=0.02)
        
        # Start in mode 0
        assert monitor.current_mode == 0
        
        # Drop below threshold → switch to mode 1
        mode = monitor.check_mode_switch(0.85)
        assert mode == 1
        assert monitor.current_mode == 1
        
        # Slight recovery (within hysteresis) → stay in mode 1
        mode = monitor.check_mode_switch(0.91)
        assert mode == 1
        
        # Full recovery (above threshold + hysteresis) → back to mode 0
        mode = monitor.check_mode_switch(0.93)
        assert mode == 0


class TestCircuits:
    """Test circuit generation"""
    
    def test_baseline_circuit(self):
        """Test baseline circuit creation"""
        qc = create_baseline_circuit(noise_phase=0.1)
        
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2
        assert qc.depth() > 0
    
    def test_eedt_circuit(self):
        """Test EEDT circuit creation"""
        qc = create_eedt_circuit(noise_phase=0.1, estimation_accuracy=0.95)
        
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2
        assert qc.depth() > 0
    
    def test_eedt_perfect_correction(self):
        """Test EEDT with perfect estimation"""
        noise_phase = 0.5
        qc = create_eedt_circuit(
            noise_phase=noise_phase,
            estimation_accuracy=1.0  # Perfect
        )
        
        # Perfect correction should add correction gates
        assert qc.depth() > create_baseline_circuit(noise_phase).depth()
    
    def test_bell_monitor_circuit(self):
        """Test Bell pair monitor circuit"""
        qc = create_bell_monitor_circuit()
        
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2
        assert qc.depth() > 0


class TestUtilities:
    """Test utility functions"""
    
    def test_estimate_fidelity(self):
        """Test fidelity estimation from counts"""
        # High fidelity
        counts_high = {'00': 490, '11': 490, '01': 10, '10': 10}
        f_high = estimate_fidelity_from_counts(counts_high)
        assert 0.95 < f_high < 1.0
        
        # Low fidelity
        counts_low = {'00': 250, '11': 250, '01': 250, '10': 250}
        f_low = estimate_fidelity_from_counts(counts_low)
        assert 0.45 < f_low < 0.55
        
        # Edge case: empty counts
        counts_empty = {}
        f_empty = estimate_fidelity_from_counts(counts_empty)
        assert f_empty == 0.0


class TestEEDTConfig:
    """Test configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = EEDTConfig()
        
        assert config.fidelity_threshold == 0.90
        assert config.hysteresis == 0.02
        assert config.shots == 4096
        assert config.optimization_level == 3
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = EEDTConfig(
            fidelity_threshold=0.85,
            hysteresis=0.05,
            shots=8192
        )
        
        assert config.fidelity_threshold == 0.85
        assert config.hysteresis == 0.05
        assert config.shots == 8192


def test_package_version():
    """Test package has version"""
    import eedt
    assert hasattr(eedt, '__version__')
    assert isinstance(eedt.__version__, str)


def test_package_imports():
    """Test all main components are importable"""
    from eedt import (
        AdaptiveEEDT,
        EEDTConfig,
        KalmanFilter,
        FidelityMonitor,
        create_baseline_circuit,
        create_eedt_circuit,
        create_bell_monitor_circuit,
    )
    
    # All imports should succeed
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
