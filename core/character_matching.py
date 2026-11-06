"""Character-name matching between story characters and shot/scene data.

The story pass-2 LLM names top-level characters with display names
("Chi She (Red Snake)") while scene `characters` strings and shot
`characters` lists usually carry shortened forms of the same name
("Chi She"). Everything that attaches character data to shots —
reference sheets, r2v video refs, voice lines — must therefore resolve
names tolerantly instead of requiring exact equality.
"""
import re

# Keep letters (ASCII + Latin-1 supplement + accented), digits, CJK and
# Korean syllables; everything else collapses to a space.
_KEEP_RE = re.compile(r"[^0-9a-zà-öø-ÿ\u00c0-\u024f\u0370-\u03ff"
                      r"\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+")
# ASCII and full-width bracketed qualifiers ("(Red Snake)", "（白蛇）")
_PAREN_RE = re.compile(r"[(（][^)）]*[)）]|\[[^\]]*\]|【[^】]*】")


def normalize_character_key(name):
    """Normalized comparison key for a character name.

    Casefolds, drops parenthesized/square-bracketed qualifiers ("Chi She
    (Red Snake)" -> "chi she") and punctuation. CJK names survive
    unchanged apart from punctuation removal."""
    s = (name or "").strip().lower()
    s = _PAREN_RE.sub(" ", s)
    s = _KEEP_RE.sub(" ", s)
    return " ".join(s.split())


def _full_words(name):
    """Word set of the full lowercased name, qualifier words INCLUDED
    ("Chi She (Red Snake)" -> {chi, she, red, snake}) — used for containment
    matching so qualifier-only forms ("Red Snake") also resolve."""
    s = _KEEP_RE.sub(" ", (name or "").strip().lower())
    return set(s.split())


def resolve_character_name(raw, names):
    """Match a shot/scene character name to a story character name.

    `names` is the list of story character display names. Returns the
    matched display name, or None when nothing matches.

    Matching tiers (case-insensitive throughout):
    1. exact display-name equality
    2. equality of normalized keys, with or without parenthesized
       qualifiers ("Chi She" == "Chi She (Red Snake)")
    3. word containment — every word of `raw` (len >= 2) appears in the
       candidate's full name including qualifier words; the candidate with
       the fewest extra words wins, and only when that best candidate is
       unique ("Chi She" and "Red Snake" both resolve to
       "Chi She (Red Snake)", but "Snake" alone stays unresolved when it
       could mean several characters)."""
    raw = (raw or "").strip()
    if not raw:
        return None
    names = [n for n in (names or []) if (n or "").strip()]
    if not names:
        return None

    raw_lower = raw.lower()
    exact = [n for n in names if n.strip().lower() == raw_lower]
    if exact:
        return exact[0]

    raw_key = normalize_character_key(raw)
    if not raw_key:
        return None

    by_key = {}
    by_full = {}
    for n in names:
        key = normalize_character_key(n)
        if key and key not in by_key:
            by_key[key] = n
        full = " ".join(sorted(_full_words(n)))
        if full and full not in by_full:
            by_full[full] = n
    if raw_key in by_key:
        return by_key[raw_key]
    raw_full = " ".join(sorted(_full_words(raw)))
    if raw_full in by_full:
        return by_full[raw_full]

    raw_words = {w for w in raw_key.split() if len(w) >= 2} | \
        {w for w in _full_words(raw) if len(w) >= 2}
    if not raw_words:
        return None
    best = None  # (extra_word_count, name)
    ties = False
    for n in by_key.values():
        key_words = _full_words(n)
        if not raw_words <= key_words:
            continue
        extra = len(key_words - raw_words)
        if best is None or extra < best[0]:
            best = (extra, n)
            ties = False
        elif extra == best[0]:
            ties = True
    if best is None or ties:
        return None
    return best[1]


def canonicalize_name_list(raw_names, story_names):
    """Resolve a list of shot/scene character names against the story cast.

    Returns (canonical_names, changed): each raw name is replaced by its
    story display name when it resolves and differs; unresolved names are
    kept verbatim. `changed` is True when any name was rewritten."""
    result = []
    changed = False
    for raw in raw_names or []:
        raw = (raw or "").strip()
        if not raw:
            continue
        resolved = resolve_character_name(raw, story_names)
        if resolved and resolved != raw:
            result.append(resolved)
            changed = True
        else:
            result.append(raw)
    return result, changed


def canonicalize_scene_cast(scene, character_names, prop_names=None):
    """Rewrite a scene's `characters` string / list and `props` list in place
    using story display names, so downstream consumers (LLM shot planning,
    ref syncing) see names consistent with story.characters."""
    if character_names:
        chars = scene.get('characters')
        if isinstance(chars, str):
            # LLM scene strings may separate names with full-width commas
            parts = [p.strip() for p in chars.replace("，", ",").split(",") if p.strip()]
            canonical, _ = canonicalize_name_list(parts, character_names)
            scene['characters'] = ", ".join(canonical)
        elif isinstance(chars, list):
            canonical, _ = canonicalize_name_list(chars, character_names)
            scene['characters'] = canonical
    if prop_names:
        props = scene.get('props')
        if isinstance(props, list):
            canonical, _ = canonicalize_name_list(props, prop_names)
            scene['props'] = canonical
