# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：第1回は推測で回答していたが、今回は用語集を参照し正確な回答をしている。
- `--trace` で見えたツール呼び出し（ツール名と引数）：
search_glossary({'query': 'LoRA'})
search_glossary({'query': 'QLoRA'})
- 1つの質問での LLM 呼び出し回数（`requests`）：requests=2
- 追加したツールと、docstring に書いた説明：
agent.tool_plain(tools.make_quiz)も追加
以下はdocstringに書いた説明
def make_quiz(lecture: int) -> str:
    """指定した回の用語から1つを選び、確認問題と答えを返す。

    「第2回の確認問題を出して」のように、復習用の問題を求められたときに使う。
    """
    terms = [entry for entry in load_glossary() if entry["lecture"] == lecture]
    if not terms:
        return f"第{lecture}回の用語は用語集にありません。"

    entry = random.choice(terms)
    return json.dumps(
        {
            "question": f"「{entry['term']}」の意味は?",
            "answer": entry["definition"],
        },
        ensure_ascii=False,
    )

## 宿題

- 取り組んだレベル：発展b
- やったこと：コーディングエージェントのPiをCodespacesで動かし、公開されてい
るPiのシステムプロンプトと、自分のエージェントのINSTRUCTIONSを比べた
- 結果：
AIE2026のエージェント（INSTRUCTIONS）は、学習支援（用語の検索やヒントによる誘導など）に特化した固定の文字列として指示が定義されている。Piのエージェント（system-prompt.ts）は固定のテキストではなく、実行時の設定に応じて利用可能なツール、プロジェクトの指示、skillsなどを動的に組み合わせてプロンプトを構築するコードになっている。
- 気づき・疑問：プロンプトを単なる文章として固定するのではなく、Piのように設定に合わせて動的に生成・拡張する仕組みにすることで、多様なタスクに対応できる汎用性の高いエージェントが作れることがわかった。
