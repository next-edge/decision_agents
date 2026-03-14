# 利用ガイド

## 前提条件

| 項目 | 要件 |
| --- | --- |
| Python | 3.12 以上 |
| パッケージ管理 | [uv](https://docs.astral.sh/uv/) |
| Google Cloud | Vertex AI API が有効化されたプロジェクト |
| 認証 | `gcloud auth application-default login` 済み |

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成する。`.env.example` をコピーして、各値を設定する。

```bash
cp .env.example .env
```

`.env` の設定項目:

| 変数名 | 説明 | 例 |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud プロジェクト ID | `my-project-id` |
| `GOOGLE_CLOUD_REGION` | Google Cloud リージョン | `asia-northeast1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Vertex AI を使用するか | `true` |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI のロケーション | `us-central1` |
| `LLM_MODEL_AGENT` | エージェントが使用する LLM モデル | `gemini-2.5-flash` |
| `LLM_MODEL_TOOLS` | ツールが使用する LLM モデル | `gemini-2.5-pro` |

### 3. Google Cloud 認証

```bash
gcloud auth application-default login
```

## 実行方法

### 議論の実行

```bash
uv run python src/presentation/scripts/run.py
```

実行すると、以下の対話的なフローが開始される。

```
=== チーム選択 ===
  1. スタートアップチーム(v1) - 新規事業の構想するスタートアップチーム(v1)

チームを選択してください (1-1): 1

選択: スタートアップチーム(v1)

=== 議題入力 ===
議論してほしい議題を入力してください: ペット向けのヘルスケアサービス

議論を開始します...

[Step 1/4] ブレスト を開始...
  Round 1/2
    CEO（統合意思決定者） が発言中...
    CMO（市場・顧客視点重視） が発言中...
  Round 2/2
    CEO（統合意思決定者） が発言中...
    CMO（市場・顧客視点重視） が発言中...
  ブレスト の結論を要約中...
[Step 2/4] 売上計画検証 を開始...
  ...

議論が完了しました。レポートを出力しました: outputs/startup_team_v1_20260221_193000.md
```

### 動作確認（簡易テスト）

LLM への接続と環境変数の設定が正しいかを確認する。

```bash
uv run python src/presentation/scripts/hello_agent.py
```

### テストの実行

```bash
uv run python -m pytest src/tests/ -v
```

## チームのカスタマイズ

### 新しいチームを作成する

`configs/teams/` に新しい YAML ファイルを追加するだけで、CLI のチーム選択に自動的に表示される。

```bash
cp configs/teams/startup_team_v1.yaml configs/teams/my_team.yaml
```

YAML のスキーマについては [チーム定義 YAML スキーマリファレンス](TEAM_YAML_SCHEMA.md) を参照。

### カスタマイズ可能な項目

| 項目 | 設定箇所 | 説明 |
| --- | --- | --- |
| メンバーの追加・削除 | `members` | チーム内の参加者を自由に定義 |
| プロンプトの変更 | `members[].prompt` | 各メンバーの振る舞いを指示するプロンプト |
| ツールの付与 | `members[].tools` | メンバーが利用できるツール（例: `[google_search]`） |
| Step の構成 | `steps` | 議論の段階・参加メンバー・目的を定義 |
| 期待されるアウトプット | `steps[].output` | 各 Step で期待される成果物の形式を定義 |
| 議論の方針 | `steps[].prompt` | 各 Step での議論の進め方を指示 |
| ラウンド数 | `steps[].rounds` | 各 Step で何ラウンド議論するか（デフォルト: 2） |
| LLM モデル | `.env` の `LLM_MODEL_AGENT` | 使用する Gemini モデルを切り替え |

### プロンプト実験の例

同じチーム構成でプロンプトだけを変えた YAML を複数用意し、結果を比較する。

```
configs/teams/
  startup_team_v1.yaml          # 基本プロンプト
  startup_team_v2_detailed.yaml # より詳細な行動指針を記述
  startup_team_v3_strict.yaml   # 厳格な制約条件を追加
```

それぞれを実行し、`outputs/` に生成されるレポートを比較することで、プロンプトの違いが成果物に与える影響を検証できる。

## 出力

### レポートの出力先

```
outputs/{チーム ID}_{タイムスタンプ}.md
```

例: `outputs/startup_team_v1_20260221_193000.md`

### レポートの構成

レポートの詳細な構成については [議論フロー仕様](DISCUSSION_FLOW.md) を参照。
