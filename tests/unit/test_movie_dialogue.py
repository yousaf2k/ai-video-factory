"""
Movie dialogue layer - from screenplay to spoken lines in the shot prompts.

Covers the chain that used to leak dialogue at every step (measured on real
projects: ~20% of shots with dialogue, several films with none):
- core.dialogue matching/normalization helpers (verbatim + fuzzy line matching
  that also works for non-Latin scripts such as Urdu)
- story_engine: word-budget placeholders, dialogue normalization of scenes and
  the repair pass when Pass 2 drops or thins out the screenplay's lines
- shot_planner: voices in the cast block, dialogue planning rules and the
  coverage check that rewrites a scene whose shots do not speak every line
- r2v_composer: voice_type fallback for the voice-text embedding
- scene_graph passing dialogue through (the CLI path)
"""
import copy
import json

import pytest

import core.shot_planner as shot_planner
import core.story_engine as story_engine
from core.dialogue import (
    count_words,
    format_dialogue,
    missing_dialogue_lines,
    normalize_dialogue,
    normalize_scene_dialogue,
    normalize_speech,
    scene_dialogue,
    scripted_lines,
    speech_matches,
    unplaced_dialogue,
)
from core.r2v_composer import R2V_PROMPT_CHAR_LIMIT, _voice_texts_for_shot, compose_video_prompt
from core.scene_graph import build_scene_graph
from core.shot_planner import (
    DIALOGUE_INSTRUCTION,
    build_characters_block,
    build_dialogue_instruction,
    enforce_dialogue_coverage,
    plan_shots_batch,
    rebalance_speech_durations,
    shot_speaking_seconds,
    validate_video_prompt,
)
from core.story_engine import (
    build_story,
    detect_dialogue_language,
    dialogue_gaps,
    dialogue_in_wrong_script,
    dialogue_language_directive,
    ensure_dialogue_language,
    fill_story_placeholders,
    fit_story_dialogue,
    is_dialogue_story,
    overfull_scenes,
    scene_line_capacity,
    scene_speech_limit,
    speech_word_budgets,
)

URDU_ASK = "Bhai sahib, Faisalabad ja rahe hain?"
URDU_ANSWER = "Theek hai. Theek hai."
URDU_SCRIPT_ASK = "بھائی صاحب، فیصل آباد جا رہے ہیں؟"
# the same four lines in Latin transliteration and in Urdu script
TRANSLITRATED_LINES = [
    URDU_ASK,
    "Haan beta, baith jao. Aaj toofan chale gi, der mat karo.",
    "Yeh raaste mein bahut dhuand hai. Kya hum theek pahunchenge?",
    "Allah ki marzi. Tum bas apni zubaan band rakho aur aaram karo.",
]
URDU_SCRIPT_LINES = [
    URDU_SCRIPT_ASK,
    "ہاں بیٹا، بیٹھ جاؤ۔ آج تو آندھی چلے گی، دیر مت کرو۔",
    "یہ راستے میں بہت دھند ہے۔ کیا ہم ٹھیک پہنچیں گے؟",
    "اللہ کی مرزی۔ تم بس اپنی زبان بند رکھو اور آرام کرو۔",
]


