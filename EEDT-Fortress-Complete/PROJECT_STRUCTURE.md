# EEDT-Fortress Project Structure

```
EEDT-Fortress/
│
├── README.md                          # プロジェクト概要・使い方
├── QUICKSTART.md                      # クイックスタートガイド
├── LICENSE                            # MIT License
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
│
├── eedt_fortress_json.py             # メイン実験コード
│
├── docs/
│   └── VALIDATION_REPORT.md          # 詳細な検証レポート
│
└── results/
    ├── eedt_comparison_20260211_224719.png       # 3環境比較グラフ
    └── eedt_fortress_results_20260211_224719.json # 実験データ (JSON)
```

## ファイル説明

### ルートディレクトリ

| ファイル | 説明 |
|---------|------|
| `README.md` | プロジェクト全体の説明、理論、使用例 |
| `QUICKSTART.md` | すぐに始めるためのガイド |
| `LICENSE` | MIT License |
| `requirements.txt` | 必要なPythonパッケージ |
| `.gitignore` | Git管理から除外するファイル |

### コード

| ファイル | 説明 |
|---------|------|
| `eedt_fortress_json.py` | EEDT v3 FORTRESS実装（362行） |

主な関数:
- `QuantumFortress`: 量子回路クラス
- `create_noise_model()`: IBM実機ノイズモデル
- `run_validation_for_json()`: 単一実験
- `run_comprehensive_validation()`: 包括的検証（3環境×5 Scouts）
- `create_comparison_plot()`: 比較グラフ生成

### ドキュメント

| ファイル | 説明 |
|---------|------|
| `docs/VALIDATION_REPORT.md` | 実験方法、結果、分析の詳細レポート |

内容:
- 実験セットアップ
- 3環境での結果（理想/現実/劣化）
- 理論的検証
- 実用的な応用例

### 結果データ

| ファイル | サイズ | 説明 |
|---------|--------|------|
| `results/eedt_fortress_results_20260211_224719.json` | ~15KB | 15実験の完全データ |
| `results/eedt_comparison_20260211_224719.png` | ~80KB | 3環境比較グラフ |

JSON構造:
```json
{
  "metadata": {...},
  "experiments": {
    "none": [...],      // 5実験
    "realistic": [...], // 5実験
    "degraded": [...]   // 5実験
  }
}
```

## Git使い方

### 初回セットアップ

```bash
cd EEDT-Fortress
git init
git add .
git commit -m "Initial commit: EEDT v3 FORTRESS"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/EEDT-Fortress.git
git push -u origin main
```

### 更新

```bash
git add .
git commit -m "Update: add new experiments"
git push
```

## 拡張方法

### 新しい実験を追加

1. `eedt_fortress_json.py` をコピー
2. `run_validation_for_json()` を修正
3. 新しい結果を `results/` に保存
4. `VALIDATION_REPORT.md` を更新

### IBM実機統合

```python
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()
backend = service.backend("ibm_torino")

# fortress.build_circuit() の出力を実機で実行
```

## データサイズ

```
Total: ~100KB

eedt_fortress_json.py:              15KB
eedt_fortress_results_*.json:       15KB
eedt_comparison_*.png:              80KB
Documentation:                      50KB
```

## バージョン履歴

- **v1.0** (2026-02-11): 初回リリース
  - パリティベース検出実装
  - 3環境（理想/現実/劣化）検証完了
  - JSON出力機能
  - 包括的ドキュメント

## 次のバージョン計画

- v1.1: IBM実機統合
- v1.2: タイムシリーズ分析
- v2.0: マルチパーティ拡張
