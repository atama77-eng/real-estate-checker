# 不動産価格チェッカー

国土交通省「不動産情報ライブラリ」API (XIT001) を利用した、中古マンション等の取引価格チェック + 簡易利回り分析アプリです。

## セットアップ

```bash
pip install -r requirements.txt
```

### APIキーの設定

1. https://www.reinfolib.mlit.go.jp/api/request/ から利用申請(無料・審査あり)
2. 発行されたキーを `.streamlit/secrets.toml` に設定

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml の REINFOLIB_API_KEY に発行されたキーを記入
```

APIキー未設定の場合は自動的にダミーデータで動作します。

## 起動

```bash
streamlit run app.py
```

## GitHubへのpush(VSCode)

VSCodeでプロジェクトフォルダを開き、ターミナル(`Ctrl + @` または `Terminal > New Terminal`)で以下を実行してください。

### 1. ローカルでgit初期化

```bash
git init
git add .
git commit -m "Initial commit: real estate price checker MVP"
```

### 2. GitHubで新規リポジトリを作成

GitHub上で空のリポジトリを作成してください(README等は追加しない)。
作成後に表示されるリポジトリURLを使います。

### 3. リモートを登録してpush

```bash
git remote add origin https://github.com/<ユーザー名>/<リポジトリ名>.git
git branch -M main
git push -u origin main
```

### 2回目以降の更新

```bash
git add .
git commit -m "変更内容を簡潔に書く"
git push
```

### 注意

- `.gitignore`で`.env`や`.streamlit/secrets.toml`を除外しているので、**APIキーが誤ってpushされる心配はありません**(念のため初回push後、GitHub上のファイル一覧に`secrets.toml`が含まれていないか確認してください)
- 初回pushでGitHub認証が求められた場合は、VSCodeの案内に従ってブラウザでログインするか、Personal Access Tokenを使ってください

## 今後の拡張候補

- XIT002 APIを使った市区町村リストの動的取得(現状はサンプルのみハードコード)
- 駅名 → 駅コード変換(現状は駅コードを直接入力する想定)
- 賃料を入力して想定利回りを計算する機能
- Supabaseでお気に入りエリア・検索履歴の保存
- 海外エリア対応(別データソースが必要)
