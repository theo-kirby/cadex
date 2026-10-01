# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot11 blind video judge (P1): its runner and its receipts.

``docs/probes/ot11/README.md`` freezes what the judge sees, which seeds it
judges, how many calls are made and the bar; ``runner/judge.py`` is the
procedure. The literals below pin the procedure: the instructions the judge
is given around the rubric, the isolation of each call, and the rule that a
refusal, an error or another model's answer is never a score. The committed
receipts are held to what the runner would compute from their own calls, and
so are the four receipts of the floor-marks probe that changed nothing
(ADR-461).

No test here calls a model. The end-to-end ones run the runner against a
stand-in executable that answers as the harness does.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
OT11 = REPO / "docs/probes/ot11"
CONTRACT = json.loads((OT11 / "contract.json").read_text(encoding="utf-8"))
README = (OT11 / "README.md").read_text(encoding="utf-8")

_spec = importlib.util.spec_from_file_location("ot11_judge", OT11 / "runner/judge.py")
judge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(judge)

RUBRIC_SHA256 = "dc081807c28033ec7c729ff967d078a2dfdd884f088d8fa7cf130255048d83ed"
INSTRUCTIONS_SHA256 = "dfeab7c7624b2a7472baaaf1e6b9d20ebaba0c80f96953ea203d5725ef02b706"
TRAITS = ["V1", "V2", "V3", "V4"]
BAR = {"total_min": 9, "total_max": 12, "trait_min": 2, "scope": "each judged seed"}
JUDGED = [1101, 1105, 1110]
#: label -> (behaviour, the evaluation receipt its sheets were drawn from)
NEGATIVES = {"w2-2": ("walk", "p2-w2-2-evaluation.json"),
             "robin": ("balance", "p2-robin-evaluation.json")}
#: The one sentence the floor-marks probe's second arm added to the instructions (ADR-461).
MARKS_SENTENCE = ("In the detail sheet the floor keeps a light mark wherever a part of the robot has "
                  "touched it since the episode began; the marks are fixed to the floor, so a part set "
                  "down and lifted leaves a separate print and a part dragged across the floor leaves a "
                  "streak or a smear.")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scores(*values: int) -> dict:
    return {trait: {"score": value, "reason": "x"} for trait, value in zip(TRAITS, values)}


def _envelope(result: str, **over) -> str:
    return json.dumps({"is_error": False, "result": result, "session_id": "s", "duration_ms": 1,
                       "num_turns": 3, "total_cost_usd": 0.1, "stop_reason": "end_turn",
                       "modelUsage": {"claude-opus-5-5": {"outputTokens": 1}}, **over})


# -- the procedure ------------------------------------------------------------

def test_the_rubric_the_judge_is_given_is_the_frozen_one() -> None:
    assert _sha(judge.rubric().encode()) == RUBRIC_SHA256 == CONTRACT["judge"]["rubric_sha256"]
    assert judge.system_prompt() == judge.INSTRUCTIONS + judge.rubric()


def test_the_instructions_round_the_rubric_are_pinned_and_name_no_behaviour() -> None:
    """They say what a sheet is and what to reply with. Changing them after a
    score exists is a recorded decision, so the digest is a literal here."""

    assert _sha(judge.INSTRUCTIONS.encode()) == INSTRUCTIONS_SHA256
    for word in ("walk", "step", "balanc", "reach", "arm", "leg", "wheel", "shove", "target", "fall"):
        assert word not in judge.INSTRUCTIONS.lower(), word