class FakeProvider:
    """Sequential LLM stub: pops one canned response per ask() call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def ask(self, prompt, response_format=None):
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response) if not isinstance(response, str) else response

    def disable_thinking(self):
        return False


def _i2v_prompt(*lines):
    """Valid I2VA video prompt whose driver speaks `lines`."""
    speech = " ".join(
        f'The driver with a weary voice (S1) says: <d>[Urdu] {line}</d>' for line in lines)
    return (
        "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) "
        "is fully referenced.\n\n"
        "integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium shot frames "
        f"a taxi driver at night. {speech}\n\n"
        "overall_soundscape: Rain on the windshield and an idling engine.\n\n"
        "non_diegetic_music: N/A"
    )


def _shot(prompt, scene_id=0, duration=10, index=1):
    return {
        "scene_id": scene_id,
        "duration": duration,
        "camera": "close-up",
        "image_prompt": "a taxi driver",
        "motion_prompt": "the driver talks",
        "video_prompt": prompt,
        "soundfx_prompt": "rain",
        "music_prompt": "low strings",
        "index": index,
    }


SCENE = {
    "scene_id": 0,
    "location": "Taxi, Faisalabad road",
    "characters": "Driver, Passenger",
    "action": "The passenger gets in and gives a destination.",
    "narration": "",
    "dialogue": [
        {"speaker": "Driver", "line": URDU_ASK, "delivery": "hopeful"},
        {"speaker": "Passenger", "line": URDU_ANSWER, "delivery": "flat"},
    ],
    "scene_duration": 20,
}


# ------------------------------------------------------------ core.dialogue

class TestSpeechMatching:
    def test_normalize_drops_tag_punctuation_and_case(self):
        assert normalize_speech("[Urdu] Bhai sahib, Faisalabad ja rahe hain?") == \
            "bhai sahib faisalabad ja rahe hain"

    def test_normalize_keeps_non_latin_letters(self):
        urdu = normalize_speech("[Urdu] بارش ایک تحفہ ہے۔")
        assert urdu == "بارش ایک تحفہ ہے"

    def test_exact_match_for_short_lines(self):
        assert speech_matches("No.", "no")
        assert not speech_matches("No.", "No, I will not go there tonight")
        assert not speech_matches("", "anything")

    def test_verbatim_inside_a_longer_block_matches(self):
        assert speech_matches(URDU_ASK, f"[Urdu] {URDU_ASK}")

    def test_punctuation_and_typo_tolerated(self):
        assert speech_matches(URDU_ASK, "[Urdu] “Bhai sahib! Faisalabad ja rahe hain.”")
        assert speech_matches(URDU_ASK, "[Urdu] Bhai sahib, Faislabad ja rahe hain?")

    def test_different_line_does_not_match(self):
        assert not speech_matches(URDU_ASK, "[Urdu] Chal, utar ja yahan se.")
        # a truncated line is not the scripted line
        assert not speech_matches("I will not go there tonight with you", "I will not go")

    def test_count_words_ignores_bare_punctuation(self):
        assert count_words("Theek hai. Theek hai? —") == 4
        assert count_words("") == 0
        assert count_words(None) == 0

    def test_count_words_ignores_bracketed_cues(self):
        assert count_words("[Urdu] Bhai sahib, Faisalabad ja rahe hain?") == 6
        assert count_words("[Ambient Horror Sounds: low wind, distant dog, a ticking watch] "
                           "The fog comes first.") == 4


class TestNormalizeDialogue:
    def test_object_entries(self):
        entries = normalize_dialogue([
            {"speaker": "Driver", "line": " Where to? ", "delivery": "weary"},
            {"character": "Passenger", "text": "The fort.", "direction": "flat"},
            {"speaker": "Ghost", "line": "   "},  # no line -> dropped
            42, None,  # not entries -> dropped
        ])
        assert entries == [
            {"speaker": "Driver", "line": "Where to?", "delivery": "weary"},
            {"speaker": "Passenger", "line": "The fort.", "delivery": "flat"},
        ]

    def test_bare_string_in_a_list_keeps_its_line(self):
        assert normalize_dialogue(["Hello?", "Come in."]) == [
            {"speaker": "", "line": "Hello?", "delivery": ""},
            {"speaker": "", "line": "Come in.", "delivery": ""},
        ]

    def test_speaker_colon_strings_and_prose(self):
        assert normalize_dialogue([
            'Driver (weary): "Where to, brother?"',
            "Passenger: The old fort.",
            '"Just a line without a speaker"',
        ]) == [
            {"speaker": "Driver", "line": "Where to, brother?", "delivery": "weary"},
            {"speaker": "Passenger", "line": "The old fort.", "delivery": ""},
            {"speaker": "", "line": "Just a line without a speaker", "delivery": ""},
        ]
        assert normalize_dialogue('Driver: Turn here.\n\nPassenger (sharp): Not yet.') == [
            {"speaker": "Driver", "line": "Turn here.", "delivery": ""},
            {"speaker": "Passenger", "line": "Not yet.", "delivery": "sharp"},
        ]

    def test_degenerate_values(self):
        assert normalize_dialogue(None) == []
        assert normalize_dialogue(42) == []
        assert scene_dialogue("not a scene") == []

    def test_normalize_scene_dialogue_only_touches_dialogue_scenes_unless_forced(self):
        story = {"scenes": [
            {"scene_id": 0, "narration": "x"},
            {"scene_id": 1, "narration": "y", "dialogue": ["Driver: Hello."]},
        ]}
        assert normalize_scene_dialogue(story) == 1
        assert "dialogue" not in story["scenes"][0]
        assert story["scenes"][1]["dialogue"] == [
            {"speaker": "Driver", "line": "Hello.", "delivery": ""}]
        assert normalize_scene_dialogue(story, force=True) == 1
        assert story["scenes"][0]["dialogue"] == []


class TestScriptedLines:
    SCREENPLAY = (
        'The fog rolls in. DAWA FAROSH (hopeful): "Bhai sahib, Faisalabad ja rahe hain?"\n'
        'The driver does not turn. NARRATOR (voice-over): "Three in the morning. The bus is late."\n'
        'A sign reads "Chak 47" in faded paint. Dawa Farosh (laughing): "Theek hai. Theek hai."\n'
        'He whispers, "so-called brave" to himself.\n'
    )

    def test_only_cued_non_narrator_quotes(self):
        assert scripted_lines(self.SCREENPLAY) == [URDU_ASK, URDU_ANSWER]

    def test_prose_without_cues_falls_back_to_quotes(self):
        assert scripted_lines('She said she would "never go back there" and left.') == \
            ["never go back there"]

    def test_missing_lines_detected_verbatim(self):
        scenes = [{"dialogue": [{"speaker": "Dawa Farosh", "line": URDU_ASK}]}]
        assert missing_dialogue_lines([URDU_ASK, URDU_ANSWER], scenes) == [URDU_ANSWER]
        assert missing_dialogue_lines([URDU_ASK], scenes) == []


class TestUnplacedDialogue:
    def test_all_placed(self):
        shots = [_shot(_i2v_prompt(URDU_ASK)), _shot(_i2v_prompt(URDU_ANSWER))]
        assert unplaced_dialogue([SCENE], shots) == {}

    def test_missing_line_reported_with_its_entry(self):
        shots = [_shot(_i2v_prompt(URDU_ASK)), _shot(_i2v_prompt())]
        missing = unplaced_dialogue([SCENE], shots)
        assert [e["line"] for e in missing[0]] == [URDU_ANSWER]

    def test_line_split_across_sub_shots_counts_as_placed(self):
        prompt = _i2v_prompt("Theek hai.").replace(
            "</d>", "</d> <scenetrans> [Shot 2] At 00:02.000, the camera cuts to the passenger "
                    "who finishes, <d>[Urdu] Theek hai.</d>", 1)
        assert unplaced_dialogue([SCENE], [_shot(_i2v_prompt(URDU_ASK)), _shot(prompt)]) == {}

    def test_scene_id_type_mismatch_still_matches(self):
        shots = [_shot(_i2v_prompt(URDU_ASK), scene_id="0"), _shot(_i2v_prompt(URDU_ANSWER), scene_id="0")]
        assert unplaced_dialogue([SCENE], shots) == {}

    def test_scene_without_dialogue_or_shots(self):
        assert unplaced_dialogue([{"scene_id": 3, "narration": "x"}], []) == {}
        assert unplaced_dialogue([], [_shot(_i2v_prompt())]) == {}

    def test_format_dialogue(self):
        assert format_dialogue(SCENE["dialogue"]).splitlines() == [
            f'1. Driver (hopeful): "{URDU_ASK}"',
            f'2. Passenger (flat): "{URDU_ANSWER}"',
        ]


# ----------------------------------------------------------- story_engine

class TestStoryWordBudgets:
    def test_budgets_follow_the_configured_shares(self, monkeypatch):
        import config
        monkeypatch.setattr(config, "MOVIE_DIALOGUE_SHARE", 0.40)
        monkeypatch.setattr(config, "MOVIE_NARRATION_SHARE", 0.15)
        # 120s * 2.5 words/s = 300 spoken words -> 120 dialogue + 45 narration
        assert speech_word_budgets(120) == (120, 45)

    def test_placeholders_filled(self):
        prompt = ("{VIDEO_LENGTH} {MASTER_WORD_COUNT} {DIALOGUE_WORD_COUNT} {NARRATION_WORD_COUNT} "
                  "{DIALOGUE_LANGUAGE}")
        assert fill_story_placeholders(prompt, 120) == \
            "120 300 120 45 the language the IDEA names for the dialogue - English if it names none"

    def test_placeholders_untouched_without_target_length(self):
        assert fill_story_placeholders("{DIALOGUE_WORD_COUNT}", None) == "{DIALOGUE_WORD_COUNT}"
        # the language needs no target length
        assert fill_story_placeholders("{DIALOGUE_LANGUAGE}", None, "Urdu") == "Urdu"
        assert fill_story_placeholders("{DIALOGUE_LANGUAGE}", None, "Urdu", True) == \
            "Urdu written in Latin transliteration (as the IDEA asks)"

    def test_only_movie_family_is_a_dialogue_story(self):
        assert is_dialogue_story("movie/horror")
        assert is_dialogue_story("Movie/Action")
        assert not is_dialogue_story("documentary/default")
        assert not is_dialogue_story("then_vs_now/then_vs_now")
        assert not is_dialogue_story("default")
        assert not is_dialogue_story(None)


class TestBuildStoryDialogue:
    # Enough words to meet the 60s dialogue budget's floor (60 words target)
    LINES = [
        URDU_ASK,
        "Haan beta, baith jao. Aaj toofan aane wala hai, der mat karo.",
        "Yeh raaste mein bahut fog hai. Kya hum theek pahunchenge?",
        "Allah ki marzi. Tum bas apni zubaan band rakho aur aaram karo.",
    ]

    def test_movie_prompts_carry_the_dialogue_budget(self, monkeypatch):
        provider = FakeProvider([
            {"title": "T", "style": "s", "master_script": f'DRIVER (weary): "{URDU_ASK}"'},
            {"title": "", "style": "", "scenes": [
                {"scene_id": 0, "narration": "", "scene_duration": 60,
                 "dialogue": [{"speaker": "Driver", "line": line} for line in self.LINES]},
            ]},
        ])
        monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

        story = json.loads(build_story("a night taxi", director_name="movie/horror", target_length=60))

        # 60s * 2.5 = 150 spoken words -> 60 dialogue / 22 narration (0.40 / 0.15)
        assert len(provider.prompts) == 2  # healthy dialogue: no repair pass
        assert "60 words of dialogue" in provider.prompts[0]
        assert "{DIALOGUE_WORD_COUNT}" not in provider.prompts[0]
        assert '"dialogue"' in provider.prompts[1]  # the scene schema asks for it
        assert [e["line"] for e in story["scenes"][0]["dialogue"]] == self.LINES

    def test_documentary_story_is_untouched(self, monkeypatch):
        provider = FakeProvider([
            {"title": "T", "style": "s", "master_script": "A river civilization rises."},
            {"title": "", "style": "", "scenes": [{"scene_id": 0, "narration": "n", "scene_duration": 60}]},
        ])
        monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

        story = json.loads(build_story(
            "an ancient city", director_name="documentary/default", target_length=60))

        assert len(provider.prompts) == 2
        assert "dialogue" not in provider.prompts[1].lower()
        assert "dialogue" not in story["scenes"][0]


class TestFitStoryDialogue:
    MASTER = (
        'The tonga stops. DAWA FAROSH (hopeful): "Bhai sahib, Faisalabad ja rahe hain?"\n'
        'The driver does not turn. DAWA FAROSH (laughing): "Theek hai. Theek hai."\n'
    )
    # Two 30s scenes: every line carried over, 10 spoken words, nothing over-full
    HEALTHY = {"title": "T", "style": "s", "scenes": [
        {"scene_id": 0, "narration": "", "scene_duration": 30, "dialogue": [
            {"speaker": "Dawa Farosh", "line": URDU_ASK, "delivery": "hopeful"}]},
        {"scene_id": 1, "narration": "", "scene_duration": 30, "dialogue": [
            {"speaker": "Dawa Farosh", "line": URDU_ANSWER, "delivery": "laughing"}]},
    ]}

    @staticmethod
    def _scene(scene_id, duration, lines, narration=""):
        return {"scene_id": scene_id, "narration": narration, "scene_duration": duration,
                "dialogue": [{"speaker": "Driver", "line": line} for line in lines]}

    def test_fit_limits(self):
        # a 20s scene may hold 15s of speech: words at 2.5/s plus a breath per line
        assert scene_speech_limit({"scene_duration": 20}) == 15.0
        assert scene_line_capacity({"scene_duration": 15}) == 2
        assert scene_line_capacity({"scene_duration": 24}) == 3
        assert scene_line_capacity({"scene_duration": None}) == 0
        ten = " ".join(["word"] * 10)
        twelve = " ".join(["word"] * 12)
        over = overfull_scenes([self._scene(0, 20, [ten] * 2),    # 9.2s of speech: fits
                                self._scene(1, 20, [ten] * 3),    # 13.8s: fits
                                self._scene(2, 20, [twelve] * 3),  # 16.2s: within a line's slack
                                self._scene(3, 20, [ten] * 4)])   # 18.4s: cannot play
        assert [i for i, _, _, _ in over] == [3]

    def test_no_repair_when_dialogue_is_carried_over_and_fits(self):
        # 10 dialogue words against a 20-word target is within the floor
        provider = FakeProvider([])
        story = fit_story_dialogue(provider, copy.deepcopy(self.HEALTHY), self.MASTER, 60, 20)
        assert provider.prompts == []
        assert story == self.HEALTHY

    def test_too_little_flags_a_thin_budget(self):
        few_words = {"scenes": self.HEALTHY["scenes"]}
        assert dialogue_gaps(self.MASTER, few_words["scenes"], 600)[2] is True

    def test_too_little_ignores_the_budget_for_short_films(self):
        # only a 40+ word target makes a word floor meaningful
        spoken = count_words(URDU_ASK) + count_words(URDU_ANSWER)
        assert dialogue_gaps(self.MASTER, self.HEALTHY["scenes"], 0) == ([], spoken, False)

    def test_lost_lines_are_judged_by_count(self):
        screenplay = "A: \"Where to?\"\nB: \"The fort.\"\nA: \"Not yet.\"\nB: \"Open it.\"\n"
        dropped = {"scenes": [self._scene(0, 30, []), self._scene(1, 30, [])]}
        missing, _, too_little = dialogue_gaps(screenplay, dropped["scenes"], 0)
        assert too_little is True
        assert len(missing) == 4

    def test_translation_is_not_a_lost_line(self):
        # the scene pass translated every line: same count, different words
        screenplay = "A: \"Where to?\"\nB: \"The fort.\"\nA: \"Not yet.\"\nB: \"Open it.\"\n"
        translated = {"scenes": [self._scene(0, 30, ["Kahan jana hai?", "Qila."]),
                                 self._scene(1, 30, ["Abhi nahi.", "Kholo ise."])]}
        missing, _, too_little = dialogue_gaps(screenplay, translated["scenes"], 0)
        assert (missing, too_little) == ([], False)

    def test_a_screenplay_that_overshot_may_be_trimmed_to_what_fits(self):
        screenplay = "\n".join(f'A (flat): "This is screenplay line number {i} of many."'
                              for i in range(23))
        scenes = [self._scene(i, 15, [f"Line {i} a", f"Line {i} b"]) for i in range(8)]  # 16 lines
        assert dialogue_gaps(screenplay, scenes, 0) == ([], 48, False)
        # two 15s scenes have time for 4 lines; carrying only 2 of them is a loss
        thinned = [scenes[0], self._scene(1, 15, [])]
        assert dialogue_gaps(screenplay, thinned, 0)[2] is True

    def test_lost_lines_are_restored_and_the_repair_accepted(self):
        dropped = copy.deepcopy(self.HEALTHY)
        for scene in dropped["scenes"]:
            scene["dialogue"] = []
        repaired = copy.deepcopy(self.HEALTHY)
        provider = FakeProvider([repaired])

        story = fit_story_dialogue(provider, dropped, self.MASTER, 60, 60)

        assert len(provider.prompts) == 1
        repair = provider.prompts[0]
        assert URDU_ASK in repair and URDU_ANSWER in repair  # the missing lines are named
        assert '"dialogue"' in repair
        assert [s["dialogue"][0]["line"] for s in story["scenes"]] == [URDU_ASK, URDU_ANSWER]
        # only the scenes are taken from the repair; the story's own header stays
        assert story["title"] == "T"

    def test_an_overfull_scene_is_tightened_and_the_rest_kept(self):
        # three 14-word lines in 20s: 18.6s of speech (breaths included), at most 15 fit
        long_lines = [
            "Listen to me carefully, brother, because the road beyond the old canal is closed.",
            "You cannot take that cart any further tonight, turn it around and go back.",
            "The fog has swallowed the whole road ahead, and nothing that enters it returns.",
        ]
        story = copy.deepcopy(self.HEALTHY)
        story["scenes"][0].update(scene_duration=20, dialogue=[
            {"speaker": "Dawa Farosh", "line": line} for line in long_lines])
        second = story["scenes"][1]
        tightened = {"scenes": [
            {"scene_id": 0, "narration": "", "scene_duration": 99, "dialogue": [
                {"speaker": "Dawa Farosh", "line": "Listen to me, brother."},
                {"speaker": "Dawa Farosh", "line": "The road is closed."}]},
            {"scene_id": 1, "narration": "", "scene_duration": 30, "dialogue": []},
        ]}
        provider = FakeProvider([tightened])

        fitted = fit_story_dialogue(provider, story, self.MASTER, 60, 60)

        assert overfull_scenes(fitted["scenes"]) == []
        assert [e["line"] for e in fitted["scenes"][0]["dialogue"]] == \
            ["Listen to me, brother.", "The road is closed."]
        assert fitted["scenes"][0]["scene_duration"] == 20  # the film's timing, not the repair's
        assert fitted["scenes"][1] is second                 # untouched scenes keep their object
        repair = provider.prompts[0]
        assert "Scene 0 (20s) holds 3 dialogue lines" in repair
        assert "at most 15 seconds of speech fit" in repair and "at most 2 lines" in repair

    def test_silencing_an_overfull_scene_is_not_a_fix(self):
        # 6 lines of 8 words in 20s: 22.8s of speech, over a 15s limit
        story = copy.deepcopy(self.HEALTHY)
        story["scenes"][0].update(scene_duration=20, dialogue=[
            {"speaker": "Dawa Farosh", "line": f"This is spoken line number {i} of them"}
            for i in range(6)])
        provider = FakeProvider([{"scenes": [
            {"scene_id": 0, "narration": "", "scene_duration": 20, "dialogue": []}, *story["scenes"][1:]]}])
        assert fit_story_dialogue(provider, story, self.MASTER, 60, 60) == story

    def test_repair_that_changes_the_scene_count_is_rejected(self):
        dropped = copy.deepcopy(self.HEALTHY)
        dropped["scenes"][1]["dialogue"] = []
        provider = FakeProvider([{"scenes": self.HEALTHY["scenes"][:1]}])
        assert fit_story_dialogue(provider, dropped, self.MASTER, 60, 60) == dropped

    def test_repair_that_does_not_improve_anything_is_rejected(self):
        dropped = copy.deepcopy(self.HEALTHY)
        dropped["scenes"][1]["dialogue"] = []
        provider = FakeProvider([copy.deepcopy(dropped)])
        assert fit_story_dialogue(provider, dropped, self.MASTER, 60, 60) == dropped

    def test_failed_repair_call_keeps_the_story(self):
        dropped = copy.deepcopy(self.HEALTHY)
        dropped["scenes"][1]["dialogue"] = []
        provider = FakeProvider([RuntimeError("provider down")])
        assert fit_story_dialogue(provider, dropped, self.MASTER, 60, 60) == dropped
        provider = FakeProvider(["not json at all"])
        assert fit_story_dialogue(provider, dropped, self.MASTER, 60, 60) == dropped

    def test_build_story_runs_the_repair_when_pass2_drops_the_lines(self, monkeypatch):
        lines = [
            {"speaker": "Dawa Farosh", "line": URDU_ASK, "delivery": "hopeful"},
            {"speaker": "Dawa Farosh", "line": URDU_ANSWER, "delivery": "laughing"},
        ]
        provider = FakeProvider([
            {"title": "T", "style": "s", "master_script": self.MASTER},
            {"title": "", "style": "", "scenes": [
                {"scene_id": 0, "narration": "n", "scene_duration": 60}]},   # dialogue lost
            {"scenes": [{"scene_id": 0, "narration": "", "scene_duration": 60, "dialogue": lines}]},
        ])
        monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

        story = json.loads(build_story("a night taxi", director_name="movie/horror", target_length=60))

        assert len(provider.prompts) == 3
        assert story["scenes"][0]["dialogue"] == lines
        assert story["master_script"] == self.MASTER

    def test_build_story_fits_dialogue_against_the_final_durations(self, monkeypatch):
        # Pass 2 asks for 60s but the film is 30s: the fit check must see 30s.
        # 8 lines of 8 words = 30.4s of speech: fits 60s (45s limit), overflows 30s (22.5s)
        long_lines = [{"speaker": "Dawa Farosh", "line": f"This is spoken line number {i} of them"}
                      for i in range(8)]
        provider = FakeProvider([
            {"title": "T", "style": "s", "master_script": self.MASTER},
            {"title": "", "style": "", "scenes": [
                {"scene_id": 0, "narration": "", "scene_duration": 60, "dialogue": long_lines}]},
            {"scenes": [{"scene_id": 0, "narration": "", "scene_duration": 30, "dialogue": [
                {"speaker": "Dawa Farosh", "line": "This is spoken line number one."}]}]},
        ])
        monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

        story = json.loads(build_story("a night taxi", director_name="movie/horror", target_length=30))

        assert len(provider.prompts) == 3
        # 30s * 0.75 = 22.5s of speech fit - not the 45s of the pre-adjustment 60s
        assert "at most 22.5 seconds of speech fit" in provider.prompts[2]
        assert story["scenes"][0]["scene_duration"] == 30
        assert story["scenes"][0]["dialogue"][0]["line"] == "This is spoken line number one."


def test_scene_graph_passes_dialogue_through():
    story = {"scenes": [dict(SCENE, scene_id=0),
                        # a silent scene: nothing to carry, so the key stays out
                        {"scene_id": 1, "location": "l", "action": "a", "emotion": "e",
                         "characters": "c", "dialogue": []}]}
    graph = build_scene_graph(json.dumps(story))
    assert graph[0]["dialogue"] == SCENE["dialogue"]
    assert graph[0]["dialogue"] is not story["scenes"][0]["dialogue"]
    assert "dialogue" not in graph[1]


# ----------------------------------------------------------- shot_planner

class TestCharactersBlockVoices:
    def test_voice_type_and_bound_voice_ride_along(self):
        block = build_characters_block([
            {"name": "Dawa Farosh", "image_prompt": "A tired man", "voice_type": "low husky voice"},
            {"name": "Baker", "image_prompt": "A baker",
             "voice": {"text": "calm, slightly raspy voice"}, "voice_type": "ignored"},
            {"name": "Mute Driver", "image_prompt": "A tall figure"},
        ])
        assert "- Dawa Farosh: A tired man\n  voice: low husky voice" in block
        assert "  voice: calm, slightly raspy voice" in block
        assert "ignored" not in block
        assert "- Mute Driver: A tall figure\n" in block
        assert "VERBATIM" in block

    def test_dialogue_instruction_only_for_scenes_with_lines(self):
        assert build_dialogue_instruction([{"scene_id": 0, "narration": "n"}]) == ""
        assert build_dialogue_instruction([]) == ""
        assert build_dialogue_instruction([SCENE]) == DIALOGUE_INSTRUCTION
        assert "PLACE EVERY LINE" in DIALOGUE_INSTRUCTION


class TestEnforceDialogueCoverage:
    def test_everything_placed_is_a_no_op(self, monkeypatch):
        provider = FakeProvider([])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)
        shots = [_shot(_i2v_prompt(URDU_ASK)), _shot(_i2v_prompt(URDU_ANSWER))]
        assert enforce_dialogue_coverage(shots, [SCENE]) is shots
        assert provider.prompts == []

    def test_scene_without_dialogue_or_non_list_input(self):
        assert enforce_dialogue_coverage([_shot(_i2v_prompt())], [{"scene_id": 0}]) == [_shot(_i2v_prompt())]
        assert enforce_dialogue_coverage({"shots": []}, [SCENE]) == {"shots": []}

    def test_missing_line_is_rewritten_into_the_scene(self, monkeypatch):
        original = [_shot(_i2v_prompt(URDU_ASK), index=1), _shot(_i2v_prompt(), index=2)]
        fixed = [_shot(_i2v_prompt(URDU_ASK), index=1), _shot(_i2v_prompt(URDU_ANSWER), index=2)]
        provider = FakeProvider([fixed])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)

        shots = enforce_dialogue_coverage(original, [SCENE], characters=[
            {"name": "Driver", "voice_type": "low husky voice"},
            {"name": "Passenger", "voice_type": "flat young voice"},
        ])

        assert unplaced_dialogue([SCENE], shots) == {}
        assert len(shots) == 2
        rewrite = provider.prompts[0]
        assert URDU_ANSWER in rewrite          # the line that was missing is named
        assert "- Driver: low husky voice" in rewrite  # voices to copy verbatim
        assert "COMPLETE corrected list of shots" in rewrite

    def test_rewrite_keeps_other_scenes_in_place(self, monkeypatch):
        other = {"scene_id": 1, "narration": "n", "dialogue": [
            {"speaker": "Driver", "line": "We are here."}]}
        original = [
            _shot(_i2v_prompt(URDU_ASK), scene_id=0, index=1),
            _shot(_i2v_prompt(), scene_id=0, index=2),
            _shot(_i2v_prompt("We are here."), scene_id=1, index=3),
        ]
        # the rewrite adds a third shot for scene 0 that speaks the missing line
        fixed = [_shot(_i2v_prompt(URDU_ASK), duration=8), _shot(_i2v_prompt(), duration=6),
                 _shot(_i2v_prompt(URDU_ANSWER), duration=6)]
        provider = FakeProvider([fixed])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)

        shots = enforce_dialogue_coverage(original, [SCENE, other])

        assert [s["scene_id"] for s in shots] == [0, 0, 0, 1]
        assert unplaced_dialogue([SCENE, other], shots) == {}
        assert shots[-1] is original[-1]

    def test_rewrite_that_still_drops_the_line_is_rejected(self, monkeypatch):
        original = [_shot(_i2v_prompt(URDU_ASK)), _shot(_i2v_prompt())]
        provider = FakeProvider([[_shot(_i2v_prompt(URDU_ASK))]])  # still no second line
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)
        assert enforce_dialogue_coverage(original, [SCENE]) == original

    def test_rewrite_keeps_the_scene_planned_length(self, monkeypatch):
        # planned as 8s + 7s; the rewrite returns ONE 8s clip for both lines
        original = [_shot(_i2v_prompt(URDU_ASK), duration=8), _shot(_i2v_prompt(), duration=7)]
        provider = FakeProvider([[_shot(_i2v_prompt(URDU_ASK, URDU_ANSWER), duration=8)]])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)

        shots = enforce_dialogue_coverage(original, [SCENE])

        assert len(shots) == 1
        assert shots[0]["duration"] == 15.0  # the scene is neither shortened nor stretched

    def test_a_rewrite_longer_than_the_scene_is_scaled_back(self, monkeypatch):
        original = [_shot(_i2v_prompt(URDU_ASK), duration=10), _shot(_i2v_prompt(), duration=10)]
        provider = FakeProvider([[_shot(_i2v_prompt(URDU_ASK), duration=12),
                                  _shot(_i2v_prompt(URDU_ANSWER), duration=13)]])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)

        shots = enforce_dialogue_coverage(original, [SCENE])

        assert [s["duration"] for s in shots] == [9.6, 10.4]
        assert sum(s["duration"] for s in shots) == 20.0

    def test_failed_rewrite_keeps_the_original_shots(self, monkeypatch):
        original = [_shot(_i2v_prompt(URDU_ASK)), _shot(_i2v_prompt())]
        for response in (RuntimeError("provider down"), "not json", [{"no_prompt": True}]):
            provider = FakeProvider([response])
            monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)
            assert enforce_dialogue_coverage(original, [SCENE]) == original


class TestPlanShotsBatchDialogue:
    def test_planning_prompt_has_the_rules_and_coverage_is_enforced(self, monkeypatch):
        planned = [_shot(_i2v_prompt(URDU_ASK), duration=10), _shot(_i2v_prompt(), duration=10)]
        fixed = [_shot(_i2v_prompt(URDU_ASK), duration=10), _shot(_i2v_prompt(URDU_ANSWER), duration=10)]
        provider = FakeProvider([planned, fixed])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)

        shots = plan_shots_batch(
            scenes_batch=[SCENE], batch_num=1, total_batches=1,
            max_shots_instruction="Generate 2 shots.", shots_director="default",
            characters_block=build_characters_block([{"name": "Driver", "voice_type": "low husky voice"}]),
            characters=[{"name": "Driver", "voice_type": "low husky voice"}],
        )

        assert "SCRIPTED DIALOGUE" in provider.prompts[0]
        assert "  voice: low husky voice" in provider.prompts[0]
        assert len(provider.prompts) == 2  # plan + one dialogue rewrite
        assert unplaced_dialogue([SCENE], shots) == {}
        assert shots[1]["scene_id"] == 0

    def test_narrated_scene_plans_without_dialogue_rules_or_extra_calls(self, monkeypatch):
        scene = {"scene_id": 0, "location": "taxi", "action": "Rain on the road.", "scene_duration": 10}
        provider = FakeProvider([[_shot(_i2v_prompt())]])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)

        shots = plan_shots_batch(
            scenes_batch=[scene], batch_num=1, total_batches=1,
            max_shots_instruction="Generate 1 shot.", shots_director="default")

        assert len(provider.prompts) == 1
        assert "SCRIPTED DIALOGUE" not in provider.prompts[0]
        assert len(shots) == 1


# ---------------------------------------------------------- r2v_composer

class TestVoiceFallback:
    STORY = {"characters": [
        {"name": "Dawa Farosh (Medicine-Seller)", "voice_type": "low husky voice, slow breathless delivery"},
        {"name": "Baker", "voice": {"text": "calm, slightly raspy voice"}, "voice_type": "ignored"},
        {"name": "Tonga Driver", "voice_type": "None - completely silent"},
    ]}

    def test_voice_type_embedded_when_the_shot_speaks(self):
        shot = {"characters": ["Dawa Farosh"], "video_prompt": "... (S1) says: <d>[Urdu] ...</d>"}
        assert _voice_texts_for_shot(shot, self.STORY) == [
            ("Dawa Farosh (Medicine-Seller)", "low husky voice, slow breathless delivery")]

    def test_silent_shot_keeps_its_prompt_unchanged(self):
        assert _voice_texts_for_shot({"characters": ["Dawa Farosh"], "video_prompt": "fog drifts"}, self.STORY) == []

    def test_bound_voice_text_wins_and_is_always_embedded(self):
        assert _voice_texts_for_shot({"characters": ["Baker"]}, self.STORY) == \
            [("Baker", "calm, slightly raspy voice")]

    def test_character_without_a_voice(self):
        assert _voice_texts_for_shot({"characters": ["Nobody"]}, {"characters": [{"name": "Nobody"}]}) == []


# ------------------------------------------- parse / retry / cap regressions

class TestUnparseableResponseRetries:
    """An unparseable batch response used to escape as an UnboundLocalError
    instead of ValueError - skipping the planner's one retry and silently
    dropping the batch's scenes from the film."""

    def test_unparseable_json_raises_value_error(self):
        from core.shot_planner import extract_and_repair_json
        with pytest.raises(ValueError):
            extract_and_repair_json('[{"scene_id": 0, "video_prompt": "unterminated}]')
        with pytest.raises(ValueError):
            extract_and_repair_json("no array here")

    def test_batch_is_retried_after_an_unparseable_response(self, monkeypatch):
        provider = FakeProvider([
            '[{"scene_id": 0, "video_prompt": "unterminated}]',
            [_shot(_i2v_prompt())],
        ])
        monkeypatch.setattr(shot_planner, "get_provider", lambda: provider)
        shots = plan_shots_batch(
            scenes_batch=[{"scene_id": 0, "location": "taxi", "action": "Rain.", "scene_duration": 10}],
            batch_num=1, total_batches=1,
            max_shots_instruction="Generate 1 shot.", shots_director="default")
        assert len(provider.prompts) == 2
        assert len(shots) == 1


