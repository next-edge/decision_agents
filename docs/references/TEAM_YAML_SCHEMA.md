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
| `goal` | string | はい | - | このステップの議論の目的。エージェントへのシステムコンテキストとして使用される。 |
| `rounds` | int | いいえ | `2` | ラウンド数。1ラウンドで全参加メンバーが1回ずつ発言する。 |
| `fallback` | string \| null | いいえ | `null` | 検証に耐えられない場合に戻る先の Step ID。`null` の場合は戻り先なし。現時点では未実装。 |

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
    goal: "楽観的に初期の事業アイディアをブレスト"
    rounds: 2
    fallback: null
```