def test_each_call_is_a_fresh_pinned_model_with_no_fallback_and_one_directory() -> None:
    assert (judge.MODEL, judge.CALLS, tuple(TRAITS)) == ("claude-opus-5-5", 3, judge.TRAITS)
    assert (CONTRACT["judge"]["model"], CONTRACT["judge"]["fallback"], CONTRACT["judge"]["calls"]) == (
        "claude-opus-5-5", None, 3)
    argv = judge.command("claude", "PROMPT", Path("/sheets"))
    assert "--fallback-model" not in argv
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--tools") + 1] == "Read" == argv[argv.index("--allowedTools") + 1]
    assert argv[argv.index("--setting-sources") + 1] == "project"
    for flag in ("--strict-mcp-config", "--no-session-persistence", "--disable-slash-commands"):
        assert flag in argv, flag
    assert "--mcp-config" not in argv
    assert [argv[i + 1] for i, a in enumerate(argv) if a == "--add-dir"] == ["/sheets"]
    assert argv[argv.index("--system-prompt") + 1] == judge.INSTRUCTIONS + judge.rubric()
    assert argv[argv.index("-p") + 1] == "PROMPT"


@pytest.mark.parametrize("behaviour", ["walk", "reach", "balance"])
def test_the_judge_sees_the_rubric_the_intent_and_the_two_sheets_and_nothing_else(behaviour) -> None:
    intent = CONTRACT["behaviours"][behaviour]["intent"]
    message = judge.user_prompt(intent, Path("/w/filmstrip/overview.png"), Path("/w/filmstrip/detail.png"))
    assert message == ("What the robot was asked to do:\n" + intent + "\n\n"
                       "Overview sheet: /w/filmstrip/overview.png\n"
                       "Detail sheet: /w/filmstrip/detail.png\n\n"
                       "Read both, then reply with the JSON object only.")
    # Beside the frozen rubric: no reward, no metric, no seed, no project,
    # no report, no policy and no verdict.
    seen = judge.INSTRUCTIONS + message
    for leak in ("reward", "1101", "1105", "1110", "seed", "ot11", "ot10", "ot9", "w2", "Robin", "robin",
                 "cadex", "Cadex", "evaluation", "policy", "slip_share", "steps_min", "hip height",
                 "COM height", "predicate", "pass", "fail"):
        assert leak not in seen, leak


def test_a_reply_is_four_integer_scores_or_it_is_not_a_score() -> None:
    good = _scores(2, 1, 3, 0)
    assert judge.parse("```json\n" + json.dumps(good) + "\n```")["V3"]["score"] == 3
    for bad in ({**good, "V3": {"score": 4}}, {**good, "V3": {"score": 1.5}}, {**good, "V3": {"score": True}},
                {k: v for k, v in good.items() if k != "V4"}, {**good, "V5": {"score": 1}}):
        with pytest.raises(judge.JudgeError):
            judge.parse(json.dumps(bad))
    with pytest.raises(judge.JudgeError):
        judge.parse("I can't score this.")


def test_each_trait_is_the_median_of_the_calls_and_the_bar_is_the_frozen_one() -> None:
    bar = CONTRACT["judge"]["bar"]
    assert bar == BAR
    calls = [_scores(0, 3, 2, 3), _scores(3, 3, 2, 1), _scores(1, 3, 2, 2)]
    assert judge.aggregate(calls, bar) == {"medians": dict(zip(TRAITS, (1, 3, 2, 2))), "total": 8,
                                           "meets_bar": False}
    # Nine with no trait under two meets it; nine with a one does not; eight does not.
    assert judge.aggregate([_scores(3, 2, 2, 2)] * 3, bar)["meets_bar"] is True
    assert judge.aggregate([_scores(3, 3, 2, 1)] * 3, bar)["meets_bar"] is False
    assert judge.aggregate([_scores(2, 2, 2, 2)] * 3, bar)["meets_bar"] is False
    assert judge.aggregate([_scores(3, 3, 3, 3)] * 3, bar) == {
        "medians": dict.fromkeys(TRAITS, 3), "total": 12, "meets_bar": True}