class TestVoiceEmbeddingCap:
    SIX_SECTIONS = (
        "subject_definitions:\n<Subject 1>: a baker, in <Picture 1>.\n\n"
        "summary:\n[reference generation] {pad}\n\n"
        "retention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - identity from <Picture 1>.\n\n"
        "detailed_description:\nThe target video is live-action.\n"
        "[Shot 1] The baker (S1) says: <d>[English] Morning.</d>\n\n"
        "overall_soundscape: A quiet street.\n\n"
        "non_diegetic_music: N/A"
    )
    STORY = {"characters": [{"name": "Baker", "voice_type": "calm, slightly raspy voice"}]}

    def _shot(self, length):
        base = self.SIX_SECTIONS.format(pad="")
        return {"characters": ["Baker"],
                "video_prompt": self.SIX_SECTIONS.format(pad="x" * (length - len(base)))}

    def test_voice_note_added_when_it_fits(self):
        composed, problems = compose_video_prompt(
            self._shot(6000), self.STORY, attached_picture_count=1, r2v_six_sections=True)
        assert "The voice of Baker: calm, slightly raspy voice." in composed
        assert problems == []

    def test_voice_note_is_skipped_rather_than_breaking_the_cap(self):
        shot = self._shot(R2V_PROMPT_CHAR_LIMIT - 10)
        composed, problems = compose_video_prompt(
            shot, self.STORY, attached_picture_count=1, r2v_six_sections=True)
        assert "The voice of Baker" not in composed
        assert len(composed) <= R2V_PROMPT_CHAR_LIMIT
        assert problems == []

    def test_a_prompt_already_over_the_cap_still_gets_its_voice(self):
        composed, problems = compose_video_prompt(
            self._shot(R2V_PROMPT_CHAR_LIMIT + 50), self.STORY,
            attached_picture_count=1, r2v_six_sections=True)
        assert "The voice of Baker: calm, slightly raspy voice." in composed
        assert any("exceeds" in p for p in problems)


