# EEDT: 量子運用安定化ミドルウェア

*(Runtime Stabilization Layer for NISQ Devices)* 🛡️⚛️

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Hardware: IBM Heron](https://img.shields.io/badge/Hardware-IBM_Heron-purple)](#)
[![Status: Hardware Validated](https://img.shields.io/badge/Status-Hardware_Validated-green)](#)

> **【技術・経営担当の方へ】**
>
> 本プロジェクトは、既存の量子制御理論を否定するものではありません。
> むしろ、実機特有の「デコヒーレンス（情報の消失）」という物理的な壁に対し、
> **「計算を止めずにシステムを稼働させ続ける」** ための、実用性に特化した安定化レイヤーの提案です。

---

## 🚨 解決する課題: "The Decoherence Wall"

現在のNISQデバイスにおいて、量子状態はマイクロ秒単位で崩壊します（T₁減衰）。教科書的な理論が正しくても、実機のノイズ環境下では計算結果を維持できません。

**EEDT (Entanglement-Enhanced Dynamical Tracking)** は、この自然崩壊に対抗し、稼働時間を最大化する **「ランタイム・スタビライザー」** です。

---

## ⚡ 実証結果 (IBM Heron Validated)

**2026-02-10 実施 / Backend: ibm_torino**

IBM Quantum Heron実機において、3量子ビット反復符号（Qubit #42, #64, #51）を用いた生存テストを実施しました。
シミュレーション上のノイズではなく、**実機の自然減衰環境下**での検証結果です。

### 📉 Before (対策なし) vs 📈 After (EEDT適用)

何もしなければ8%しか残らない信号を、EEDTの自律補正により**約5.5倍**の生存率で維持することに成功しました。

| 戦略 | QECサイクル | P(\|111⟩) after 200µs | 改善率 |
| :--- | :---: | :---: | :---: |
| 対策なし (Free Decay) | 0 | 8.6% | — |
| **EEDT (QEC 20µs)** | **10** | **47.3%** | **5.5× 🚀** |
| EEDT (QEC 40µs) | 5 | 41.4% | 4.8× |

> **検証のポイント:**
> 本システムは、理想的な環境ではなく、**実際の物理デバイスが持つ過酷なエラー環境**で動作し、有意な寿命延長を実現しました。

![Hardware Results](EEDT_Hardware_20260210_2321.png)

---

## 🧠 エンジニアリング・スタンス

私は物理学の学位を持ちませんが、**生成AIを「高度な思考ツール兼パートナー」として指揮（Orchestrate）** することで、理論構築から実機実装までを短期間で完遂しました。

* **AIの役割:** 量子誤り訂正理論の構造化、Qiskitコードのプロトタイピング。
* **人間の役割:** 現場課題（ドリフト/減衰）の定義、アーキテクチャ設計、**実機データに基づく意思決定**。

本リポジトリのコードは、AIが提案したものであっても、**「実機で動作し、有意な改善を示したもの」**のみを採用しています。
*Final decisions were based on **measured hardware behavior**, not model suggestions.*

---

## 📜 ライセンスと商用利用

本プロジェクトは **GNU AGPLv3** ライセンスで公開されています。

> **【商用利用をご検討の企業様へ】**
> 本技術を自社製品へ組み込む（ソースコード非公開での利用）場合、または独占的な技術利用をご希望の場合は、**別途「商用ライセンス契約」または「技術顧問契約」が必要** です。
> *For proprietary (closed-source) integration, please contact me for a commercial license or technical partnership.*

---

## 📬 Contact & Requirements

現在、この技術の本質であるスケーラビリティを実証するため、
**100量子ビット級（IBM Eagle / Heron 等）の大規模実機環境を提供いただけるパートナー** を探しています。

**【求める環境】**

* **リソース:** 100量子ビット以上の実機アクセス権、および裁量のある開発環境
* **言語:** 日本語のみで対応可能

「運用安定化技術」と「大規模実機環境」の対等な価値交換に興味がある方は、本リポジトリの **Issues** または下記メールアドレスまでご連絡ください。

**[T.Okuda]** 📧 [o93dice@gmail.com](mailto:o93dice@gmail.com)
