# HyperFit デプロイ手順

[中文](deployment.zh.md) · [English](deployment.en.md) · [日本語](deployment.ja.md)

## コードの取得

Python API と三言語の Web 画面を起動します。Python 3.12 を推奨し、最低バージョンは 3.11 です。Git と Python を用意してください。Node/npm のビルド、GPU、Abaqus は不要です。

```text
git clone https://github.com/ywytrew/hyperfit.git
cd hyperfit
```

## Windows

リポジトリのルートで実行します。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

http://127.0.0.1:8765 を開きます。初期言語は中国語です。画面で日本語を選ぶか ?lang=ja を付けてください。英語は ?lang=en です。次回からは start.cmd をダブルクリックできます。Ctrl+C で停止します。PowerShell が起動スクリプトを制限する場合は上記の Python コマンドを直接実行し、システムの実行ポリシーを変更する必要はありません。ポートが使用中なら 8765 を 8766 に変更するか、./start.ps1 -Port 8766 を使用します。

## Linux / macOS

venv を利用できる Python 3.12 を用意し、リポジトリのルートで実行します。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

同じローカルアドレスを開き、Ctrl+C で終了します。worker は 1 のままにしてください。ジョブ状態とキャンセルは単一プロセスで管理しており、Uvicorn の worker を増やす構成には対応していません。

## Docker Compose

Docker Engine 28 以降、または対応する Docker Desktop の Linux コンテナ環境と Compose プラグインを起動してください。開発 PC では Docker daemon が動作していなかったため、コンテナをローカルで実行検証していません。リポジトリの CI にはビルドと HTTP の動作確認を含めています。

```sh
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 hyperfit
# Stop without removing saved runs:
docker compose down
```

コンテナ内では 0.0.0.0:8765 を使用し、ホストには 127.0.0.1:8765 のみ公開します。非 root ユーザー、単一 worker で動作し、hyperfit-runs 名前付きボリュームの /data に記録を保存します。イメージにはアプリと固定依存関係だけを含め、ローカルの実験や実行記録はコピーしません。ヘルスチェックは /api/models にアクセスします。実行ボリュームを削除する意図がない限り down -v は使用しないでください。

8765 が使用中なら compose.yaml のポート対応を 127.0.0.1:8766:8765 に変更し、8766 を開きます。ブラウザーのアドレスだけを変えても接続できません。

## SSH 経由でリモートサーバーを利用

自分のサーバーでリポジトリを取得し、上記のネイティブ版または Docker 版を起動します。待受けをループバックに限定し、ファイアウォールの 8765 番は開放しません。利用者の PC で SSH アカウントとホスト名を置き換えて実行します。

```sh
ssh -N -L 8765:127.0.0.1:8765 your-user@your-server
```

SSH 接続を開いたまま、PC の http://127.0.0.1:8765 にアクセスします。ローカルで使用中ならトンネルの左側のポートを 8766 に変更します。データと記録はリモートサーバーで処理・保存されます。本アプリには認証、利用者ごとの分離、計算量制限がないため、この手順では SSH を利用します。インターネット向けの複数利用者サービスには認証、HTTPS、アクセス制御、計算キューの設計が必要で、待受けアドレスを変えるだけでは不十分です。

## フロントエンド・バックエンドと記録

既定では同じサービスが静的ファイルと /api/* を配信しますが、科学計算モジュールは画面から独立しています。別のフロントエンドでは app.js より先に window.HYPERFIT_API を指定できます。開発用 CORS は localhost:5173 と 127.0.0.1:5173 のみ許可します。管理された配置では同一オリジンのリバースプロキシを推奨します。GitHub Pages では Python/FEM バックエンドを実行できません。

ネイティブ版の保存先は既定で runs/ です。起動前に HYPERFIT_RUNS を書き込み可能な専用ディレクトリへ設定できます。Docker は /data の名前付きボリュームを使用します。ディレクトリやボリューム全体をバックアップし、測定データを含む JSON を適切に保管してください。中断されたジョブは自動再開しません。更新前に記録を出力・バックアップし、git rev-parse HEAD を控えます。停止後に git pull --ff-only、固定依存関係のインストールまたは Compose 再ビルドを行い、再起動します。戻す場合は別ディレクトリで以前のコミットと環境を復元し、未コミットの作業を上書きしないでください。

## 検証と保守

仮想環境の Python を使います。Windows は .venv/Scripts/python.exe、Linux/macOS は .venv/bin/python です。

```sh
python -m pytest -q
python -m hyperfit.verify --output validation-results/fem-verification.json
python tools/build_manuals.py
python tools/package_source.py
```

画面では合成サンプル読込、フィット、三言語切替、候補選択、立方体検証、JSON 出力を確認します。/docs に API の対話型仕様があります。科学的な制限は[使用マニュアル](manual.ja.md)と[検証記録](VALIDATION.md)を参照してください。Windows ネイティブ版は開発 PC で確認済みです。Linux とコンテナの確認状況は Actions の実際の結果を参照してください。macOS の実機確認は未実施です。

公式資料：[Docker port publishing](https://docs.docker.com/engine/network/port-publishing/) · [Uvicorn deployment](https://uvicorn.dev/deployment/)
