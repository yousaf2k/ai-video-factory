"""Scripted dialogue shared by the story pass and the shot planner.

Movie stories carry their spoken lines as a structured ``dialogue`` list on
every scene (``{speaker, line, delivery}`` in playing order). The screenplay
prompts ask for it; these helpers keep it well-formed and verify that lines
written at story level actually reach the shot ``video_prompt`` as
``<d>[Language] ...</d>`` speech - without that check the lines were silently
lost between passes and films came out nearly silent.
"""
import re
from difflib import SequenceMatcher

# Spoken words per second of screen time - every speech budget derives from
# it (a 10-word line needs ~4s), matching MiniMax H3's dialogue pacing.
SPEECH_WORDS_PER_SECOND = 2.5
# A breath after every spoken line, on top of the words themselves. Counting
# it is what keeps scenes and clips consistent: a scene of many short lines
# takes longer to play than its word count suggests.
DIALOGUE_PAUSE_SECONDS = 0.6
# Share of running time that may be spoken, for a scene and for a clip alike.
# Past it the lines run wall to wall and the video model rushes or clips them.
SPEECH_FIT_SHARE = 0.75


def speaking_seconds(texts):
    """Seconds a group of spoken texts takes to play: their words at the
    spoken-word rate plus a breath after each non-empty text."""
    spoken = [t for t in texts if t and str(t).strip()]
    if not spoken:
        return 0.0
    return (sum(count_words(t) for t in spoken) / SPEECH_WORDS_PER_SECOND
            + DIALOGUE_PAUSE_SECONDS * len(spoken))

# A scripted line counts as spoken when a <d> block equals it, contains it, or
# is this similar (tolerates a stray comma or a typo in a verbatim line).
_FUZZY_MATCH_RATIO = 0.92
# Shorter normalized lines are too generic for containment/fuzzy matching
# ("No." would match almost any answer), so they must match exactly.
_MIN_FUZZY_LENGTH = 12

_DIALOGUE_TAG_RE = re.compile(r"<d>(.*?)</d>", re.DOTALL | re.IGNORECASE)
# Bracketed cues, from a language tag ([Urdu], [unclear]) to a narration
# direction ([Ambient Horror Sounds: low wind, distant dog])
_LANGUAGE_TAG_RE = re.compile(r"\[[^\]\n]{1,40}\]")
_BRACKET_CUE_RE = re.compile(r"\[[^\]\n]{1,120}\]")
_QUOTED_LINE_RE = re.compile(r'"([^"\n]+)"')
# "SPEAKER (delivery): line" / "SPEAKER: \"line\"" / "NARRATOR (voice-over): ..."
_SPEAKER_LINE_RE = re.compile(r"^\s*([^:(\n]{1,60}?)\s*(?:\(([^)\n]*)\))?\s*:\s*(.+)$", re.DOTALL)
# Cue ending right before a quoted screenplay line, and the narrator's variant
_SPEECH_CUE_RE = re.compile(r"[^\s:][^:\n]{0,60}?:\s*$")
_NARRATOR_CUE_RE = re.compile(r"(?i)(?:^|\W)narrator\s*(?:\([^)\n]*\))?\s*:\s*$")


def count_words(text):
    """Word count of a spoken text: tokens holding at least one letter/digit.

    Bracketed cues (``[Urdu]``, ``[Silence]``, ``[Ambient Horror Sounds: low
    wind]``) are not spoken and do not count.
    """
    if not text:
        return 0
    text = _BRACKET_CUE_RE.sub(" ", str(text))
    return len([w for w in re.split(r"\s+", text) if any(ch.isalnum() for ch in w)])


def normalize_speech(text):
    """Comparison key for spoken text: casefolded letters and digits only.

    Drops ``[Language]`` tags, punctuation, quotes, dashes and whitespace, so a
    verbatim line still matches after a curly quote or a changed comma.
    """
    text = _LANGUAGE_TAG_RE.sub(" ", text or "")
    text = text.casefold()
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


def speech_matches(line, spoken):
    """True when `spoken` (a ``<d>`` block's text) carries the scripted `line`."""
    a, b = normalize_speech(line), normalize_speech(spoken)
    if not a:
        return False
    if a == b:
        return True
    if len(a) < _MIN_FUZZY_LENGTH or not b:
        return False
    if a in b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= _FUZZY_MATCH_RATIO


def shot_dialogue(shot):
    """Texts of a shot's ``<d>`` speech blocks, in order."""
    if not isinstance(shot, dict):
        return []
    return [m.strip() for m in _DIALOGUE_TAG_RE.findall(shot.get("video_prompt") or "")]


def _strip_quotes(text):
    text = (text or "").strip()
    for a, b in (('“', '”'), ('‘', '’'), ('"', '"'), ("'", "'")):
        if len(text) >= 2 and text.startswith(a) and text.endswith(b):
            return text[1:-1].strip()
    return text


def _split_speaker_line(item):
    """(speaker, line, delivery) from a ``SPEAKER (delivery): "line"`` string."""
    match = _SPEAKER_LINE_RE.match(item.strip())
    if not match:
        return "", _strip_quotes(item), ""
    return match.group(1).strip(), _strip_quotes(match.group(3)), (match.group(2) or "").strip()


