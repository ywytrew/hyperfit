# HyperFit

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

等方性超弾性材料の応力と体積を連成して同定する研究用プレビュー 0.1.0 です。ライセンスは GPL-3.0-or-later です。

- [使用マニュアル](docs/manual.ja.md)：データ定義、モデル、seed 付き初期化、誤差基準、候補選択、検証。
- [デプロイ手順](docs/deployment.ja.md)：Windows、Linux/macOS、Docker Compose、SSH 経由のリモート利用。
- [数式の規約](docs/methods.md)、[検証記録](docs/VALIDATION.md)、[貢献ガイド](docs/CONTRIBUTING.md)。

## 起動

Python 3.12 を推奨します。リポジトリを取得し、仮想環境を作成して requirements-lock.txt をインストールした後、ルートから実行します。

```sh
python -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

仮想環境の Python を使い、http://127.0.0.1:8765/?lang=ja を開きます。フロントエンドのビルドは不要です。ヘッダーで中文・English・日本語を切り替えても入力と結果は保持されます。OS 別のコマンドはデプロイ手順に記載しています。

## 機能と適用範囲

Neo-Hookean、Mooney–Rivlin、多項式、Yeoh、Ogden の偏差エネルギーと、K0/(2β)[exp(β(ln J)²)−1] を含む四つの体積エネルギーを組み合わせます。横方向応力ゼロの条件から横収縮と体積を求めるため、応力と体積は連成しています。seed 付き Latin hypercube 初期化では連成応答を確認してから複数の開始点を選択します。手動初期値も使用できます。

絶対＋相対許容差、ロバスト損失、ひずみ区間の重みにより誤差の選好を明示します。既知の標準偏差やピーク NRMSE も選択できます。三つの重みで局所探索した候補の非劣解を表示しますが、大域的パレートフロントは保証しません。残差、境界到達、収束、感度も確認できます。

独立した材料点計算を FElupe の u/p/J 混合要素で検証します。音響テンソルのサンプリングは安定性のスクリーニングであり、大域的な証明ではありません。画面は均一単軸データをフィットし、元試験片形状の逆解析は行いません。非均一な体積場の精度には追加検証が必要です。Abaqus 実行検証や UHYPER/UMAT 出力はありません。

公開対象は再実装したコード、文書、テスト、合成例です。失われたコードの復元や元実験の再現ではなく、原実験データと論文 PDF は含めていません。サーバーは複数利用者認証を備えていないローカル研究ツールです。リモート利用にはデプロイ手順の SSH 構成を使ってください。

## 開発

```sh
python -m pytest -q
python -m hyperfit.verify --output validation-results/fem-verification.json
python tools/build_manuals.py
python tools/package_source.py
```

API 仕様は /docs です。科学計算モジュールは HTTP から独立し、画面は /api/* の JSON を使用します。翻訳は hyperfit/frontend/locales/ に保存し、三言語のキーと置換変数を一致させます。ブラウザー用文書は docs/manual.*.md と docs/deployment.*.md から生成します。

[LICENSE](LICENSE) と[第三者ライセンス](THIRD_PARTY_NOTICES.md)を参照してください。
