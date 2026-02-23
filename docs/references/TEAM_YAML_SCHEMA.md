# チーム定義 YAML スキーマリファレンス

チーム定義は `configs/teams/` 配下に YAML ファイルとして配置する。ファイル名は任意だが、チーム ID と一致させることを推奨する（例: `startup_team_v1.yaml`）。

## トップレベル

| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `id` | string | はい | チームの一意な識別子。ファイル名と一致させることを推奨。 |
| `name` | string | はい | チームの表示名。CLI でのチーム選択時に表示される。 |
| `description` | string | はい | チームの概要説明。CLI でのチーム選択時に表示される。 |
| `members` | list[Member] | はい | チームに所属するメンバーのリスト。 |
| `steps` | list[Step] | はい | 議論のステップを定義するリスト。定義順に実行される。 |

## Member

| フィールド | 型 | 必須 | デフォルト | 説明 |
| --- | --- | --- | --- | --- |
| `id` | string | はい | - | メンバーの識別子。チーム内でユニークであること。steps の `members` で参照される。 |
| `name` | string | はい | - | メンバーの表示名（例: "CEO（統合意思決定者）"）。レポートや進捗表示で使用される。 |
| `prompt` | string | はい | - | メンバーの挙動を指示する LLM 用プロンプト。YAML のリテラルブロック（`|`）で複数行記述可能。 |
| `tools` | list[string] | いいえ | `[]` | メンバーが利用できるツールの短縮名リスト。利用可能なツール名: `google_search`（Google 検索）。 |

## Step

| フィールド | 型 | 必須 | デフォルト | 説明 |
| --- | --- | --- | --- | --- |
| `id` | string | はい | - | ステップの識別子。`fallback` で参照される。 |
| `name` | string | はい | - | ステップの表示名。レポートや進捗表示で使用される。 |
| `members` | list[string] | はい | - | このステップに参加するメンバーの ID リスト。上位の `members` で定義された ID を参照する。 |
| `description` | string | はい | - | このステップの議論の目的。エージェントへのシステムコンテキストとして使用される。 |
| `output` | string | いいえ | `""` | このステップで期待されるアウトプットの形式。エージェントへのシステムコンテキストおよびレポートに使用される。 |
| `prompt` | string | いいえ | `""` | 議論の進め方の方針。エージェントへのシステムコンテキストとして使用される。 |
| `rounds` | int | いいえ | `2` | ラウンド数。1ラウンドで全参加メンバーが1回ずつ発言する。 |
| `fallback` | list[string] \| string \| null | いいえ | `[]` | 品質評価で不合格の場合に戻る先の Step ID のリスト。LLM がリストの中から最適な差し戻し先を選択する。自身の Step ID を含めることで、自身の再実行も候補にできる。空リスト `[]` または `null` の場合は差し戻しなし。後方互換として単一文字列も受け付ける。`output` が設定されている Step でのみ機能する。各 Step につき最大 1 回まで差し戻しが行われる。 |

## 記述例

```yaml
id: "startup_team_v1"
name: "スタートアップチーム(v1)"
description: "新規事業の構想するスタートアップチーム(v1)"

members:
  - id: ceo
    name: "CEO（統合意思決定者）"
    prompt: |
      あなたはスタートアップ企業のCEOです。
      ...
    tools: []

  - id: cmo
    name: "CMO（市場・顧客視点重視）"
    prompt: |
      あなたはスタートアップ企業のCMOです。
      ...
    tools: [google_search]

steps:
  - id: step1
    name: "ブレスト"
    members: [ceo, cmo]
    description: "楽観的に初期の事業アイディアをブレスト"
    output: "初期事業アイディアのリスト（各アイディアの概要・ターゲット顧客・想定される価値提案）"
    prompt: "自由な発想でアイディアを出すことを優先し、批判は控える。"
    rounds: 2
    fallback: []

  - id: step2
    name: "売上計画検証"
    members: [ceo, cmo, cfo]
    description: "Step 1 の結果に対して売上計画の現実性を検証"
    output: "各アイディアの売上モデル・コスト構造・損益分岐点の概算"
    prompt: "新規参加メンバー（CFO）の専門的視点を優先的に取り入れること。"
    rounds: 2
    fallback: [step2, step1]  # 自身 or step1
```