def test_an_error_a_refusal_and_another_models_answer_are_not_scores() -> None:
    reply = json.dumps(_scores(0, 0, 0, 0))
    scores, receipt = judge.read_envelope(_envelope(reply))
    assert scores["V1"]["score"] == 0 and receipt["reply"] == reply
    assert list(receipt["modelUsage"]) == ["claude-opus-5-5"]
    for stdout, code, why in (
            (_envelope(reply), 1, "claude exited 1"),
            ("not json", 0, "no JSON envelope"),
            (_envelope("usage limit reached", is_error=True), 0, "reported an error"),
            # A refusal that happens to carry scores is still a refusal.
            (_envelope(reply, stop_reason="refusal"), 0, "refused"),
            (_envelope(reply, modelUsage={"claude-sonnet-5-5": {}}), 0, "not by claude-opus-5-5 alone"),
            (_envelope(reply, modelUsage={"claude-opus-5-5": {}, "claude-haiku-4-5-20251001": {}}), 0,
             "not by claude-opus-5-5 alone"),
            (_envelope(reply, modelUsage={}), 0, "no named model"),
            (_envelope("I would rather not judge this."), 0, "no JSON object")):
        with pytest.raises(judge.JudgeError, match=why):
            judge.read_envelope(stdout, code)


def test_a_failed_call_is_retried_once_and_a_second_failure_is_no_score() -> None:
    good = (_scores(1, 1, 1, 1), {"reply": "r"})
    script = iter([judge.JudgeError("flaky"), good, good, good])

    def call(_claude, _intent, _paths):
        step = next(script)
        if isinstance(step, Exception):
            raise step
        return step

    calls, raw, failure = judge.judge_seed("claude", "intent", {}, call=call)
    assert failure is None and len(calls) == 3
    assert raw[0] == {"error": "flaky", "attempt": 1} and len(raw) == 4

    script = iter([good, judge.JudgeError("refused"), judge.JudgeError("refused again"), good])
    calls, raw, failure = judge.judge_seed("claude", "intent", {}, call=call)
    assert failure == "refused again" and len(calls) == 1
    assert [row.get("attempt") for row in raw] == [None, 1, 2]


# -- the sheets, read through the evaluation --------------------------------------

def _evaluation(root: Path, seed: int = 1101, *, state: str = "ready", frames: int = 12) -> Path:
    out = root / "evaluations" / "rev-policy"
    out.mkdir(parents=True)
    film = {"schema": "cadex-evaluation-film-v1", "state": state, "style_sha256": "f" * 64, "seeds": []}
    row = {"seed": seed, "trace_sha256": "t" * 64}
    for kind in ("overview", "detail"):
        data = f"{kind} of seed {seed}".encode()
        (out / f"seed-{seed}-{kind}.png").write_bytes(data)
        row[kind] = {"file": f"seed-{seed}-{kind}.png", "sha256": _sha(data), "frames": frames,
                     "times_s": [0.1 * k for k in range(frames)], "view": kind + " view"}
    row["detail"]["follows"] = "c_body"
    film["seeds"].append(row)
    (out / "evaluation.json").write_text(json.dumps({
        "schema": "cadex-evaluation-v1", "verdict": "fail", "accepted_revision": "a" * 64,
        "policy_sha256": "p" * 64, "task_sha256": "k" * 64, "model_sha256": "m" * 64, "film": film}))
    return out


def test_the_sheets_judged_are_the_ones_the_evaluation_recorded(tmp_path) -> None:
    out = _evaluation(tmp_path / "a")
    facts, paths = judge.sheets(out, 1101, CONTRACT)
    assert [p.name for p in paths.values()] == ["seed-1101-overview.png", "seed-1101-detail.png"]
    assert facts["evaluation"]["policy_sha256"] == "p" * 64 and facts["trace_sha256"] == "t" * 64
    assert [row["sheet"] for row in facts["sheets"]] == ["overview", "detail"]
    assert facts["sheets"][1]["follows"] == "c_body" and facts["film_style_sha256"] == "f" * 64

    (out / "seed-1101-detail.png").write_bytes(b"another film")
    with pytest.raises(judge.JudgeError, match="seed-1101-detail.png is not the sheet this evaluation recorded"):
        judge.sheets(out, 1101, CONTRACT)
    with pytest.raises(judge.JudgeError, match="seed 1105 was not filmed"):
        judge.sheets(out, 1105, CONTRACT)
    with pytest.raises(judge.JudgeError, match="the contract judges 1101, 1105, 1110"):
        judge.sheets(_evaluation(tmp_path / "b", 1102), 1102, CONTRACT)
    with pytest.raises(judge.JudgeError, match="film is failed"):
        judge.sheets(_evaluation(tmp_path / "c", state="failed"), 1101, CONTRACT)
    with pytest.raises(judge.JudgeError, match="has 7 frames, not the 12"):
        judge.sheets(_evaluation(tmp_path / "d", frames=7), 1101, CONTRACT)


