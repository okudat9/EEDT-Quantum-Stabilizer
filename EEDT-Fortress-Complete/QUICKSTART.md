# Quick Start Guide

## インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/YOUR_USERNAME/EEDT-Fortress.git
cd EEDT-Fortress
```

### 2. 依存関係をインストール

```bash
pip install -r requirements.txt
```

または個別に:

```bash
pip install qiskit qiskit-aer numpy matplotlib
```

## 基本的な使い方

### すぐに実行

```bash
python eedt_fortress_json.py
```

これで以下が自動生成されます:
- `eedt_fortress_results_YYYYMMDD_HHMMSS.json` - 実験データ
- `eedt_comparison_YYYYMMDD_HHMMSS.png` - 比較グラフ

### カスタム実験

```python
from eedt_fortress_json import run_validation_for_json

# 単一実験
result = run_validation_for_json(
    num_scouts=3,           # Scout数: 1-5
    shots=4000,             # 測定回数
    noise_level='realistic' # 'none', 'realistic', 'degraded'
)

# 結果を表示
print(f"Detection Rate: {result['detection_rate']*100:.1f}%")
print(f"False Positive: {result['false_positive_rate']*100:.1f}%")
```

### ノイズレベルの意味

| noise_level | T1 | 説明 |
|-------------|-----|------|
| `'none'` | ∞ | 理想的な量子コンピュータ |
| `'realistic'` | 75µs | IBM Quantum実機相当 |
| `'degraded'` | 3.4µs | 長時間稼働後の劣化状態 |

## 結果の解釈

### False Positive Rate = ハードウェア品質

```python
fp_rate = result['false_positive_rate']

if fp_rate < 0.10:
    print("✅ ハードウェア状態: 優秀")
elif fp_rate < 0.20:
    print("✅ ハードウェア状態: 良好")
else:
    print("⚠️ ハードウェア状態: 劣化 - QEC再キャリブレーション推奨")
```

### JSONデータの構造

```python
import json

# データを読み込み
with open('eedt_fortress_results_20260211_224719.json') as f:
    data = json.load(f)

# 特定の実験にアクセス
realistic_3scouts = data['experiments']['realistic'][2]  # 3 Scouts = index 2

print(f"Detection: {realistic_3scouts['detection_rate']*100:.1f}%")
print(f"False Pos: {realistic_3scouts['false_positive_rate']*100:.1f}%")
```

## よくある使い方

### 1. ハードウェア監視ループ

```python
import time
from eedt_fortress_json import run_validation_for_json

while True:
    result = run_validation_for_json(num_scouts=3, noise_level='realistic')
    fp = result['false_positive_rate']
    
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] FP Rate: {fp*100:.1f}%")
    
    if fp > 0.20:
        print("⚠️ Alert: Hardware degradation detected!")
    
    time.sleep(3600)  # 1時間ごと
```

### 2. 複数Scout数の比較

```python
from eedt_fortress_json import run_validation_for_json

for n_scouts in [2, 3, 4, 5]:
    result = run_validation_for_json(
        num_scouts=n_scouts,
        shots=4000,
        noise_level='realistic'
    )
    print(f"Scouts={n_scouts}: FP={result['false_positive_rate']*100:.1f}%")
```

### 3. ノイズレベル感度テスト

```python
from eedt_fortress_json import run_validation_for_json

for noise in ['none', 'realistic', 'degraded']:
    result = run_validation_for_json(
        num_scouts=3,
        shots=4000,
        noise_level=noise
    )
    print(f"{noise:10s}: FP={result['false_positive_rate']*100:.1f}%")
```

出力例:
```
none      : FP=0.0%
realistic : FP=9.5%
degraded  : FP=20.2%
```

## トラブルシューティング

### Qiskitのインストールエラー

```bash
# 最新版を指定
pip install qiskit==1.0.0 qiskit-aer==0.13.0
```

### メモリエラー

shots数を減らす:

```python
result = run_validation_for_json(num_scouts=3, shots=2000)  # デフォルトは4000
```

### グラフが表示されない

バックエンドを指定:

```python
import matplotlib
matplotlib.use('Agg')  # ファイル保存のみ
```

## 次のステップ

1. [VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md) - 詳細な検証結果
2. [README.md](README.md) - プロジェクト全体の概要
3. IBM Quantum実機での実行（準備中）

## サポート

Issues: https://github.com/YOUR_USERNAME/EEDT-Fortress/issues