# ------------------------------------------------------- dialogue language

class TestDetectDialogueLanguage:
    def test_detects_the_language_an_idea_names(self):
        assert detect_dialogue_language(
            "Dialogs in Urdu Lanaguge. Studio Ghibli Visual Style.") == ("Urdu", False)
        assert detect_dialogue_language(
            "Dialogs in Urdu language. Do not use English in dialogue.") == ("Urdu", False)
        assert detect_dialogue_language("dialogue should be in Mexican Spanish") == ("Spanish", False)
        assert detect_dialogue_language("Urdu-language dialogue throughout") == ("Urdu", False)
        assert detect_dialogue_language("narrated in English, dialogues in punjabi") == ("Punjabi", False)

    def test_explicit_transliteration_is_respected(self):
        assert detect_dialogue_language("Dialogs in Roman Urdu") == ("Urdu", True)
        assert detect_dialogue_language("Roman Urdu dialogue, please") == ("Urdu", True)

    def test_no_language_or_english_leaves_the_choice_to_the_model(self):
        assert detect_dialogue_language("A baker opens his shop at dawn") == (None, False)
        assert detect_dialogue_language("Do not use English in dialogue") == (None, False)
        assert detect_dialogue_language("conversations in the old town") == (None, False)
        assert detect_dialogue_language("") == (None, False)
        assert detect_dialogue_language(None) == (None, False)

    def test_directive_text(self):
        assert dialogue_language_directive(None) == \
            "the language the IDEA names for the dialogue - English if it names none"
        assert dialogue_language_directive("Urdu") == "Urdu"
        assert dialogue_language_directive("Urdu", True) == \
            "Urdu written in Latin transliteration (as the IDEA asks)"