# -- end to end, against a stand-in for the harness ---------------------------------

_STAND_IN = """#!{python}
import json, os, sys
from pathlib import Path
argv = sys.argv[1:]
here = Path.cwd()
sheets = Path(argv[argv.index('--add-dir') + 1])
seen = {{
    'cwd_holds': sorted(p.name for p in here.iterdir()),
    'sheets': sorted(p.name for p in sheets.iterdir()),
    'sheet_bytes': {{p.name: p.read_bytes().decode() for p in sheets.iterdir()}},
    'in_repo': str(here).startswith({repo!r}),
    'prompt': argv[argv.index('-p') + 1],
    'cadex_env': sorted(k for k in os.environ if k.startswith('CADEX_')),
}}
log = Path({log!r})
calls = json.loads(log.read_text()) if log.exists() else []
calls.append(seen)
log.write_text(json.dumps(calls))
replies = json.loads(Path({replies!r}).read_text())
print(json.dumps(replies[min(len(calls), len(replies)) - 1]))
"""


def _stand_in(tmp_path: Path, replies: list[dict]) -> tuple[Path, Path]:
    log = tmp_path / "calls.json"
    (tmp_path / "replies.json").write_text(json.dumps(replies))
    claude = tmp_path / "claude"
    claude.write_text(_STAND_IN.format(python=sys.executable, repo=str(REPO), log=str(log),
                                       replies=str(tmp_path / "replies.json")))
    claude.chmod(claude.stat().st_mode | stat.S_IXUSR)
    return claude, log