def normalize_dialogue(raw):
    """Well-formed ``[{speaker, line, delivery}]`` from whatever an LLM put in
    a scene's ``dialogue`` field.

    Accepts the object form, ``"SPEAKER (delivery): line"`` strings and a
    prose block of such lines; entries without a line are dropped.
    """
    if isinstance(raw, str):
        raw = [l for l in raw.splitlines() if l.strip()]
    entries = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            line = str(item.get("line") or item.get("text") or item.get("dialogue") or "").strip()
            speaker = str(item.get("speaker") or item.get("character") or item.get("name") or "").strip()
            delivery = str(item.get("delivery") or item.get("direction") or "").strip()
        elif isinstance(item, str):
            speaker, line, delivery = _split_speaker_line(item)
        else:
            continue
        if line:
            entries.append({"speaker": speaker, "line": line, "delivery": delivery})
    return entries


def scene_dialogue(scene):
    """A scene's scripted dialogue entries (empty list when it has none)."""
    return normalize_dialogue(scene.get("dialogue")) if isinstance(scene, dict) else []


def scene_speaking_seconds(scene):
    """Seconds a scene's speech takes to play: every dialogue line (with its
    breath) plus the narrator's voice-over."""
    if not isinstance(scene, dict):
        return 0.0
    return (speaking_seconds([e["line"] for e in scene_dialogue(scene)])
            + count_words(scene.get("narration") or "") / SPEECH_WORDS_PER_SECOND)


def bound_voice_text(char):
    """A character's explicitly bound ``voice.text`` ('' when there is none)."""
    voice = char.get("voice") if isinstance(char, dict) else None
    return str(voice.get("text") or "").strip() if isinstance(voice, dict) else ""


def character_voice(char):
    """A story character's speaking voice: the bound ``voice.text``, else the
    ``voice_type`` the story directors write. Shot prompts copy it verbatim so
    separately generated clips keep the same voice."""
    if not isinstance(char, dict):
        return ""
    return bound_voice_text(char) or str(char.get("voice_type") or "").strip()


def normalize_scene_dialogue(story, force=False):
    """Clean up every scene's ``dialogue`` list in place; returns the total
    number of dialogue lines.

    Scenes that never carried the key are left untouched unless ``force`` —
    dialogue-layer directors (movie screenplays) get an explicit ``[]`` so the
    planner and the UI can rely on the field; narrated story families such as
    documentaries keep their scene shape unchanged.
    """
    if not isinstance(story, dict):
        return 0
    total = 0
    for scene in story.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        if "dialogue" in scene or force:
            scene["dialogue"] = scene_dialogue(scene)
            total += len(scene["dialogue"])
    return total


def dialogue_word_count(scenes):
    """Total spoken words across the scenes' dialogue."""
    return sum(count_words(e["line"]) for s in scenes or [] for e in scene_dialogue(s))


def format_dialogue(entries, start=1):
    """Numbered ``N. SPEAKER (delivery): "line"`` lines for prompts and logs."""
    out = []
    for i, e in enumerate(entries or [], start):
        head = e.get("speaker") or "SPEAKER"
        if e.get("delivery"):
            head += f" ({e['delivery']})"
        out.append(f'{i}. {head}: "{e["line"]}"')
    return "\n".join(out)


def scripted_lines(text):
    """Dialogue lines of a master script screenplay: the quoted spans a
    ``SPEAKER (delivery):`` cue introduces. Narrator lines and quotes that are
    not speech (a sign, a scare quote) are left out."""
    lines, cued_any = [], False
    for match in _QUOTED_LINE_RE.finditer(text or ""):
        line = match.group(1).strip()
        if count_words(line) < 2:
            continue
        cue = text[text.rfind("\n", 0, match.start()) + 1:match.start()]
        if _NARRATOR_CUE_RE.search(cue):
            continue
        cued = bool(_SPEECH_CUE_RE.search(cue))
        cued_any = cued_any or cued
        lines.append((cued, line))
    # Prose without cues: every non-narrator quote is treated as a spoken line
    return [line for cued, line in lines if cued] if cued_any else [line for _, line in lines]


def missing_dialogue_lines(lines, scenes):
    """Scripted lines that no scene dialogue entry carries (verbatim)."""
    spoken = [e["line"] for s in scenes or [] for e in scene_dialogue(s)]
    return [line for line in lines or [] if not any(speech_matches(line, s) for s in spoken)]


def unplaced_dialogue(scenes, shots):
    """``{scene_id: [entries]}`` for scripted lines missing from the shots.

    A line is placed when a shot of its scene speaks it: one ``<d>`` block
    carries it, or the shot's blocks joined in order do (a line split across
    sub-shots with ``<scenetrans>``).
    """
    said = {}
    for shot in shots or []:
        if not isinstance(shot, dict):
            continue
        blocks = shot_dialogue(shot)
        said.setdefault(str(shot.get("scene_id")), []).extend(
            [normalize_speech(b) for b in blocks] + [normalize_speech(" ".join(blocks))])
    missing = {}
    for scene in scenes or []:
        entries = scene_dialogue(scene)
        if not entries:
            continue
        lost = [e for e in entries
                if not any(speech_matches(e["line"], s) for s in said.get(str(scene.get("scene_id")), []))]
        if lost:
            missing[scene.get("scene_id")] = lost
    return missing
