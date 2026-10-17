"""Shared prompt composer for reference-to-video (r2v) and text-to-video (t2v).

Everything applied to the shots agent's raw output lives here exactly once and
is called by both the CLI flow (core/main.py) and the backend video path, so
the logic never forks:

- voice-text embedding (D13): every character bound to a text voice must have
  that text appear VERBATIM in the prompt; when the agent's prose lost it, a
  deterministic voice-note line is inserted into subject_definitions
  (idempotent — never duplicated).
- <Picture N> label pruning (D3): the agent numbers pictures in attachment
  convention order (characters -> background -> props). When the slot budget
  dropped trailing refs, citations beyond the attached count are stripped so
  the prompt never references a picture that isn't wired.
- <Audio N> definitions: when voice/BGM audio refs are attached, a
  voice-timbre definition line is appended to subject_definitions.
- 7000-character R2V prompt cap (Q4): enforced as a problem for the caller
  to repair (the shot planner's LLM repair loop).

t2v prompts (three-field T2VA format) use the same voice/cap handling; label
handling is a no-op with zero refs.
"""
import logging
import re

logger = logging.getLogger(__name__)

R2V_PROMPT_CHAR_LIMIT = 7000

_PICTURE_RE = re.compile(r"<Picture (\d+)>")

R2V_REQUIRED_SECTIONS = (
    "subject_definitions:",
    "summary:",
    "retention_analysis:",
    "detailed_description:",
    "overall_soundscape:",
    "non_diegetic_music:",
)


def _voice_texts_for_shot(shot, story):
    """[(character_name, voice_text)] for characters in this shot that have one."""
    story = story or {}
    voices = {}
    for char in story.get('characters') or []:
        name = (char.get('name') or '').strip()
        voice = char.get('voice') or {}
        text = (voice.get('text') or '').strip() if isinstance(voice, dict) else ''
        if name and text:
            voices[name] = text
    if not voices:
        return []

    names = shot.get('characters')
    if not names:
        single = (shot.get('character_name') or '').strip()
        names = [single] if single else []
    return [(n, voices[n]) for n in names if n in voices]


def _insert_into_subject_definitions(prompt: str, lines) -> str:
    """Append definition lines at the end of the subject_definitions block."""
    if not lines:
        return prompt
    marker = "subject_definitions:"
    idx = prompt.find(marker)
    if idx == -1:
        # T2V has no subject_definitions block: append as a trailing note
        return prompt.rstrip() + "\n\n" + "\n".join(lines) + "\n"
    # find the next blank line (end of the block) or fall back to end of text
    rest = prompt[idx + len(marker):]
    match = re.search(r"\n\s*\n", rest)
    insert_at = idx + len(marker) + (match.start() if match else len(rest))
    block = "\n".join(lines)
    return prompt[:insert_at].rstrip("\n") + "\n" + block + "\n" + prompt[insert_at:].lstrip("\n")


def prune_picture_labels(prompt: str, attached_picture_count):
    """Strip <Picture N> citations for pictures beyond the attached count.

    The agent numbers citations in attachment-convention order, so citations
    1..attached stay and any higher number is a ref the slot budget dropped.
    The citation is removed while keeping the sentence readable; the subject
    definition itself stays (text-only subject).
    """
    if attached_picture_count is None:
        return prompt, 0
    dropped = set()
    for m in _PICTURE_RE.finditer(prompt):
        if int(m.group(1)) > attached_picture_count:
            dropped.add(int(m.group(1)))
    if not dropped:
        return prompt, 0
    result = prompt
    for n in sorted(dropped, reverse=True):
        # "in <Picture n>" / "from <Picture n>" / "and <Picture n>" / bare
        result = re.sub(rf"\s*(?:in|from|using|and)\s+<Picture {n}>", "", result)
        result = result.replace(f"<Picture {n}>", "")
    result = re.sub(r"[ \t]{2,}", " ", result)
    logger.info(f"[COMPOSER] Stripped {len(dropped)} unattached <Picture> citation(s): {sorted(dropped)}")
    return result, len(dropped)


def append_audio_definitions(prompt: str, audio_attachments):
    """Append <Audio N> voice-timbre definition lines to subject_definitions.

    audio_attachments: list of dicts {name: character name, speaker: '(S1)'-style
    id or None}. The agent's own citation prose (if any) is left untouched.
    """
    if not audio_attachments:
        return prompt
    existing = {m for m in re.findall(r"<Audio (\d+)>", prompt)}
    lines = []
    next_id = 1
    for att in audio_attachments:
        while f"{next_id}" in existing:
            next_id += 1
        speaker = att.get('speaker')
        name = att.get('name', 'the speaker')
        line = f"<Audio {next_id}> is the voice-timbre reference for {name}"
        if speaker:
            line += f" {speaker}"
        line += "."
        lines.append(line)
        existing.add(f"{next_id}")
    return _insert_into_subject_definitions(prompt, lines)


def embed_voice_texts(prompt: str, voice_pairs):
    """Ensure every bound character voice text appears verbatim in the prompt.

    Returns (prompt, missing_names). Missing texts are inserted as a
    deterministic voice-note line in subject_definitions (idempotent).
    """
    missing = [(name, text) for name, text in voice_pairs if text not in prompt]
    if not missing:
        return prompt, []
    lines = [f"The voice of {name}: {text}." for name, text in missing]
    prompt = _insert_into_subject_definitions(prompt, lines)
    logger.info(f"[COMPOSER] Injected voice text for {len(missing)} character(s): {[n for n, _ in missing]}")
    return prompt, [name for name, _ in missing]


def validate_composed_prompt(prompt: str, r2v_six_sections=False):
    """Structural checks the composer can do deterministically.

    Returns a list of problems (empty = valid).
    """
    problems = []
    if not prompt or not prompt.strip():
        problems.append("empty video_prompt")
        return problems
    if r2v_six_sections:
        lowered = prompt.lower()
        for section in R2V_REQUIRED_SECTIONS:
            if section not in lowered:
                problems.append(f"missing section '{section.rstrip(':')}'")
    if len(prompt) > R2V_PROMPT_CHAR_LIMIT:
        problems.append(
            f"prompt exceeds the {R2V_PROMPT_CHAR_LIMIT}-character R2V limit "
            f"({len(prompt)} chars)")
    return problems


def compose_video_prompt(shot, story=None, attached_picture_count=None,
                         audio_attachments=None, r2v_six_sections=False):
    """Full compose pipeline over a shot's video_prompt.

    Returns (composed_prompt, problems). problems is empty when the prompt is
    structurally valid and fully self-consistent; callers feed non-empty
    problems into the shot planner's repair path.
    """
    prompt = (shot.get('video_prompt') or shot.get('motion_prompt') or '').strip()

    prompt, _ = prune_picture_labels(prompt, attached_picture_count)
    prompt, _ = embed_voice_texts(prompt, _voice_texts_for_shot(shot, story))
    if audio_attachments:
        prompt = append_audio_definitions(prompt, audio_attachments)
    problems = validate_composed_prompt(prompt, r2v_six_sections=r2v_six_sections)
    return prompt, problems
