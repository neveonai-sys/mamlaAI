"""
tests/test_chitchat_guard.py
Tests for the zero-cost chitchat interceptor.
"""
import pytest
from core.chitchat_guard import check_chitchat, has_legal_signal

# ── inputs that should be blocked ─────────────────────────────────────────
CHITCHAT_INPUTS = [
    # greetings — exact
    "hi",
    "hello",
    "Hey!",
    "namaste",
    "Good morning",
    "good evening",
    # greetings — fuzzy (normalisation step)
    "hiii",
    "hellooo",
    "heyyyy",
    "hiiii!",
    # gibberish
    "fa",
    "ab",
    "xyz",
    "ksjd",
    "",          # empty
    "   ",       # whitespace only
    # how are you
    "how are you",
    "How are u",
    "what's up",
    # meta / architecture
    "what's your architecture",
    "who made you",
    "who created this",
    "are you an AI",
    "which model are you",
    "tell me about yourself",
    "introduce yourself",
    "what llm do you use",
    # gratitude
    "thanks",
    "Thank you",
    "thx",
    # farewell
    "bye",
    "Goodbye",
    "see you",
    # one-word acks
    "ok",
    "okay",
    "noted",
    "understood",
    "yes",
    "no",
    "cool",
    "great",
    "lol",
]

# ── inputs that should pass through to LLM ────────────────────────────────
LEGAL_INPUTS = [
    "What are my rights under Section 420 IPC?",
    "Explain Article 21 of the Constitution.",
    "What is the limitation period under CPC?",
    "Can I file anticipatory bail under Section 438 CrPC?",
    "Summarise this contract clause.",
    "Is there any precedent on res judicata in Bombay HC?",
    "What documents are needed for a divorce petition?",
    "My landlord evicted me without notice — what can I do?",
    "Draft a cease and desist letter.",
    # Edge: "understand" contains "understood" as substring — must NOT be blocked
    "I need to understand the doctrine of promissory estoppel.",
    # "okay" as part of a sentence — must NOT be blocked
    "Is it okay to challenge an FIR under Section 482 CrPC?",
]


@pytest.mark.parametrize("text", CHITCHAT_INPUTS)
def test_chitchat_is_blocked(text):
    is_cc, reply = check_chitchat(text)
    assert is_cc is True, f"Expected chitchat to be blocked: {text!r}"
    assert isinstance(reply, str) and len(reply) > 0


@pytest.mark.parametrize("text", LEGAL_INPUTS)
def test_legal_inputs_pass_through(text):
    is_cc, reply = check_chitchat(text)
    assert is_cc is False, f"Expected legal input to pass through: {text!r}"
    assert reply is None


def test_meta_reply_mentions_mamla():
    _, reply = check_chitchat("what's your architecture")
    assert "Mamla" in reply


def test_gratitude_reply_is_short():
    _, reply = check_chitchat("thanks")
    assert len(reply) < 200


def test_farewell_reply_is_short():
    _, reply = check_chitchat("bye")
    assert len(reply) < 200


# ── fuzzy normalisation ───────────────────────────────────────────────────

@pytest.mark.parametrize("text", ["hiii", "hellooo", "heyyyy", "hiiii!"])
def test_fuzzy_greetings_blocked(text):
    is_cc, reply = check_chitchat(text)
    assert is_cc is True, f"Fuzzy greeting should be blocked: {text!r}"
    assert reply is not None


# ── gibberish ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", ["fa", "ab", "xyz", "ksjd", "", "   "])
def test_gibberish_blocked(text):
    is_cc, reply = check_chitchat(text)
    assert is_cc is True, f"Gibberish should be blocked: {text!r}"
    assert reply is not None


def test_ipc_abbrev_not_gibberish():
    """'IPC' is a 3-letter legal abbreviation — must NOT be treated as gibberish."""
    is_cc, _ = check_chitchat("IPC")
    # IPC alone is ambiguous but NOT gibberish; guard should pass it through
    # (the T0 gate or T1 will handle it)
    assert is_cc is False


# ── has_legal_signal ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "What are my rights under Section 420 IPC?",
    "File an FIR",
    "I need bail",
    "Explain Article 21",
    "court hearing tomorrow",
    "my advocate said",
    "draft a petition",
])
def test_legal_signal_detected(text):
    assert has_legal_signal(text) is True, f"Expected legal signal in: {text!r}"


@pytest.mark.parametrize("text", [
    "hi",
    "how are you",
    "tell me a joke",
    "what's the weather",
    "hiii",
])
def test_no_legal_signal_in_chitchat(text):
    assert has_legal_signal(text) is False, f"Expected no legal signal in: {text!r}"