class TestDialogueInWrongScript:
    ENGLISH = {"scenes": [{"scene_id": 0, "dialogue": [{"speaker": "Rahim", "line": URDU_ASK}]}]}
    URDU = {"scenes": [{"scene_id": 0, "dialogue": [{"speaker": "Rahim", "line": URDU_SCRIPT_ASK}]}]}

    def test_requested_non_latin_language_answered_in_ascii(self):
        assert dialogue_in_wrong_script("Urdu", self.ENGLISH["scenes"]) is True

    def test_native_script_present(self):
        assert dialogue_in_wrong_script("Urdu", self.URDU["scenes"]) is False

    def test_cannot_be_checked_for_latin_script_languages_or_without_lines(self):
        assert dialogue_in_wrong_script("Spanish", self.ENGLISH["scenes"]) is False
        assert dialogue_in_wrong_script(None, self.ENGLISH["scenes"]) is False
        assert dialogue_in_wrong_script("Urdu", [{"dialogue": []}]) is False


class TestEnsureDialogueLanguage:
    STORY = {"title": "T", "scenes": [
        {"scene_id": 0, "narration": "n", "scene_duration": 20, "action": "a",
         "dialogue": [{"speaker": "Rahim Bakhsh", "line": URDU_ASK, "delivery": "hopeful"}]},
        {"scene_id": 1, "narration": "", "scene_duration": 20, "action": "b",
         "dialogue": [{"speaker": "Rahim Bakhsh", "line": URDU_ASK, "delivery": "flat"},
                      {"speaker": "Shahzad", "line": "Open it yourself, Uncle.", "delivery": "cocky"}]},
    ]}
    TRANSLATED = {"scenes": [
        {"scene_id": 0, "dialogue": [{"speaker": "RAHIM BAKHSH", "line": URDU_SCRIPT_ASK}]},
        {"scene_id": 1, "dialogue": [
            {"speaker": "Rahim Bakhsh", "line": URDU_SCRIPT_ASK},
            {"speaker": "Shahzad", "line": "خود کھول لو چاچا۔"}]},
    ]}

    def test_nothing_to_do_when_the_script_is_right_or_checkable(self):
        provider = FakeProvider([])
        assert ensure_dialogue_language(provider, {"scenes": [{"dialogue": []}]}, "Urdu") == \
            {"scenes": [{"dialogue": []}]}
        assert ensure_dialogue_language(provider, copy.deepcopy(self.STORY), "Spanish") == self.STORY
        assert provider.prompts == []

    def test_lines_are_translated_one_to_one_and_nothing_else_changes(self):
        provider = FakeProvider([self.TRANSLATED])
        story = ensure_dialogue_language(provider, copy.deepcopy(self.STORY), "Urdu")

        assert "written in Urdu" in provider.prompts[0]
        assert [e["line"] for e in story["scenes"][0]["dialogue"]] == [URDU_SCRIPT_ASK]
        assert [e["line"] for e in story["scenes"][1]["dialogue"]] == \
            [URDU_SCRIPT_ASK, "خود کھول لو چاچا۔"]
        assert story["scenes"][1]["dialogue"][0]["speaker"] == "Rahim Bakhsh"  # as scripted
        # the translation only supplies words: speaker and delivery stay as scripted
        assert story["scenes"][0]["dialogue"] == [
            {"speaker": "Rahim Bakhsh", "line": URDU_SCRIPT_ASK, "delivery": "hopeful"}]
        # every other field is the original scene's
        assert {k: v for k, v in story["scenes"][0].items() if k != "dialogue"} == \
            {k: v for k, v in self.STORY["scenes"][0].items() if k != "dialogue"}
        assert story["title"] == "T"

    def test_a_scene_whose_lines_no_longer_map_onto_its_speakers_keeps_its_own(self):
        swapped = copy.deepcopy(self.TRANSLATED)
        swapped["scenes"][1]["dialogue"].reverse()  # Shahzad now speaks Rahim's line
        provider = FakeProvider([swapped])
        story = ensure_dialogue_language(provider, copy.deepcopy(self.STORY), "Urdu")
        assert story["scenes"][1] == self.STORY["scenes"][1]
        assert story["scenes"][0]["dialogue"][0]["line"] == URDU_SCRIPT_ASK

    def test_failed_or_unusable_translation_keeps_the_lines(self):
        for response in (RuntimeError("provider down"), "not json", {"scenes": []},
                         {"scenes": [{"dialogue": [{"speaker": "R", "line": URDU_ASK}]}] * 2}):
            provider = FakeProvider([response])
            assert ensure_dialogue_language(provider, copy.deepcopy(self.STORY), "Urdu") == self.STORY

    @staticmethod
    def _lines(speaker, lines):
        return [{"speaker": speaker, "line": line} for line in lines]

    def test_build_story_tells_the_screenplay_prompts_the_language(self, monkeypatch):
        provider = FakeProvider([
            {"title": "T", "style": "s",
             "master_script": 'RAHIM (hopeful): "' + URDU_SCRIPT_LINES[0] + '"'},
            {"title": "", "style": "", "scenes": [
                {"scene_id": 0, "narration": "", "scene_duration": 60,
                 "dialogue": self._lines("Rahim", URDU_SCRIPT_LINES)}]},
        ])
        monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

        story = json.loads(build_story(
            "A locked classroom. Dialogs in Urdu language. Do not use English in dialogue.",
            director_name="movie/horror", target_length=60))

        assert len(provider.prompts) == 2  # written in Urdu from the start: no extra pass
        assert "This film's dialogue language is Urdu" in provider.prompts[0]
        assert "this film's dialogue language is Urdu" in provider.prompts[1]
        assert "{DIALOGUE_LANGUAGE}" not in provider.prompts[0] + provider.prompts[1]
        assert [e["line"] for e in story["scenes"][0]["dialogue"]] == URDU_SCRIPT_LINES

    def test_build_story_translates_when_the_model_answers_in_english(self, monkeypatch):
        provider = FakeProvider([
            {"title": "T", "style": "s", "master_script": f'RAHIM (hopeful): "{URDU_ASK}"'},
            {"title": "", "style": "", "scenes": [
                {"scene_id": 0, "narration": "", "scene_duration": 60,
                 "dialogue": self._lines("Rahim", TRANSLITRATED_LINES)}]},
            {"scenes": [{"scene_id": 0, "dialogue": self._lines("Rahim", URDU_SCRIPT_LINES)}]},
        ])
        monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

        story = json.loads(build_story(
            "A locked classroom. Dialogs in Urdu language.", director_name="movie/horror", target_length=60))

        assert len(provider.prompts) == 3
        assert "must be written in Urdu" in provider.prompts[2]
        assert [e["line"] for e in story["scenes"][0]["dialogue"]] == URDU_SCRIPT_LINES
        assert story["scenes"][0]["narration"] == ""


