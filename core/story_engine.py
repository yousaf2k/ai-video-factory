"""
Story Engine - Generate cinematic stories from ideas using LLM directors.
"""
from core.llm_engine import get_provider
from core.director_loader import load_director_prompt, get_director_loader
from core.logger_config import setup_director_logger
from core.dialogue import (DIALOGUE_PAUSE_SECONDS, SPEECH_FIT_SHARE, SPEECH_WORDS_PER_SECOND,
                           dialogue_word_count, format_dialogue, missing_dialogue_lines,
                           normalize_scene_dialogue, scene_dialogue, scene_speaking_seconds,
                           scripted_lines)
from web_ui.backend.models.story import ProjectType
import config
import json
import re
import uuid


# Get logger for story engine operations
logger = setup_director_logger(__name__)


# Common single-token LLM slips, repaired only as a last-ditch fallback when
# strict parsing failed and the repaired text is itself re-validated by a
# successful json.loads before being returned:
# - a key missing its opening quote:  `,\n      emotion": "..."`  (Gemini has
#   been observed truncating exactly the first quote of repeated keys)
# - a trailing comma before a closing brace/bracket
_KEY_MISSING_QUOTE_RE = re.compile(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*":)')
_TRAILING_COMMA_RE = re.compile(r',\s*([}\]])')


def parse_llm_json(text):
    """
    Parse JSON from an LLM response, tolerating markdown code fences
    and surrounding prose.

    Even when asked for response_format="application/json", providers
    sometimes wrap the payload in ```json fences or prefix it with
    prose, which plain json.loads() rejects. Strip the fences first,
    then fall back to the outermost {...} or [...] span in the text,
    then to repairing the common single-token slips above.

    Raises json.JSONDecodeError if no JSON value can be recovered.
    """
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        last_err = None
        for open_ch, close_ch in (("{", "}"), ("[", "]")):
            start = cleaned.find(open_ch)
            end = cleaned.rfind(close_ch)
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError as e:
                    last_err = e
        key_repaired = _KEY_MISSING_QUOTE_RE.sub(r'\1"\2\3', cleaned)
        both_repaired = _TRAILING_COMMA_RE.sub(r'\1', key_repaired)
        for repaired in (key_repaired, both_repaired):
            if repaired == cleaned:
                continue
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                continue
        if last_err:
            raise last_err
        raise json.JSONDecodeError("No JSON found in LLM response", cleaned, 0)


def parse_story_json_with_retry(provider, text):
    """Parse a story LLM response, with one LLM repair pass on failure.

    Raises ValueError when the response cannot be recovered — callers must
    never fall back to the raw invalid text, which would propagate into
    story.json and break every downstream json.loads.
    """
    try:
        return parse_llm_json(text)
    except json.JSONDecodeError as first_err:
        logger.warning(f"Story JSON invalid ({first_err}); requesting an LLM repair pass")
        repair_prompt = (
            "The following text was meant to be a single valid JSON object but "
            f"contains syntax errors ({first_err}). Return ONLY the corrected JSON "
            "object — no markdown fences, no commentary, and no changes to the "
            f"content:\n\n{text}"
        )
        try:
            return parse_llm_json(
                provider.ask(repair_prompt, response_format="application/json"))
        except json.JSONDecodeError as second_err:
            raise ValueError(
                f"Story JSON still invalid after repair pass ({second_err}); "
                f"response snippet: {str(text)[:300]!r}") from second_err


def normalize_scene_ids(story):
    """Re-index story scenes to their array position (0-based), in place.

    The LLM sometimes returns 1-based scene_ids. Every downstream consumer
    keys on 0-based positions — plan_shots injects 0-based indices into its
    batches, background sheets are named/stamped per 0-based scene index, and
    the r2v reference sync matches shots to backgrounds by scene_id — so a
    story saved with the LLM's own numbering silently mismatches: backgrounds
    attach to the wrong scene, or to none at all.
    """
    if isinstance(story, dict):
        for i, scene in enumerate(story.get('scenes') or []):
            if isinstance(scene, dict):
                scene['scene_id'] = i
    return story


def validate_and_adjust_scene_durations(story, target_length, tolerance=0.15):
    """
    Validate scene durations sum to approximately target_length.
    Auto-correct if outside tolerance.

    Args:
        story: Story dict with 'scenes' list, or list of scenes directly
        target_length: Target total duration in seconds
        tolerance: Acceptable deviation as fraction (e.g., 0.15 = 15%)

    Returns:
        Tuple: (is_valid, actual_total, difference, adjusted_story)
    """
    # Handle both dict and list inputs
    if isinstance(story, list):
        scenes = story
        story_is_dict = False
    else:
        scenes = story.get('scenes', [])
        story_is_dict = True

    if not scenes:
        return True, 0, 0, story

    # Check if scenes have scene_duration field
    has_durations = any('scene_duration' in s for s in scenes)
    if not has_durations:
        return True, 0, 0, story

    # Calculate actual total duration
    actual_total = sum(s.get('scene_duration', 0) for s in scenes)
    difference = actual_total - target_length
    deviation_ratio = abs(difference) / target_length if target_length > 0 else 0

    # Check if within tolerance
    if deviation_ratio <= tolerance:
        logger.info(f"Scene durations validation passed: {actual_total}s (target: {target_length}s, deviation: {deviation_ratio*100:.1f}%)")
        return True, actual_total, difference, story

    # Outside tolerance - apply proportional correction
    logger.warning(f"Scene duration mismatch: {actual_total}s vs target {target_length}s (deviation: {deviation_ratio*100:.1f}%)")
    print(f"[WARN] Scene duration mismatch: {actual_total}s vs target {target_length}s (deviation: {deviation_ratio*100:.1f}%)")

    # Calculate adjustment factor
    adjustment_factor = target_length / actual_total if actual_total > 0 else 1.0

    # Adjust each scene's duration proportionally and ensure scene_id
    adjusted_scenes = []
    for i, scene in enumerate(scenes):
        adjusted_scene = scene.copy()
        # Ensure scene_id exists
        if 'scene_id' not in adjusted_scene:
            adjusted_scene['scene_id'] = i
            
        if 'scene_duration' in scene:
            original_duration = scene['scene_duration']
            adjusted_duration = max(config.MIN_SCENE_LENGTH, int(original_duration * adjustment_factor))
            adjusted_scene['scene_duration'] = adjusted_duration
            logger.debug(f"Adjusted scene duration: {original_duration}s -> {adjusted_duration}s")
        adjusted_scenes.append(adjusted_scene)

    # Return in same format as input
    if story_is_dict:
        adjusted_story = story.copy()
        adjusted_story['scenes'] = adjusted_scenes
    else:
        adjusted_story = adjusted_scenes

    new_total = sum(s.get('scene_duration', 0) for s in adjusted_scenes)
    logger.info(f"Auto-corrected scene durations: {actual_total}s -> {new_total}s")
    print(f"[INFO] Auto-corrected scene durations: {actual_total}s -> {new_total}s")

    return False, actual_total, difference, adjusted_story


def resolve_master_script_director(director_name: str = "default") -> str:
    """
    Pick the Pass-1 master script director for a story director.

    A story family (e.g. ``movie``, ``documentary``) ships its own Pass-1
    prompt as ``<family>/_base/master_script.md``; families without one
    (and bare director names) fall back to the documentary master script.

    Args:
        director_name: Name of the Pass-2 story director (may contain a
            family prefix, e.g. "movie/horror")

    Returns:
        Director id to load for the master script pass
    """
    if "/" in director_name:
        family_master = f"{director_name.split('/', 1)[0]}/_base/master_script"
        try:
            get_director_loader().load_prompt_raw("story", family_master)
            return family_master
        except (FileNotFoundError, ValueError):
            pass
    return "documentary/_base/master_script"


def is_dialogue_story(director_name: str) -> bool:
    """True for story families whose scenes carry a dialogue layer.

    Only the ``movie`` family writes a screenplay: its lines are spoken by the
    characters (lip-synced by the video model). Documentaries and the other
    narrated families keep their narration-only scene shape.
    """
    return str(director_name or "").strip().split("/", 1)[0].lower() == "movie"


def speech_word_budgets(target_length):
    """(dialogue_words, narration_words) planned for a film of `target_length` seconds.

    Both derive from the running time at the spoken-word rate, in the shares
    configured by MOVIE_DIALOGUE_SHARE / MOVIE_NARRATION_SHARE.
    """
    words = float(target_length) * SPEECH_WORDS_PER_SECOND
    return (round(words * config.MOVIE_DIALOGUE_SHARE),
            round(words * config.MOVIE_NARRATION_SHARE))


# Languages an idea may name for its dialogue ("Dialogs in Urdu"). A name that
# is not listed is ignored rather than guessed - forcing a wrong language is
# worse than leaving the choice to the model.
_DIALOGUE_LANGUAGES = {
    "amharic", "arabic", "armenian", "azerbaijani", "balochi", "bengali", "bulgarian",
    "cantonese", "chinese", "croatian", "czech", "dari", "danish", "dutch", "english",
    "farsi", "filipino", "finnish", "french", "georgian", "german", "greek", "gujarati",
    "hausa", "hebrew", "hindi", "hungarian", "indonesian", "italian", "japanese",
    "kannada", "kashmiri", "kazakh", "korean", "kurdish", "malay", "malayalam",
    "mandarin", "marathi", "nepali", "norwegian", "pashto", "persian", "polish",
    "portuguese", "punjabi", "romanian", "russian", "serbian", "sindhi", "sinhala",
    "slovak", "somali", "spanish", "swahili", "swedish", "tagalog", "tamil", "telugu",
    "thai", "turkish", "turkmen", "ukrainian", "urdu", "uzbek", "vietnamese", "yiddish",
}
# Of those, the ones normally written in a non-Latin script. For them the
# dialogue's script can be checked without a language detector.
_NON_LATIN_SCRIPT_LANGUAGES = {
    "amharic", "arabic", "armenian", "balochi", "bengali", "cantonese", "chinese",
    "dari", "farsi", "georgian", "greek", "gujarati", "hebrew", "hindi", "japanese",
    "kannada", "kashmiri", "kazakh", "korean", "kurdish", "malayalam", "mandarin",
    "marathi", "nepali", "pashto", "persian", "punjabi", "russian", "serbian",
    "sindhi", "sinhala", "tamil", "telugu", "thai", "ukrainian", "urdu", "yiddish",
}
# "Roman Urdu" / "Latin Hindi": the idea asks for transliteration, not the native script
_TRANSLITERATION_CUES = {"roman", "latin"}

_LANG_NAME = r"([A-Za-z]+(?:[ -][A-Za-z]+)?)"
# "Roman Urdu dialogue" / "dialogue in Latin Hindi": the native script is
# explicitly NOT wanted, so the cue is looked for before anything else
_TRANSLITERATION_RES = (
    re.compile(r"\b(roman|latin)[ -]([A-Za-z]+)\b[^.\n;]{0,30}\bdialog", re.IGNORECASE),
    re.compile(r"\bdialog(?:ue)?s?\b[^.\n;]{0,30}\b(roman|latin)[ -]([A-Za-z]+)\b", re.IGNORECASE),
)
_DIALOGUE_LANGUAGE_RES = (
    # "Dialogs in Urdu", "dialogue should be in Spanish", "lines in Hindi"
    re.compile(r"\b(?:dialog(?:ue)?s?|lines?|conversations?|speech|spoken\s+words?)\b"
               r"[^.\n;]{0,40}?\b(?:in|using)\s+" + _LANG_NAME, re.IGNORECASE),
    # "Urdu dialogue", "Urdu-language dialogue"
    re.compile(r"\b([A-Za-z]+)\b(?:[ -](?:language|lang)\s*)?dialog(?:ue)?s?\b", re.IGNORECASE),
)


def detect_dialogue_language(idea):
    """(language, transliterated) that the IDEA names for its dialogue, e.g.
    ("Urdu", False); (None, False) when it names none.

    Only a listed language name counts, so the prose around it ("Dialogs in
    Urdu Lanaguge", "do not use English in dialogue") cannot produce a wrong
    language - "English" is the default anyway.
    """
    idea = idea or ""
    for pattern in _TRANSLITERATION_RES:
        for match in pattern.finditer(idea):
            if match.group(2).lower() in _DIALOGUE_LANGUAGES:
                return match.group(2).title(), True
    for pattern in _DIALOGUE_LANGUAGE_RES:
        for match in pattern.finditer(idea):
            words = re.sub(r"\s+", " ", match.group(1).lower()).split(" ")
            if " ".join(words) in _DIALOGUE_LANGUAGES:
                return " ".join(words).title(), False
            if (len(words) == 2 and words[0] in _TRANSLITERATION_CUES
                    and words[1] in _DIALOGUE_LANGUAGES):
                return words[1].title(), True
            for word in words:
                if word in _DIALOGUE_LANGUAGES:
                    return word.title(), False
    return None, False


def dialogue_language_directive(language, transliterated=False):
    """Text the {DIALOGUE_LANGUAGE} placeholder expands to."""
    if not language:
        return "the language the IDEA names for the dialogue - English if it names none"
    if transliterated:
        return f"{language} written in Latin transliteration (as the IDEA asks)"
    return language


def dialogue_in_wrong_script(language, scenes):
    """True when a non-Latin-script dialogue language was requested but not a
    single dialogue line is written in that script - the lines came back in
    English, or in transliteration nobody asked for."""
    if not language or language.lower() not in _NON_LATIN_SCRIPT_LANGUAGES:
        return False
    lines = [e["line"] for s in scenes or [] for e in scene_dialogue(s)]
    if not lines:
        return False
    return not any(ch.isalpha() and ord(ch) > 127 for line in lines for ch in line)


def fill_story_placeholders(prompt, target_length, dialogue_language=None, transliterated=False):
    """Substitute the placeholders a story director prompt carries.

    {VIDEO_LENGTH} and {MASTER_WORD_COUNT} are used by every family;
    {DIALOGUE_WORD_COUNT}, {NARRATION_WORD_COUNT} and {DIALOGUE_LANGUAGE} by
    the movie screenplay. Only placeholders actually present are replaced, so
    narrated directors are unaffected by the dialogue budget. Length
    placeholders need a target length; the language directive does not.
    """
    prompt = prompt.replace("{DIALOGUE_LANGUAGE}", dialogue_language_directive(
        dialogue_language, transliterated))
    if not target_length:
        return prompt
    dialogue_words, narration_words = speech_word_budgets(target_length)
    replacements = {
        "{VIDEO_LENGTH}": str(int(target_length)),
        "{MASTER_WORD_COUNT}": str(int(target_length * SPEECH_WORDS_PER_SECOND)),
        "{DIALOGUE_WORD_COUNT}": str(dialogue_words),
        "{NARRATION_WORD_COUNT}": str(narration_words),
    }
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt


# A screenplay has "too little" dialogue when the scenes carry far fewer lines
# than the screenplay (or than the film has time for), or less than this share
# of the dialogue word budget. Clear under-delivery gets one repair pass; small
# deviations do not (word counts are only ever approximate).
_DIALOGUE_LINE_LOSS_RATIO = 0.34
_DIALOGUE_WORD_FLOOR_RATIO = 0.5
# Films too short for a meaningful word budget (a 40-word target = 40s)
_MIN_DIALOGUE_BUDGET_WORDS = 40

# Seconds a scene's speech may run past its limit before the scene counts as
# over-full: about a line's worth of slack, so a marginal overflow does not
# cost a repair pass.
SCENE_SPEECH_SLACK_SECONDS = 1.6
# Screen time one dialogue line needs on average (about ten spoken words plus
# a breath): the countable budget both screenplay passes are given.
SECONDS_PER_DIALOGUE_LINE = 7
MAX_DIALOGUE_LINE_WORDS = 12


def _scene_seconds(scene):
    try:
        return float(scene.get("scene_duration") or 0)
    except (TypeError, ValueError):
        return 0.0


def scene_speech_limit(scene):
    """Seconds of speech a scene can hold and still leave room to act."""
    return _scene_seconds(scene) * SPEECH_FIT_SHARE


def scene_line_capacity(scene):
    """Dialogue lines a scene has time for (0 when it has no duration)."""
    seconds = _scene_seconds(scene)
    return max(1, int(seconds // SECONDS_PER_DIALOGUE_LINE)) if seconds > 0 else 0


def overfull_scenes(scenes):
    """[(index, scene, speech_seconds, limit_seconds)] for scenes whose speech
    cannot fit their duration (beyond a line's worth of slack)."""
    out = []
    for i, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        limit = scene_speech_limit(scene)
        speech = scene_speaking_seconds(scene)
        if limit > 0 and speech > limit + SCENE_SPEECH_SLACK_SECONDS:
            out.append((i, scene, speech, limit))
    return out


def dialogue_gaps(master_script, scenes, dialogue_target):
    """How far a screenplay's dialogue is from what the scenes should carry.

    Returns (missing_lines, dialogue_words, too_little). `too_little` is True
    when the scenes carry far fewer dialogue lines than the screenplay — or
    than the film has time for — or hold less than half the dialogue word
    budget. Line loss is judged by COUNT, not by verbatim text: the scene pass
    may translate or reword a line, and that is not a loss. `missing_lines`
    (screenplay lines no scene speaks verbatim) are reported for the repair
    prompt only.
    """
    scenes = scenes or []
    script_lines = scripted_lines(master_script)
    entries = sum(len(scene_dialogue(s)) for s in scenes)
    # A scene can only hold so many lines, so a screenplay that overshot is
    # rightly trimmed by the scene pass down to what the film has time for
    capacity = sum(scene_line_capacity(s) for s in scenes if isinstance(s, dict))
    expected = min(len(script_lines), capacity)
    lines_lost = expected >= 3 and entries <= expected * (1 - _DIALOGUE_LINE_LOSS_RATIO)
    words = dialogue_word_count(scenes)
    under_budget = (dialogue_target >= _MIN_DIALOGUE_BUDGET_WORDS
                    and words < dialogue_target * _DIALOGUE_WORD_FLOOR_RATIO)
    too_little = bool(lines_lost or under_budget)
    # Named for the repair prompt only; with a translation or rewording these
    # are the lines to bring back in the film's dialogue language
    missing = missing_dialogue_lines(script_lines, scenes) if too_little else []
    return missing, words, too_little


def _merge_repaired_scenes(scenes, repaired_scenes):
    """Take a repaired scene only where it improves on the original.

    An over-full scene is replaced by a version with less speech (and still at
    least one line when it had one). A scene with room to spare is replaced by
    one with more dialogue that still fits. Everything else keeps the original.

    Returns (scenes, excess_before, excess_after, fit_before, fit_after):
    `excess` is the seconds of speech the scenes hold beyond their limits, and
    `fit` is (dialogue words, lines) held by the scenes that were NOT over-full
    — the dialogue a repair may add to but must never shrink.
    """
    merged, excess, fit = [], [0.0, 0.0], [[0, 0], [0, 0]]
    for original, repaired in zip(scenes, repaired_scenes):
        original_speech = scene_speaking_seconds(original)
        limit = scene_speech_limit(original)
        overfull = limit > 0 and original_speech > limit + SCENE_SPEECH_SLACK_SECONDS
        excess[0] += max(0.0, original_speech - limit)
        keep = original
        if isinstance(repaired, dict):
            # timing is the film's, not the repair's
            repaired = {**repaired, "scene_duration": original.get("scene_duration")}
            repaired_speech = scene_speaking_seconds(repaired)
            if overfull:
                keeps_a_line = not scene_dialogue(original) or bool(scene_dialogue(repaired))
                if repaired_speech < original_speech and keeps_a_line:
                    keep = repaired
            elif repaired_speech > original_speech and repaired_speech <= limit:
                keep = repaired
        if not overfull:
            fit[0][0] += dialogue_word_count([original])
            fit[0][1] += len(scene_dialogue(original))
            fit[1][0] += dialogue_word_count([keep])
            fit[1][1] += len(scene_dialogue(keep))
        merged.append(keep)
        excess[1] += max(0.0, scene_speaking_seconds(keep) - limit)
    return merged, excess[0], excess[1], tuple(fit[0]), tuple(fit[1])


def fit_story_dialogue(provider, story, master_script, target_length, dialogue_target):
    """One repair pass when a film's dialogue does not fit the film.

    Pass 2 breaks the master script into scenes and is where dialogue used to
    vanish. Two failures are checked deterministically, because models cannot
    count words reliably:
    - too little: far fewer dialogue lines than the screenplay (or than the
      film has time for), or less than half the dialogue word budget;
    - too much: a scene holding more spoken words than its duration can play.
    Either triggers one LLM pass that names the problems scene by scene.

    Returns the (possibly replaced) story. Scenes are merged one by one (see
    `_merge_repaired_scenes`), so the result never regresses; on any failure
    the original story is kept.
    """
    scenes = story.get("scenes") or []
    missing, words, too_little = dialogue_gaps(master_script, scenes, dialogue_target)
    overfull = overfull_scenes(scenes)
    if not too_little and not overfull:
        return story

    summary = []
    if too_little:
        summary.append(f"too little dialogue ({len(missing)} screenplay lines unspoken, "
                       f"{words}/{dialogue_target} dialogue words)")
    if overfull:
        summary.append("speech overflows " + ", ".join(
            f"scene {scene.get('scene_id')} ({speech:.0f}s of speech for {limit:g}s)"
            for _, scene, speech, limit in overfull))
    logger.warning("Screenplay dialogue does not fit the film: " + "; ".join(summary)
                   + "; requesting one repair pass")
    print(f"[WARN] Screenplay dialogue does not fit the film: {'; '.join(summary)}; repairing")

    problems = []
    if too_little:
        problems.append(
            f"- The scenes hold only {words} dialogue words; a {int(target_length)}-second film "
            f"needs about {dialogue_target}. Fill the conversations out so the scenes reach "
            f"about that many.")
        if missing:
            problems.append(
                "- The scenes carry far fewer lines than the screenplay. These screenplay lines "
                "are not spoken in any scene:\n" + format_dialogue(
                    [{"speaker": "SCREENPLAY", "line": line} for line in missing[:30]]))
    for _, scene, speech, limit in overfull:
        lines_that_fit = scene_line_capacity(scene)
        words_that_fit = max(0.0, (limit - DIALOGUE_PAUSE_SECONDS * lines_that_fit)
                             * SPEECH_WORDS_PER_SECOND)
        problems.append(
            f"- Scene {scene.get('scene_id')} ({scene.get('scene_duration')}s) holds "
            f"{len(scene_dialogue(scene))} dialogue lines - about {speech:.0f} seconds of speech - "
            f"but at most {limit:g} seconds of speech fit in that time. Rewrite its dialogue with "
            f"at most {lines_that_fit} lines of at most {MAX_DIALOGUE_LINE_WORDS} words each, "
            f"about {words_that_fit:.0f} words or fewer in total (narration included): keep its "
            f"strongest lines and the turn of the conversation, cut or shorten the rest.")

    current = {k: v for k, v in story.items() if k != "master_script"}
    repair_prompt = f"""DIALOGUE REPAIR — the screenplay of a {int(target_length)}-second film was broken into scenes, but its dialogue does not fit. Return the corrected story JSON.

WHAT WENT WRONG
{chr(10).join(problems)}

WHAT TO DO
- Every scene keeps a "dialogue" array: {{"speaker": "<exact character name>", "line": "<the exact words>", "delivery": "<short acting note>"}} in playing order. "narration" holds only the narrator's voice-over and may be "" for a dialogue scene.
- Write the dialogue in the language and script the scenes already use for it (the language the idea asks for). A screenplay line written in another language is translated faithfully into it, never copied as is.
- Speech runs at ~2.5 words per second plus a breath after every line, and it needs room to act: a scene's speech (dialogue plus narration) may fill at most three quarters of its scene_duration.
- Keep the same {len(scenes)} scenes in the same order with the same scene_id and scene_duration values; keep every field that is not dialogue or narration unchanged.
- Respond with the single corrected story JSON object only.

SCREENPLAY:
{master_script}

CURRENT STORY JSON:
{json.dumps(current, ensure_ascii=False)}
"""
    try:
        repaired = parse_llm_json(provider.ask(repair_prompt, response_format="application/json"))
    except Exception as e:
        logger.warning(f"Dialogue repair pass failed (keeping the original scenes): {e}")
        print(f"[WARN] Dialogue repair pass failed (keeping original scenes): {str(e)[:200]}")
        return story
    if not isinstance(repaired, dict) or not isinstance(repaired.get("scenes"), list):
        logger.warning("Dialogue repair pass returned no scene list; keeping the original scenes")
        return story
    if len(repaired["scenes"]) != len(scenes):
        logger.warning("Dialogue repair pass changed the scene count; keeping the original scenes")
        return story

    normalize_scene_dialogue(repaired, force=True)
    (merged, excess_before, excess_after,
     fit_before, fit_after) = _merge_repaired_scenes(scenes, repaired["scenes"])
    after_words = dialogue_word_count(merged)
    improved = excess_after < excess_before or fit_after[0] > fit_before[0]
    regressed = (excess_after > excess_before or fit_after[0] < fit_before[0]
                 or fit_after[1] < fit_before[1])
    if not improved or regressed:
        logger.warning(
            f"Dialogue repair pass did not improve the fit (dialogue words {words} -> {after_words}, "
            f"speech overflow {excess_before:.1f} -> {excess_after:.1f}s); keeping the original scenes")
        print("[WARN] Dialogue repair did not improve the fit; keeping the original scenes")
        return story

    logger.info(f"Dialogue repair pass: dialogue words {words} -> {after_words}, "
                f"speech overflow {excess_before:.1f} -> {excess_after:.1f}s")
    print(f"[INFO] Dialogue repaired: {words} -> {after_words} dialogue words, "
          f"overflow {excess_before:.1f}s -> {excess_after:.1f}s")
    for _, scene, speech, limit in overfull_scenes(merged):
        logger.warning(
            f"Scene {scene.get('scene_id')} still holds about {speech:.0f}s of speech for "
            f"{scene.get('scene_duration')}s (at most {limit:g}s fit); its lines will play back to back")
    return {**story, "scenes": merged}


def ensure_dialogue_language(provider, story, language):
    """One pass rewriting the dialogue in the film's language when it came back
    in another script.

    Models drift out of a requested dialogue language ("Dialogs in Urdu"
    answered in English), and no amount of prompt wording makes that reliable.
    For a language written in a non-Latin script the result can be checked
    deterministically (`dialogue_in_wrong_script`): then the model is asked to
    translate every line, and a scene keeps its translated dialogue only if the
    lines still map one to one onto the same speakers.

    Returns the (possibly replaced) story; only `dialogue` arrays are taken
    from the translation, everything else is the original story's.
    """
    scenes = story.get("scenes") or []
    if not dialogue_in_wrong_script(language, scenes):
        return story

    logger.warning(f"Dialogue is not written in {language} as the idea asks; requesting a translation pass")
    print(f"[WARN] Dialogue is not written in {language}; translating the lines")
    current = {k: v for k, v in story.items() if k != "master_script"}
    prompt = f"""DIALOGUE LANGUAGE — this film's dialogue must be written in {language}, but the scenes' dialogue lines are not. Return the corrected story JSON.

WHAT TO DO
- Rewrite EVERY "line" of every scene's "dialogue" array in {language}, written in the {language} script. Translate each line faithfully from its current wording: same meaning, same tone, at most 12 words, phrased the way a native speaker would actually say it - natural, colloquial, actable.
- Keep everything else exactly as it is: the same scenes in the same order, the same "speaker" names (a name is never translated), the same "delivery" notes, the same scene_duration values, the same narration, and every other field.
- Respond with the single corrected story JSON object only.

CURRENT STORY JSON:
{json.dumps(current, ensure_ascii=False)}
"""
    try:
        translated = parse_llm_json(provider.ask(prompt, response_format="application/json"))
    except Exception as e:
        logger.warning(f"Dialogue translation pass failed (keeping the original lines): {e}")
        print(f"[WARN] Dialogue translation failed (keeping the original lines): {str(e)[:200]}")
        return story
    if not isinstance(translated, dict) or not isinstance(translated.get("scenes"), list):
        logger.warning("Dialogue translation pass returned no scene list; keeping the original lines")
        return story
    if len(translated["scenes"]) != len(scenes):
        logger.warning("Dialogue translation pass changed the scene count; keeping the original lines")
        return story

    def speakers(entries):
        return [e["speaker"].strip().casefold() for e in entries]

    merged, translated_count, line_count = [], 0, 0
    for original, new in zip(scenes, translated["scenes"]):
        new_lines = scene_dialogue(new) if isinstance(new, dict) else []
        old_lines = scene_dialogue(original)
        one_to_one = (bool(new_lines) and len(new_lines) == len(old_lines)
                      and speakers(new_lines) == speakers(old_lines))
        if one_to_one and not dialogue_in_wrong_script(language, [new]):
            # only the words are the translation's: speaker and delivery stay
            # the scripted ones (a speaker must keep matching the story cast)
            merged.append({**original, "dialogue": [
                {**old, "line": new_line["line"]}
                for old, new_line in zip(old_lines, new_lines)]})
            translated_count += 1
            line_count += len(new_lines)
        else:
            merged.append(original)
    if not translated_count:
        logger.warning("Dialogue translation pass changed nothing usable; keeping the original lines")
        return story
    logger.info(f"Dialogue translated into {language}: {line_count} lines in "
                f"{translated_count}/{len(scenes)} scene(s)")
    print(f"[INFO] Dialogue translated into {language}: {line_count} lines")
    return {**story, "scenes": merged}


def finalize_story_dialogue(story, provider, master_script, target_length, director_name,
                            idea=""):
    """Give a screenplay story its dialogue layer and make it fit the film.

    Order: dialogue language first (a translation changes the word counts),
    then the fit check - on the final scene durations, so it sees the timing
    the shots will actually be planned against.
    """
    if not isinstance(story, dict) or not is_dialogue_story(director_name):
        return story
    lines = normalize_scene_dialogue(story, force=True)
    words = dialogue_word_count(story.get("scenes") or [])
    budget = speech_word_budgets(target_length)[0] if target_length else None
    print(f"[INFO] Screenplay dialogue: {lines} lines, {words} words (target ~{budget})")
    if provider is None:
        return story
    language, transliterated = detect_dialogue_language(idea)
    if language and not transliterated:
        story = ensure_dialogue_language(provider, story, language)
    if not target_length:
        return story
    return fit_story_dialogue(provider, story, master_script, target_length, budget)


def build_story(idea, director_name="default", target_length=None, aspect_ratio="16:9"):
    """
    Build a cinematic story from an idea using the specified director.
    Performs a two-pass generation:
    1. Generates a master script (story.json base)
    2. Breaks the master script down into detailed scenes.

    Args:
        idea: The video idea/concept
        director_name: Name of story director to use (default: "default")
        target_length: Target video length in seconds (optional).
                      Injected via {VIDEO_LENGTH} placeholder in director prompts.
        aspect_ratio: Video aspect ratio (default: "16:9")

    Returns:
        JSON string with story structure including scenes
    """
    provider = get_provider()
    # Story prompts are long and structural — thinking adds latency/cost
    # without quality here, so turn it off for story-generation calls.
    provider.disable_thinking()

    # Pass 1: Generate Master Script (families can override via <family>/_base/master_script.md)
    master_director = resolve_master_script_director(director_name)
    # The dialogue language the idea names ("Dialogs in Urdu") is told to the
    # screenplay prompts explicitly - left implicit in the idea, models drift
    dialogue_language, transliterated = detect_dialogue_language(idea)
    if dialogue_language:
        print(f"[INFO] Dialogue language: {dialogue_language}"
              f"{' (Latin transliteration)' if transliterated else ''}")
    try:
        master_prompt = fill_story_placeholders(
            load_director_prompt("story", idea, master_director), target_length,
            dialogue_language, transliterated)
        if target_length:
            logger.info(f"Master script requested: {int(target_length)}s (~{int(target_length * SPEECH_WORDS_PER_SECOND)} words)")
            print(f"[INFO] Master script requested: {int(target_length)}s (~{int(target_length * SPEECH_WORDS_PER_SECOND)} words)")
    except (FileNotFoundError, ValueError):
        logger.error("Master script director (master_script.md) not found.")
        print("[WARN] Master script director not found. Generating basic story instead.")
        master_prompt = f"Write a full voice-over script for this idea: {idea}\n\nReturn JSON:\n{{\n 'title': '',\n 'style': '',\n 'master_script': ''\n}}"

    print(f"\n[STORY] Pass 1: Generating Master Script (director: {master_director})...")
    master_json_str = provider.ask(master_prompt, response_format="application/json")
    
    try:
        master_data = parse_llm_json(master_json_str)
        master_script = master_data.get("master_script", "")
    except json.JSONDecodeError as e:
        logger.warning(
            f"Failed to parse master script JSON ({e}). "
            f"Keeping scene-pass title/style. Response snippet: {str(master_json_str)[:200]!r}"
        )
        master_script = idea
        # Empty dict so the merge below falls through to the story's own
        # title/style instead of overwriting them with placeholders.
        master_data = {}

    # Pass 2: Break down into scenes
    print("\n[STORY] Pass 2: Generating Scenes from Master Script...")
    scene_idea = f"IDEA: {idea}\n\nMASTER SCRIPT TO BREAK DOWN INTO SCENES:\n{master_script}"
    
    try:
        # Try to use director prompt
        prompt = load_director_prompt("story", scene_idea, director_name)
        if target_length and "{VIDEO_LENGTH}" in prompt:
            logger.info(f"Video length context injected into scene gen: {int(target_length)}s")
        prompt = fill_story_placeholders(prompt, target_length, dialogue_language, transliterated)

    except (FileNotFoundError, ValueError):
        # Fall back to legacy prompt if director not found
        print(f"[WARN] Story director '{director_name}' not found, using legacy prompt")
        prompt = f"""
Expand into cinematic narrative.

Return JSON:

{{
 "title":"",
 "style":"ultra cinematic documentary",
 "scenes":[
   {{
     "location":"Short name of the setting",
     "characters":"",
     "action":"",
     "emotion":"",
     "narration":"",
     "set_prompt":"Detailed background image prompt for this scene's environment: a WIDE ESTABLISHING VIEW of the empty space — geography, architecture and key objects with materials, weather and time of day, lighting, atmosphere. Not a close-up, no camera language; 2-3 sentences, no people.",
     "scene_duration":15
   }}
 ]
}}

{scene_idea}
"""

    story_json_str = provider.ask(prompt, response_format="application/json")

    # Merge, Validate, and Format — parse_story_json_with_retry raises ValueError
    # on unrecoverable output instead of letting raw invalid text propagate
    if target_length:
        story = parse_story_json_with_retry(provider, story_json_str)
        # Add total_duration to story dict
        story['total_duration'] = int(target_length)

        # Inject master data (Pass 2 director is authoritative; Pass 1 fills gaps)
        story['title'] = story.get('title') or master_data.get('title') or 'Video'
        story['style'] = story.get('style') or master_data.get('style') or 'cinematic'
        story['master_script'] = master_script

        # Add aspect_ratio to story dict
        story['aspect_ratio'] = aspect_ratio

        is_valid, actual_total, diff, adjusted_story = validate_and_adjust_scene_durations(
            story, target_length, config.SCENE_DURATION_TOLERANCE
        )
        normalize_scene_ids(adjusted_story)
        # Screenplays carry a dialogue layer: make sure it is in the film's
        # dialogue language, survived Pass 2 and fits the final scene durations
        adjusted_story = finalize_story_dialogue(
            adjusted_story, provider, master_script, target_length, director_name, idea=idea)
        story_json_str = json.dumps(adjusted_story, ensure_ascii=False, indent=2)
    else:
        # Format JSON with proper indentation even when no target_length
        story = parse_story_json_with_retry(provider, story_json_str)
        # Pass 2 director is authoritative; Pass 1 fills gaps
        story['title'] = story.get('title') or master_data.get('title') or 'Video'
        story['style'] = story.get('style') or master_data.get('style') or 'cinematic'
        story['master_script'] = master_script
        story = finalize_story_dialogue(
            story, provider, master_script, target_length, director_name, idea=idea)

        # Add aspect_ratio to story dict
        story['aspect_ratio'] = aspect_ratio

        # Ensure scene_id in all scenes
        if 'scenes' in story:
            for i, scene in enumerate(story['scenes']):
                if 'scene_id' not in scene:
                    scene['scene_id'] = i

        normalize_scene_ids(story)
        story_json_str = json.dumps(story, ensure_ascii=False, indent=2)

    return story_json_str


def build_story_then_vs_now(movie_name: str, director_name: str = "then_vs_now/then_vs_now", target_length: int = None, aspect_ratio: str = "16:9") -> str:
    """
    Build a ThenVsNow story from a movie name.
    Generates both story and shots directly (bypasses shot planner).

    Args:
        movie_name: The movie name to generate a reunion story for
        target_length: Target video length in seconds (optional)
        aspect_ratio: Video aspect ratio (default: "16:9")

    Returns:
        JSON string with story structure including shots
    """
    provider = get_provider()
    # Story prompts are long and structural — thinking adds latency/cost
    # without quality here, so turn it off for story-generation calls.
    provider.disable_thinking()

    # Load the then_vs_now director
    # If director_name doesn't already contain a slash, prepend 'then_vs_now/'
    final_director_path = director_name
    if "/" not in director_name:
        final_director_path = f"then_vs_now/{director_name}"
        
    prompt = load_director_prompt("story", movie_name, final_director_path)
    if target_length:
        prompt = prompt.replace("{VIDEO_LENGTH}", str(int(target_length)))

    # Generate story
    logger.info(f"Generating ThenVsNow story for movie: {movie_name}")
    print(f"[INFO] Generating ThenVsNow story for movie: {movie_name}")

    story_json_str = provider.ask(prompt, response_format="application/json")
    story = parse_llm_json(story_json_str)

    # Ensure project_type is set
    story['project_type'] = ProjectType.THEN_VS_NOW

    # Add aspect_ratio to story
    story['aspect_ratio'] = aspect_ratio

    # CRITICAL: Normalize scene_id to array indices BEFORE generating shots
    # This ensures shots' scene_id values match the scenes array indices
    if 'scenes' in story:
        for i, scene in enumerate(story['scenes']):
            scene['scene_id'] = i

    # Generate shots directly from story
    shots = generate_shots_from_then_vs_now_story(story)
    story['shots'] = shots

    # Validate durations
    if target_length:
        story['total_duration'] = int(target_length)
        _, _, _, adjusted_story = validate_and_adjust_scene_durations(
            story, target_length, config.SCENE_DURATION_TOLERANCE
        )
        story_json_str = json.dumps(adjusted_story, ensure_ascii=False, indent=2)
    else:
        story_json_str = json.dumps(story, ensure_ascii=False, indent=2)

    logger.info(f"Generated {len(shots)} shots for {len(story.get('characters', []))} characters")
    return story_json_str


def build_story_asmr_glass_cutting(
    idea: str,
    director_name: str = "asmr/asmr_glass_cutting",
    shot_duration: int = 5,
    aspect_ratio: str = "16:9"
) -> str:
    """
    Build an ASMR glass cutting story from natural language input.

    The story director generates all shots directly in a single LLM call,
    following the THEN_VS_NOW pattern.

    Args:
        idea: Natural language description (e.g., "create videos of strawberry, apple, and tomato")
        director_name: Story director to use (default: "asmr/asmr_glass_cutting")
        shot_duration: Fixed duration for each shot in seconds (default: 5)
        aspect_ratio: Video aspect ratio (default: "16:9")

    Returns:
        JSON string with story structure including shots

    Raises:
        ValueError: If input is too short or LLM doesn't generate valid shots
    """
    from web_ui.backend.models.story import ProjectType

    # Validate input
    if not idea or len(idea.strip()) < 3:
        raise ValueError("Please describe the fruits or vegetables to create videos for")

    provider = get_provider()
    # Story prompts are long and structural — thinking adds latency/cost
    # without quality here, so turn it off for story-generation calls.
    provider.disable_thinking()

    # Load the ASMR director prompt
    # If director_name doesn't contain a slash, assume it's in the asmr/ directory
    final_director_path = director_name
    if "/" not in director_name:
        final_director_path = f"asmr/{director_name}"

    try:
        prompt = load_director_prompt("story", idea, final_director_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load ASMR director: {e}")
        raise ValueError(f"ASMR glass cutting director not found: {final_director_path}")

    # Generate story with shots
    logger.info(f"Generating ASMR glass cutting story for: {idea}")
    print(f"[INFO] Generating ASMR glass cutting story for: {idea}")

    try:
        story_json_str = provider.ask(prompt, response_format="application/json")
        story = parse_llm_json(story_json_str)

        # Handle case where LLM returns an array instead of object
        if isinstance(story, list):
            if len(story) > 0:
                logger.warning(f"LLM returned array, extracting first element")
                story = story[0]
            else:
                raise ValueError("LLM returned empty array. Please try a different description.")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError("Failed to generate valid story. Please try a different description.")

    # Ensure project_type is set
    story['project_type'] = ProjectType.ASMR_GLASS_CUTTING

    # Add aspect_ratio
    story['aspect_ratio'] = aspect_ratio

    # Validate expanded_objects
    if not story.get("expanded_objects") or len(story.get("expanded_objects", [])) == 0:
        logger.warning("No expanded_objects in response")
        raise ValueError(
            "Could not identify objects from input. "
            "Please specify fruits or vegetables more clearly."
        )

    # Validate shots were generated
    if "shots" not in story or len(story["shots"]) == 0:
        logger.error("No shots in generated story")
        raise ValueError("No shots generated. Try a different description.")

    # Warn if too few shots
    if len(story["shots"]) < 3:
        logger.warning(f"Only {len(story['shots'])} shots generated. Expected at least 3.")

    # Calculate and set total_duration
    shot_count = len(story["shots"])
    story['total_duration'] = shot_count * shot_duration

    # Update shot durations
    for shot in story["shots"]:
        shot["duration"] = shot_duration

    # Ensure each shot has required fields
    for i, shot in enumerate(story["shots"]):
        if "id" not in shot:
            shot["id"] = f"shot_{i+1:03d}"
        if "index" not in shot:
            shot["index"] = i + 1
        if "shot_type" not in shot:
            shot["shot_type"] = "asmr_glass_cutting"

        # Handle backward compatibility: map 'prompt' to 'image_prompt' if needed
        if "prompt" in shot and "image_prompt" not in shot:
            shot["image_prompt"] = shot["prompt"]

        # Validate image_prompt exists and is detailed
        if "image_prompt" not in shot or len(shot.get("image_prompt", "")) < 50:
            logger.warning(f"Shot {i+1} has missing or short image_prompt")

        # Validate motion_prompt exists and is detailed
        if "motion_prompt" not in shot or len(shot.get("motion_prompt", "")) < 50:
            logger.warning(f"Shot {i+1} has missing or short motion_prompt")
            # Add fallback motion_prompt for video generation if missing
            object_name = shot.get("object_name", "object")
            shot["motion_prompt"] = f"Close-up shot of precision cutting through {object_name} glass sculpture. Camera maintains steady focus on the cutting action with slight push-in motion. Glass pieces separate and fall with realistic physics. Shallow depth of field, cinematic ASMR style."

    logger.info(f"Generated {len(story['shots'])} shots for {len(story['expanded_objects'])} objects")
    print(f"[INFO] Generated {len(story['shots'])} shots for {len(story['expanded_objects'])} objects")

    return json.dumps(story, ensure_ascii=False, indent=2)


def generate_shots_from_then_vs_now_story(story: dict) -> list:
    """
    Generate FLFI2V shots directly from a ThenVsNow story.
    Each character gets 1 shot with BOTH Meeting and Departure videos.

    Args:
        story: Story dict with characters and scenes

    Returns:
        List of shot dicts with FLFI2V structure
    """
    characters = story.get('characters', [])
    scenes = story.get('scenes', [])

    # Build scene lookup
    scenes_by_id = {scene.get('scene_id', 0): scene for scene in scenes}

    # Group characters by scene_id
    characters_by_scene = {}
    for char in characters:
        scene_id = char.get('scene_id', 0)  # Use character's scene_id
        if scene_id not in characters_by_scene:
            characters_by_scene[scene_id] = []
        characters_by_scene[scene_id].append(char)

    shots = []
    shot_index = 1

    # Generate shots in scene order
    for scene_id in sorted(characters_by_scene.keys()):
        scene = scenes_by_id.get(scene_id, {})
        scene_name = scene.get('scene_name', f'Scene {scene_id}')
        scene_characters = characters_by_scene[scene_id]

        for char_idx, character in enumerate(scene_characters):
            # Single shot per character with BOTH meeting and departure prompts
            shot = {
                'id': uuid.uuid4().hex[:8],
                'index': shot_index,
                'is_flfi2v': True,
                'character_id': f"char_{scene_id:02d}_{char_idx:02d}",
                'character_name': character.get('name', ''),
                'scene_id': scene_id,
                'scene_name': scene_name,
                'order_in_scene': char_idx,
                'then_image_prompt': character.get('then_prompt', ''),
                'now_image_prompt': character.get('now_prompt', ''),
                'meeting_video_prompt': character.get('meeting_prompt', ''),
                'departure_video_prompt': character.get('departure_prompt', ''),
                'camera': 'tracking',
                'narration': '',
                'batch_number': 1,
                # Standard fields for compatibility
                'image_prompt': character.get('now_prompt', ''),
                'motion_prompt': character.get('meeting_prompt', ''),  # Default to meeting
                'image_generated': False,
                'image_path': None,
                'image_paths': [],
                'video_rendered': False,
                'video_path': None,
                'video_paths': []
            }
            shots.append(shot)
            shot_index += 1

    logger.info(f"Generated {len(shots)} shots for {len(characters)} characters (1 shot per character with both meeting and departure prompts)")
    return shots
