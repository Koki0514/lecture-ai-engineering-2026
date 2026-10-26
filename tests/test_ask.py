from types import SimpleNamespace

from app import ask as ask_module


class FakeChat:
    def __init__(self):
        self.messages = []

    def send_message(self, question):
        self.messages.append(question)
        return SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=12,
                candidates_token_count=7,
            ),
            text="回答",
        )


class FakeClient:
    chat = None

    def __init__(self, *, api_key):
        self.chats = self

    def create(self, *, model):
        return self.chat


def test_ask_prints_token_usage(capsys):
    fake_chat = FakeChat()

    assert ask_module.ask("質問", fake_chat) == "回答"
    assert fake_chat.messages == ["質問"]
    assert capsys.readouterr().out == "[usage] input_tokens=12 output_tokens=7\n"


def test_main_reuses_chat_for_followup(monkeypatch, capsys):
    fake_chat = FakeChat()
    monkeypatch.setattr(FakeClient, "chat", fake_chat)
    monkeypatch.setattr(ask_module.genai, "Client", FakeClient)
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr("sys.argv", ["app.ask", "最初の質問"])
    questions = iter(["追加質問", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(questions))

    ask_module.main()

    assert fake_chat.messages == ["最初の質問", "追加質問"]
    output = capsys.readouterr().out
    assert "[質問] 最初の質問" in output
    assert "[質問] 追加質問" in output