# ---------------------------------------------------------- clip pacing

class TestRebalanceSpeechDurations:
    THREE_LINES = ("Listen to me carefully brother please", "The road is closed tonight for all",
                   "Turn the cart around now and go")  # 20 words in 3 lines -> 9.8s -> needs 13.1s

    def test_speaking_seconds(self):
        assert shot_speaking_seconds({"video_prompt": _i2v_prompt()}) == 0.0
        two_lines = _i2v_prompt("One two three four five.", "Six seven eight nine ten.")
        assert shot_speaking_seconds({"video_prompt": two_lines}) == pytest.approx(5.2)

    def test_a_crammed_clip_takes_time_from_the_silent_one(self):
        shots = [_shot(_i2v_prompt(*self.THREE_LINES), duration=8, index=1),
                 _shot(_i2v_prompt(), duration=10, index=2)]
        assert rebalance_speech_durations(shots) == 2
        assert shots[0]["duration"] == 13.1
        assert shots[1]["duration"] == 4.9
        assert sum(s["duration"] for s in shots) == 18.0

    def test_nothing_changes_when_the_lines_already_fit(self):
        shots = [_shot(_i2v_prompt(URDU_ASK, URDU_ANSWER), duration=10), _shot(_i2v_prompt(), duration=5)]
        assert rebalance_speech_durations(shots) == 0
        assert [s["duration"] for s in shots] == [10, 5]

    def test_nothing_changes_without_dialogue_or_with_bad_input(self):
        shots = [_shot(_i2v_prompt(), duration=4), _shot(_i2v_prompt(), duration=12)]
        assert rebalance_speech_durations(shots) == 0
        assert rebalance_speech_durations({"not": "a list"}) == 0

    def test_a_silent_clip_keeps_its_last_sub_shot_cut(self):
        with_cut = _i2v_prompt().replace(
            "\n\noverall_soundscape:",
            " [Shot 2] At 00:06.000, the camera cuts to the gate.\n\noverall_soundscape:", 1)
        shots = [_shot(_i2v_prompt(*self.THREE_LINES), duration=8), _shot(with_cut, duration=10)]
        rebalance_speech_durations(shots)
        assert shots[1]["duration"] == pytest.approx(6.7)  # cut at 6.0s + 0.7s margin
        assert shots[0]["duration"] == pytest.approx(11.3)
        assert validate_video_prompt(with_cut, shots[1]["duration"]) == []

    def test_the_clip_cap_is_respected(self):
        shots = [_shot(_i2v_prompt(*self.THREE_LINES), duration=8), _shot(_i2v_prompt(), duration=10)]
        rebalance_speech_durations(shots, max_shot_duration=10)
        assert [s["duration"] for s in shots] == [10, 8]

    def test_scenes_are_rebalanced_independently(self):
        shots = [_shot(_i2v_prompt(*self.THREE_LINES), scene_id=0, duration=8),
                 _shot(_i2v_prompt(), scene_id=1, duration=10)]
        rebalance_speech_durations(shots)
        assert [s["duration"] for s in shots] == [8, 10]  # no silent clip in scene 0 to take from

    def test_a_speaking_clip_with_room_to_spare_gives_time(self):
        # every clip speaks and the scene is packed: spare time moves from the
        # clip that has it to the one that needs it
        shots = [_shot(_i2v_prompt(" ".join(["word"] * 10)), duration=7),                 # needs 6.1s
                 _shot(_i2v_prompt(" ".join(["word"] * 6), " ".join(["word"] * 8),
                                   " ".join(["word"] * 8)), duration=9)]                 # needs 14.1s
        assert rebalance_speech_durations(shots) == 2
        assert shots[0]["duration"] == 6.1
        assert shots[1]["duration"] == 9.9
        assert sum(s["duration"] for s in shots) == 16.0
