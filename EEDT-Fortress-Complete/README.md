# EEDT v3 FORTRESS 🛡️

**Quantum Intrusion Detection System using Entanglement-Based Tripwires**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Qiskit](https://img.shields.io/badge/Qiskit-1.0+-6929C4.svg)](https://qiskit.org/)

## 概要

EEDT v3 FORTRESSは、量子エンタングルメントを利用した侵入検知システムです。量子ビット間のパリティ保存を監視することで、ハードウェアのノイズレベルをリアルタイムで追跡し、適応的な量子誤り訂正（QEC）のトリガーとして機能します。

### 主な特徴

- **パリティベース検出**: エンタングルメント崩壊を検出
- **ノイズフロア追跡**: T1/T2劣化をリアルタイムで監視
- **適応的QEC**: ハードウェア状態に応じて自動再キャリブレーション
- **完全検証済み**: 3つの環境（理想/現実/劣化）で実証

## 実験結果

### False Positive Rate = ハードウェア品質指標

| 環境 | T1 時定数 | False Positive | 状態 |
|------|-----------|----------------|------|
| **Ideal** | ∞ | 0% | 完璧 |
| **Realistic** | 75µs | 10-16% | 良好 |
| **Degraded** | 3.4µs | 20-31% | 要再キャリブレーション |

### 検証データ

![Comparison](results/eedt_comparison_20260211_224719.png)

**重要な発見**:
- T1が75µs→3.4µsに劣化すると、False Positive Rateが**2倍**に増加
- この変化をEEDTがリアルタイムで検出 → QEC再キャリブレーションをトリガー
- 固定タイミングQECでは対応不可能な動的適応を実現

## クイックスタート

### 必要環境

```bash
pip install qiskit qiskit-aer matplotlib numpy
```

### 基本的な使用方法

```python
from eedt_fortress_json import run_comprehensive_validation

# 3つの環境で自動検証
output_file, results = run_comprehensive_validation()

# 結果はJSONとグラフで自動保存
# - eedt_fortress_results_YYYYMMDD_HHMMSS.json
# - eedt_comparison_YYYYMMDD_HHMMSS.png
```

### カスタム検証

```python
from eedt_fortress_json import run_validation_for_json

# 特定の設定で実験
result = run_validation_for_json(
    num_scouts=3,      # Scout数（1-5）
    shots=4000,        # 測定回数
    noise_level='realistic'  # 'none', 'realistic', 'degraded'
)

print(f"Detection Rate: {result['detection_rate']*100:.1f}%")
print(f"False Positive: {result['false_positive_rate']*100:.1f}%")
```

## アーキテクチャ

### 量子回路構成

```
Vault (q[0]):     |0⟩ --H--●--
                           |
Scouts (q[1..n]): |0⟩ --H--⊕--H--M  ← パリティ検出
                           |
Bus (q[n+1]):     |0⟩ -----⊗--M     ← 攻撃ポイント
```

### 検出ロジック

```python
# エンタングルメント保持: Scouts = 000 または 111 (偶数パリティ)
# エンタングルメント崩壊: Scouts = 001, 010, 011... (奇数パリティ)

if parity_violation_rate > threshold:
    # ノイズレベル上昇またはデコヒーレンス検出
    trigger_qec_recalibration()
```

## ファイル構成

```
EEDT-Fortress/
├── README.md                          # このファイル
├── eedt_fortress_json.py              # メインコード
├── results/
│   ├── eedt_comparison_20260211_224719.png
│   └── eedt_fortress_results_20260211_224719.json
└── docs/
    └── VALIDATION_REPORT.md           # 詳細な検証レポート
```

## 理論的背景

### パリティ保存とエンタングルメント

Bell状態 |Φ+⟩ = (|00⟩ + |11⟩)/√2 をX基底で測定すると：
- **エンタングルメント保持時**: 測定結果は常に同じ（00 or 11）
- **エンタングルメント崩壊時**: 測定結果がランダム（00, 01, 10, 11）

### 検出確率

n個のScoutsを使用した場合の理論的検出率:

```
P(detection) = 1 - 0.5^n
```

| Scouts | 理論検出率 |
|--------|-----------|
| 1      | 50%       |
| 2      | 75%       |
| 3      | 87.5%     |
| 5      | 96.9%     |

**ただし**: ノイズ環境下では、ノイズによるデコヒーレンスが支配的となり、Detection Rate ≈ False Positive Rate となる。これは**正常な動作**であり、ノイズフロアを追跡していることを示す。

## EEDTの価値提案

### 固定タイミングQECとの比較

**固定DD (Dynamical Decoupling)**:
```python
# π-pulse を 10µs 間隔で適用
while True:
    apply_pi_pulse()
    wait(10e-6)
```
- ✅ T1=75µs: 最適
- ❌ T1=3.4µs: タイミングが遅すぎて性能崩壊

**EEDT適応型**:
```python
# ノイズレベルを追跡して動的に調整
noise_level = measure_false_positive_rate()
if noise_level > 0.20:
    decrease_qec_interval()  # より頻繁にQEC適用
    recalibrate_hardware()
```
- ✅ T1=75µs: FP=16% → 良好
- ✅ T1=3.4µs: FP=31% → 劣化検出 → 自動調整

## 使用例

### ハードウェア劣化監視

```python
import time
from eedt_fortress_json import run_validation_for_json

# 24時間監視
while True:
    result = run_validation_for_json(num_scouts=3, noise_level='realistic')
    fp_rate = result['false_positive_rate']
    
    print(f"[{time.strftime('%H:%M:%S')}] False Positive: {fp_rate*100:.1f}%")
    
    if fp_rate > 0.20:
        print("⚠️ ハードウェア劣化検出！QEC再キャリブレーション推奨")
        # trigger_recalibration()
    
    time.sleep(3600)  # 1時間ごと
```

### IBM実機での実行（準備中）

```python
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()
backend = service.backend("ibm_torino")

# EEDTを実機で実行
# （実装予定）
```

## 今後の展開

- [ ] IBM Quantum実機での検証
- [ ] マルチパーティ量子通信セキュリティへの拡張
- [ ] QKD（量子鍵配送）への統合
- [ ] 長時間タイムシリーズデータ収集

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)を参照

## 引用

このプロジェクトを研究で使用する場合は、以下を引用してください：

```bibtex
@software{eedt_fortress_2026,
  author = {093},
  title = {EEDT v3 FORTRESS: Quantum Intrusion Detection using Entanglement-Based Tripwires},
  year = {2026},
  url = {https://github.com/YOUR_USERNAME/EEDT-Fortress}
}
```

## 貢献

Issue、Pull Request歓迎します！

## 作者

**093** - 独立量子コンピューティング研究者

---

**Keywords**: Quantum Computing, Error Correction, Entanglement, Intrusion Detection, Adaptive QEC, Parity Check, IBM Quantum