def test_a_seed_is_judged_in_three_blind_calls_and_the_receipt_says_what_was_shown(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CADEX_PROJECT", "ot11-secret")
    out = _evaluation(tmp_path)
    replies = [json.loads(_envelope(json.dumps(_scores(*row)))) for row in ((1, 0, 2, 1), (0, 0, 2, 3), (1, 1, 1, 2))]
    claude, log = _stand_in(tmp_path, replies)
    receipt = tmp_path / "score.json"
    code = judge.main(["walk", "--evaluation", str(out), "--seed", "1101", "--label", "fixture",
                       "--out", str(receipt), "--claude", str(claude)])
    assert code == 0
    calls = json.loads(log.read_text())
    assert len(calls) == 3
    for call in calls:
        # A new directory outside the repository holding the two sheets under
        # names that say nothing, and no product environment.
        assert call["cwd_holds"] == ["filmstrip"] and call["sheets"] == ["detail.png", "overview.png"]
        assert call["sheet_bytes"] == {"overview.png": "overview of seed 1101", "detail.png": "detail of seed 1101"}
        assert call["in_repo"] is False and call["cadex_env"] == []
        assert CONTRACT["behaviours"]["walk"]["intent"] in call["prompt"]
        assert "1101" not in call["prompt"] and "fixture" not in call["prompt"]
    result = json.loads(receipt.read_text())
    assert (result["schema"], result["label"], result["behaviour"], result["seed"]) == (
        "ot11-judge-v1", "fixture", "walk", 1101)
    assert (result["model"], result["fallback"], result["calls"]) == ("claude-opus-5-5", None, 3)
    assert result["rubric_sha256"] == RUBRIC_SHA256 and result["instructions_sha256"] == INSTRUCTIONS_SHA256
    assert result["intent_sha256"] == _sha(CONTRACT["behaviours"]["walk"]["intent"].encode())
    assert result["medians"] == dict(zip(TRAITS, (1, 0, 2, 2))) and result["total"] == 5
    assert result["meets_bar"] is False and result["bar"] == BAR
    assert [row["sha256"] for row in result["sheets"]] == [
        _sha(b"overview of seed 1101"), _sha(b"detail of seed 1101")]
    assert len(result["raw"]) == 3 and not (tmp_path / "score.json.failed.json").exists()


def test_a_refusal_writes_no_score_and_keeps_what_happened(tmp_path) -> None:
    out = _evaluation(tmp_path)
    good = json.loads(_envelope(json.dumps(_scores(3, 3, 3, 3))))
    refusal = json.loads(_envelope("I can't help with that.", stop_reason="refusal"))
    claude, log = _stand_in(tmp_path, [good, refusal, refusal])
    receipt = tmp_path / "score.json"
    code = judge.main(["balance", "--evaluation", str(out), "--seed", "1101", "--out", str(receipt),
                       "--claude", str(claude)])
    assert code == 2 and not receipt.exists()
    kept = json.loads((tmp_path / "score.json.failed.json").read_text())
    assert kept["state"] == "no score" and "refused" in kept["error"]
    assert "medians" not in kept and "meets_bar" not in kept
    assert [("scores" in row, row.get("attempt")) for row in kept["raw"]] == [(True, None), (False, 1), (False, 2)]
    assert len(json.loads(log.read_text())) == 3


def test_a_seed_the_contract_does_not_judge_is_refused_before_any_call(tmp_path, capsys) -> None:
    out = _evaluation(tmp_path, 1102)
    claude, log = _stand_in(tmp_path, [])
    code = judge.main(["walk", "--evaluation", str(out), "--seed", "1102", "--out", str(tmp_path / "s.json"),
                       "--claude", str(claude)])
    assert code == 2 and not log.exists() and "not a judged seed" in capsys.readouterr().err


# -- the procedure on the page, and the receipts ---------------------------------------

def test_the_procedure_is_pinned_in_the_contract_and_stated_on_the_page() -> None:
    procedure = CONTRACT["judge_procedure"]
    assert procedure["runner"] == "runner/judge.py" and (OT11 / procedure["runner"]).is_file()
    assert (procedure["effort"], procedure["instructions_sha256"]) == (judge.EFFORT, INSTRUCTIONS_SHA256)
    assert judge.EFFORT == "high" and procedure["adr"] == "ADR-460"
    flat = " ".join(README.split())
    for phrase in ("### The procedure (ADR-460)", "`--model claude-opus-5-5`, no fallback model, effort `high`",
                   "one tool (`Read`), no MCP servers, no skills",
                   "The seed number and `--label` go into the receipt and never to the judge.",
                   "or an answer from any model but `claude-opus-5-5` writes no score"):
        assert phrase in flat, phrase
    decisions = (REPO / "docs/DECISIONS.md").read_text(encoding="utf-8")
    assert "## ADR-460 — " in decisions
    # The frozen judge block is as it was: the procedure adds beside it.
    assert set(CONTRACT["judge"]) == {"model", "fallback", "calls", "aggregation", "traits", "rubric_sha256",
                                      "sees", "sees_nothing_else", "judged_seeds", "filmstrip", "bar"}
    assert CONTRACT["judge"]["filmstrip"]["detail"]["view"] == "side-on, following the base"


def test_both_negatives_were_judged_on_the_three_seeds_and_neither_meets_the_bar() -> None:
    """The committed receipts: three scored calls a seed from the pinned model
    alone, on the sheets the evaluation receipt records, with the medians,
    total and bar the runner computes from those calls."""

    flat = " ".join(README.split())
    judged = CONTRACT["known_negatives"]["judged"]
    shown = {"w2-2": "`w2-2`", "robin": "Robin"}
    for label, (behaviour, evaluation) in NEGATIVES.items():
        report = json.loads((OT11 / "retained" / evaluation).read_text(encoding="utf-8"))
        filmed = {row["seed"]: row for row in report["film"]["seeds"]}
        assert judged[label]["behaviour"] == behaviour and judged[label]["meets_bar"] is False
        assert sorted(map(int, judged[label]["seeds"])) == JUDGED == sorted(filmed)
        for seed in JUDGED:
            name = f"judge-{label}-seed-{seed}.json"
            text = (OT11 / "retained" / name).read_text(encoding="utf-8")
            assert "/home/" not in text and "/tmp/" not in text, name
            receipt = json.loads(text)
            assert (receipt["schema"], receipt["label"], receipt["behaviour"], receipt["seed"]) == (
                "ot11-judge-v1", label, behaviour, seed)
            assert (receipt["model"], receipt["fallback"], receipt["effort"], receipt["calls"]) == (
                "claude-opus-5-5", None, "high", 3)
            assert receipt["rubric_sha256"] == RUBRIC_SHA256
            assert receipt["instructions_sha256"] == INSTRUCTIONS_SHA256
            assert receipt["intent_sha256"] == _sha(CONTRACT["behaviours"][behaviour]["intent"].encode())
            # What was judged is what the evaluation measured and filmed.
            assert receipt["evaluation"]["policy_sha256"] == report["policy_sha256"]
            assert receipt["evaluation"]["verdict"] == "fail"
            assert receipt["trace_sha256"] == filmed[seed]["trace_sha256"]
            assert receipt["film_style_sha256"] == report["film"]["style_sha256"]
            assert [row["sha256"] for row in receipt["sheets"]] == [
                filmed[seed]["overview"]["sha256"], filmed[seed]["detail"]["sha256"]]
            assert receipt["sheets"][1]["follows"] == report["rig"]["base"]
            # Three scored calls, no error kept, each answered by the pinned model alone.
            scored = [row for row in receipt["raw"] if "scores" in row]
            assert len(scored) == len(receipt["raw"]) == 3
            assert all(list(row["modelUsage"]) == ["claude-opus-5-5"] for row in scored)
            assert all(judge.parse(row["reply"]) == row["scores"] for row in scored)
            computed = judge.aggregate([row["scores"] for row in scored], BAR)
            assert {key: receipt[key] for key in computed} == computed
            assert receipt["meets_bar"] is False and receipt["bar"] == BAR
            assert judged[label]["seeds"][str(seed)] == {"receipt": f"retained/{name}", **computed}
            row = "| {} | {} | {} | {} | **not met** |".format(
                shown[label], seed,
                " | ".join(str(computed["medians"][trait]) for trait in TRAITS), computed["total"])
            assert row in flat, row
    # The shuffle fails the judge on falling; on two seeds its manner reads as stepping.
    manner = [judged["w2-2"]["seeds"][str(seed)]["medians"]["V2"] for seed in JUDGED]
    control = [judged["w2-2"]["seeds"][str(seed)]["medians"]["V3"] for seed in JUDGED]
    assert manner == [2, 1, 2] and control == [0, 0, 0]
    assert "**`w2-2`: the judge does not see the shuffle.**" in flat
    assert "**Neither negative meets the bar on any judged seed**" in flat


def test_the_floor_marks_probe_left_the_manner_score_where_it_was_and_changed_nothing() -> None:
    """ADR-461: a detail sheet whose floor keeps a mark wherever the robot
    touched it, judged on the two ``w2-2`` seeds whose manner scored 2, as
    drawn (arm a) and with one sentence saying what a mark is (arm b). Every
    call of both arms still scored manner 2, so the film, the instructions
    and the contract are as they were."""

    flat = " ".join(README.split())
    report = json.loads((OT11 / "retained" / "p2-w2-2-evaluation.json").read_text(encoding="utf-8"))
    filmed = {row["seed"]: row for row in report["film"]["seeds"]}
    told = judge.INSTRUCTIONS.replace("bottom left. Read both", f"bottom left. {MARKS_SENTENCE} Read both")
    assert told != judge.INSTRUCTIONS and f"> {MARKS_SENTENCE}" in flat
    instructions = {"a": INSTRUCTIONS_SHA256, "b": _sha(told.encode())}
    styles = set()
    for arm in ("a", "b"):
        for seed in (1101, 1110):
            name = f"probe-marks-{arm}-w2-2-seed-{seed}.json"
            text = (OT11 / "retained" / name).read_text(encoding="utf-8")
            assert "/home/" not in text and "/tmp/" not in text, name
            receipt = json.loads(text)
            assert (receipt["schema"], receipt["behaviour"], receipt["seed"]) == ("ot11-judge-v1", "walk", seed)
            assert (receipt["model"], receipt["fallback"], receipt["effort"], receipt["calls"]) == (
                "claude-opus-5-5", None, "high", 3)
            assert receipt["rubric_sha256"] == RUBRIC_SHA256
            assert receipt["instructions_sha256"] == instructions[arm], name
            assert receipt["evaluation"]["policy_sha256"] == report["policy_sha256"]
            assert receipt["trace_sha256"] == filmed[seed]["trace_sha256"]
            # The same overview and the same moments; only the detail's floor differs.
            overview, detail = receipt["sheets"]
            assert overview["sha256"] == filmed[seed]["overview"]["sha256"]
            assert detail["sha256"] != filmed[seed]["detail"]["sha256"]
            assert detail["times_s"] == filmed[seed]["detail"]["times_s"]
            assert detail["follows"] == report["rig"]["base"]
            styles.add(receipt["film_style_sha256"])
            scored = [row for row in receipt["raw"] if "scores" in row]
            assert len(scored) == len(receipt["raw"]) == 3
            assert all(list(row["modelUsage"]) == ["claude-opus-5-5"] for row in scored)
            assert all(judge.parse(row["reply"]) == row["scores"] for row in scored)
            computed = judge.aggregate([row["scores"] for row in scored], BAR)
            assert {key: receipt[key] for key in computed} == computed
            # The finding: no call of either arm scored manner below 2.
            assert [row["scores"]["V2"]["score"] for row in scored] == [2, 2, 2], name
            assert computed["medians"] == {"V1": 1, "V2": 2, "V3": 0, "V4": 1} and not computed["meets_bar"]
            row = "| {} | {} | {} | {} |".format(
                {"a": "A: marks", "b": "B: marks and the sentence"}[arm], seed,
                " | ".join(str(computed["medians"][trait]) for trait in TRAITS), computed["total"])
            assert row in flat, row
            if seed == 1101:
                sheet = OT11 / "probe-marks-w2-2-seed-1101-detail.png"
                assert _sha(sheet.read_bytes()) == detail["sha256"] and sheet.stat().st_size <= 300 * 1024
    # One film drew all four, and it is not the film the contract's receipts were judged on.
    assert len(styles) == 1 and styles != {report["film"]["style_sha256"]}
    assert (OT11 / "retained" / "probe-marks.patch").is_file() and "probe-marks.patch" in flat
    # Not adopted: the film draws no floor marks (the patch's ``touched`` and
    # ``_marks`` are not in it; the target marker of ADR-463 is another
    # thing), the judge is told of none, and the probe added no decision.
    # The one added since records the limit the probe measured and changes
    # no frozen item.
    film_source = (REPO / "cli/cadex_cli/film.py").read_text(encoding="utf-8")
    assert "_marks(" not in film_source and "def touched" not in film_source
    assert "floor mark" not in film_source and "mark" not in judge.INSTRUCTIONS
    assert CONTRACT["judge_procedure"]["instructions_sha256"] == INSTRUCTIONS_SHA256
    # Later decisions (ADR-467 moved W10's window) are not about the judge.
    assert [row["adr"] for row in CONTRACT["decisions"]][:2] == ["ADR-454", "ADR-463"]
    assert all("judge" not in row["change"] and "mark" not in row["change"]
               for row in CONTRACT["decisions"][2:])
    assert CONTRACT["decisions"][1]["re_evaluated"].startswith("nothing:")
    assert "### A probe: floor marks in the detail sheet, measured and not adopted (ADR-461)" in README
    assert "## ADR-461 — " in (REPO / "docs/DECISIONS.md").read_text(encoding="utf-8")
