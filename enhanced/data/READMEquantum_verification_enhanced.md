# 🛡️ Enhanced Verification Suite (拡張検証スイート)

This folder contains rigorous statistical verification of the EEDT protocol, moving beyond simple proof-of-concept to comprehensive stress testing against various noise models.

このフォルダには、EEDTプロトコルの統計的検証と、多様なノイズモデルに対するストレステストの結果が格納されています。単なる概念実証にとどまらず、物理的なロバスト性を証明するためのデータセットです。

## 🧪 Experiments Overview (実験概要)

We conducted two major experiments using `qiskit-aer` with custom noise models.
`qiskit-aer` を使用し、カスタムノイズモデルを用いた2つの主要な実験を行いました。

### 1. Project Rumor: Entanglement Swapping (エンタングルメント・スワッピング)
* **Goal**: Create a high-fidelity entanglement link between non-physically connected qubits ($Q_0 \leftrightarrow Q_3$) using intermediate measurement and feedforward.
* **目的**: 物理的に接続されていない量子ビット間（$Q_0 \leftrightarrow Q_3$）に、中間測定とフィードフォワード制御を用いて高忠実度のエンタングルメントリンクを生成する。
* **Result**: 
    * Correlation (00/11): **100%**
    * Error (01/10): **0%**
    * Fidelity: **1.0**

### 2. Parameter Sweep Stress Test (パラメータスイープ・ストレステスト)
* **Goal**: Compare **Standard SWAP** vs **EEDT Protocol** across a wide range of noise intensities ($\gamma = 0.1 \to 0.9$).
* **目的**: 広範なノイズ強度（$\gamma = 0.1 \to 0.9$）において、標準的なSWAP転送とEEDTプロトコルの性能を比較する。
* **Noise Models**:
    * `Amplitude Damping` (エネルギー緩和 / $T_1$)
    * `Phase Damping` (位相緩和 / $T_2$)
    * `Depolarizing` (脱分極 / 一般的なゲートエラー)

---

## 📊 Graph Interpretation (グラフの解説)

The generated graph (`quantum_verification_enhanced.png`) visualizes the superiority of EEDT.
生成されたグラフは、EEDTの優位性を視覚化しています。

### 🟢 Top Left: Project Rumor Correlation
* Shows the measurement counts for the Bell states.
* **Meaning**: The exclusive presence of `00` and `11` states proves that perfect entanglement was generated without a direct physical wire.
* **意味**: `00` と `11` のみが観測されていることは、物理配線なしで完璧なエンタングルメントが生成されたことを証明しています。

### 📈 Line Charts: Noise Resilience (Amplitude / Phase / Depolarizing)
* **Red Line (SWAP)**: Represents the survival rate of data using standard transfer. It drops linearly as noise increases.
    * **赤線 (SWAP)**: 標準的な転送でのデータ生存率。ノイズが増えるにつれて直線的に低下します。
* **Green Line (EEDT Success)**: The rate of successful transfer *when the channel is clean*.
    * **緑線 (EEDT成功)**: 回線がクリーンな場合に転送に成功した割合。
* **Blue Area (EEDT Safe Abort)**: The crucial advantage. When EEDT detects high noise, it **aborts** the transfer to save the data in memory.
    * **青色領域 (EEDT Safe Abort)**: EEDTの決定的な利点。ノイズが高いと判断した場合、転送を**中止（Abort）**し、データをメモリ内に保護します。

> **Key Takeaway**: While SWAP lets data die (Fatal Loss), EEDT converts "Failure" into "Safe Waiting".
> **結論**: SWAPはデータを死なせますが（Fatal Loss）、EEDTは「失敗」を「安全な待機」に変換します。

### 📊 Bottom Right: Advantage Margin
* Shows the net benefit of using EEDT over SWAP.
* **Y-axis > 0**: EEDT is outperforming SWAP.
* **Meaning**: In high-noise environments ($\gamma > 0.5$), EEDT provides massive reliability gains (up to +80%) by preventing data loss.
* **意味**: 高ノイズ環境（$\gamma > 0.5$）において、EEDTはデータ損失を防ぐことで、信頼性を劇的（最大+80%）に向上させます。

---

## 🛠️ Usage

```bash
# Run the enhanced verification suite
python quantum_verification_enhanced.py