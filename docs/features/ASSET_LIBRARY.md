# Assets Feature — Design & Implementation Plan (v2)

A global **Asset Library** (nested categories, multiple library folders, image/video/audio/music
assets) plus **per-shot references**: assets attached to shots and injected into image/video
generation as references.

**v2 change:** there is **no metadata JSON**. The filename *is* the metadata:
`{ID}-{Title}.{ext}` stored flat inside its category folder. Asset type is bound to the
top-level category (`Images`/`Videos`/`Audio`/`Music`), addressed by one-letter aliases
(`i`/`v`/`a`/`m`) in URLs.

> Storage note: `.env` sets `OUTPUT_DIR="E:/output"`, so `output/Assets` resolves to
> `E:/output/Assets` via `config.resolve_path()`. Relative `output/...` paths in any persisted
> config follow the existing `shots.json` convention.

---

## 1. Key decisions

| # | Topic | Decision | Rationale |
|---|-------|----------|-----------|
| 1 | Library root | `{OUTPUT_DIR}/Assets` (default library); more roots via `.env` `ASSET_LIBRARY_DIRS` (semicolon-separated) | Fits the existing `.env` / `config_api` settings mechanism; no extra settings JSON |
| 2 | Categories | Nested subfolders, arbitrary depth. Top-level folder = asset type: `Images`, `Videos`, `Audio`, `Music` (extensible map). All asset files stored **flat in their category folder** — no per-asset folders | Folder rename = category rename; disk is the truth, nothing to sync |
| 3 | Filename = metadata | `{id}-{title}{ext}`, e.g. `9f3ab21c-Rainy Neon Street.png`. `id` = 8-char uuid hex (globally unique); `title` = everything after the **first** `-` (may contain spaces/dashes); `title` unique within its folder (case-insensitive) | Split-on-first is unambiguous since ids are dash-free hex |
| 4 | Type | Derived from top-level category: `Images→image`, `Videos→video`, `Audio→audio`, `Music→music`. Type letter aliases: `i`, `v`, `a`, `m` | One registry map in the backend; the "audio vs music" question resolves itself — the main category you upload into decides |
| 5 | URL scheme | `GET /api/assets/{letter}/{category_path}/{id}` → file. Example: `/api/assets/i/characters/9f3ab21c` serves `E:/output/Assets/Images/characters/9f3ab21c-Rainy Neon Street.png`. Category segments match case-insensitively. `.../{id}/thumb` serves the cached thumbnail | Exactly the requested Explorer-style address; ids are stable even if the title is renamed |
| 6 | References | Shot field `reference_asset_ids: string[]`, ordered — first = primary. Two ref shapes: **library** `"i/9f3ab21c"` (non-default libraries prefix the slug: `"stock/i/9f3ab21c"`) and **project media** `"p/{project_id}/images/shot_001_001.png"` | Self-describing; library refs survive title renames and category moves (id never changes); project refs resolve by direct path check against the other project's folder |
| 7 | Serving | The URL *is* the address (§5 above); API list responses also include ready `url`/`thumb_url` fields. Do **not** route through `getMediaUrl()` (it only rewrites `output/projects/...`) | No frontend path-rewrite needed |
| 8 | Detail view | Shared `AssetDetail` component, in-dialog + dedicated route `/asset/i/9f3ab21c` (catch-all `/asset/[...parts]`) opened via `window.open(..., "_blank")` | URL parity with the API scheme; satisfies "open in new window" |
| 9 | Project Library tab | Third tab in the references dialog: browse **all projects'** generated media (images, videos, narration, audio, backgrounds, references, editor files) in place and attach it as references — **no copying**. Refs from other projects can be added per-shot **and** to the project pool (one uniform pool, both ref shapes) | Reuses the existing per-project media serving routes (`projects.py:138-308`); no disk duplication; referencing the current project's own shots is allowed (e.g. style refs from earlier shots) |

**Trade-off accepted (per v2):** no tags/notes/upload-history. Listed metadata comes from the
filename + `os.stat` (size, modified/created); dimensions/duration are probed with ffprobe on
demand (detail view only). No "Rescan" feature is needed — editing folders in Explorer just works
as long as the `{id}-{title}` naming is kept.

---

## 2. On-disk layout

```
E:/output/
  Assets/                               # DEFAULT library root
    Images/
      Characters/
        9f3ab21c-Rainy Neon Street.png
        a1b2c3d4-Warrior Closeup.png
      Environments/
        City/
          77c0e1ab-Neon Alley.png
    Videos/
      Characters/
        b2f4d910-Entry Walk.mp4
    Audio/
      SFX/
        c3e5a822-Thunder Crack.wav
    Music/
      Epic/
        d4a7b633-Epic Battle Theme.mp3
    .thumbs/                            # generated thumbnails: i_9f3ab21c.jpg, ... (skipped in scans)
  projects/{project_id}/
    project_assets.json                 # project's asset pool (the only new JSON, project-scoped)
    shots.json                          # NEW field: reference_asset_ids per shot
```

Parsed entry (never stored — computed per request, with a per-folder mtime scan cache):

```json
{
  "ref": "i/9f3ab21c",
  "id": "9f3ab21c",
  "title": "Rainy Neon Street",
  "type": "image",
  "category": "Images/Characters",
  "filename": "9f3ab21c-Rainy Neon Street.png",
  "path": "output/Assets/Images/Characters/9f3ab21c-Rainy Neon Street.png",
  "url": "/api/assets/i/Characters/9f3ab21c",
  "thumb_url": "/api/assets/i/Characters/9f3ab21c/thumb",
  "size_bytes": 2048113,
  "modified_at": "2026-10-03T12:34:56Z"
}
```

**Project pool** `project_assets.json` (refs, ordered by add time; both ref shapes allowed):

```json
{ "version": 1, "assets": [
    { "ref": "i/9f3ab21c", "added_at": "2026-10-03T13:00:00Z" },
    { "ref": "p/project_20260927_125800/images/shot_001_001.png", "added_at": "2026-10-03T13:05:00Z" }
] }
```

**Type registry** — single backend constant (`config.py` or `asset_service.py`):

```python
ASSET_TYPES = {
    "i": {"folder": "Images", "type": "image"},
    "v": {"folder": "Videos", "type": "video"},
    "a": {"folder": "Audio",  "type": "audio"},
    "m": {"folder": "Music",  "type": "music"},
}
```

Top-level folders not in this map are ignored by the browser and flagged in the UI ("unrecognized
folder — rename to Images/Videos/Audio/Music").

---

## 3. Type → generation usage matrix

| Main category | Image generation | Video generation | Other |
|---|---|---|---|
| `Images` (i) | ✅ appended to `reference_images` (all modes) | ✅ first-frame / extra reference where the workflow supports it | — |
| `Videos` (v) | ❌ | ✅ FLFI2V meeting/departure sources; MiniMax H3 multi-video reference (workflow spike, §6) | editor clips |
| `Audio`/`Music` (a/m) | ❌ | ❌ (as direct gen input) | soundfx prompt context; timeline editor; final assembly |

The attach UI shows badges (`IMG`, `VID`, `SFX`) per reference indicating where it will be used,
but does **not** block attaching — the generation layer filters by type.

---

## 4. Backend

### 4.1 New / changed files

| File | Contents |
|---|---|
| `web_ui/backend/services/asset_service.py` | `AssetService` singleton: type map, filename parse/format helpers, per-folder mtime-cached scanning, category tree, upload (id mint + title de-dupe + MIME route), rename (title) / move (category) = file rename/move, delete, thumbnail cache (ffmpeg poster for videos), ref resolution — library `letter/id` → id-prefix scan, project `p/...` → `config.resolve_path` + existence check — plus project-media listing (scans a project's `images/videos/narration/audio/backgrounds/references/editor` dirs), libraries from config |
| `web_ui/backend/api/assets.py` | Routers below; registered in `main.py:130-135` |
| `web_ui/backend/models/shot.py` | add `reference_asset_ids: Optional[List[str]] = []` (models/shot.py:9-52) |
| `config.py` | `ASSET_LIBRARY_DIRS` (default `"output/Assets"`), parsed into a list; `ASSET_TYPES` map |

### 4.2 Endpoints

**Settings**

| Method & path | Purpose |
|---|---|
| `GET /api/assets/libraries` | configured roots (exists check, default flag) |
| `POST /api/assets/libraries` | replace/append list → persists `ASSET_LIBRARY_DIRS` via `update_env_config` (`core/config_utils.py:180`) + live `setattr`/`os.environ` reload |

**Browse**

| Method & path | Purpose |
|---|---|
| `GET /api/assets/tree?library=` | category tree with recursive counts (only recognized top-level folders) |
| `GET /api/assets/list?library=&cat=i/characters&q=&type=` | entries in one category (parsed from filenames + stat) |
| `GET /api/assets/search?library=&q=` | recursive title search |
| `GET /api/assets/entry?ref=i/9f3ab21c` | one entry + on-demand ffprobe dims/duration |
| `GET /api/assets/projects` | all projects for the Project Library tab (id, title/idea, thumbnail, per-type media counts) — may delegate to the existing `GET /api/projects` list (projects.py:33) |
| `GET /api/assets/projects/{pid}/media?type=` | grouped media entries of one project (`{type, filename, url, size, modified}`), scanning its media dirs (superset of `GET /api/editor/assets/{pid}`, editor.py:82-124) |

**Mutations** (all operate on files; id never changes)

| Method & path | Purpose |
|---|---|
| `POST /api/assets/upload` | multipart `files[]` + `cat=i/characters`. Mint id, sanitize title (Windows-illegal chars stripped), de-dupe title (` (2)` suffix), store `{id}-{title}{ext}`. If a file's MIME doesn't match the target main category, auto-route to the mirrored category under the correct type folder (create if missing) and say so in the response |
| `PUT /api/assets/rename` | `{ref, title}` → rename file in place |
| `PUT /api/assets/move` | `{ref, to_cat}` → move file to another category folder |
| `DELETE /api/assets/delete?ref=` | delete file; 409 with usage list if referenced by shots (then `force=true` strips refs) |
| `POST /api/assets/categories` | create nested category (mkdir) |
| `DELETE /api/assets/categories?cat=` | delete empty category folder |
| `POST /api/assets/adopt` | rename a non-conforming file (`myphoto.png` → `{minted_id}-myphoto.png`) — explicit action, never automatic |

**Serving (the requested scheme)**

| Method & path | Purpose |
|---|---|
| `GET /api/assets/{letter}/{category_path}/{id}` | FileResponse from the default library, e.g. `/api/assets/i/characters/9f3ab21c` → `Assets/Images/characters/9f3ab21c-*.png`. Category segments matched case-insensitively; file found by `{id}-` prefix scan of that folder |
| `GET /api/assets/{letter}/{category_path}/{id}/thumb` | cached thumbnail (`.thumbs/{letter}_{id}.jpg`; video poster via ffmpeg; audio/music → client-side icon tile, 404 here) |
| `GET /api/assets/by-id/{id}?letter=&library=` | reference resolution fallback: recursive `{id}-` scan of the matching main-category subtree (used by references when the category moved) |

Project refs (`p/...`) need **no new serving route** — they resolve onto the existing
`GET /api/projects/{pid}/{images|videos|narration|audio|editor|backgrounds|references}/{filename}`
FileResponse endpoints (projects.py:138-308).

**Project / shot attachment** (same file, explicit paths — follows existing URL shapes)

| Method & path | Purpose |
|---|---|
| `GET /api/projects/{pid}/assets` | project pool (resolved entries + `added_at`) |
| `POST /api/projects/{pid}/assets` | add `{refs: [...]}` to pool |
| `DELETE /api/projects/{pid}/assets/{ref}` | remove from pool (also strips from shots) |
| `GET /api/projects/{pid}/shots/{shot_id}/references` | resolved references for one shot |
| `PUT /api/projects/{pid}/shots/{shot_id}/references` | replace ordered list `{refs: [...]}` |
| `POST /api/projects/{pid}/shots/{shot_id}/references` | append `{refs: [...]}` |
| `DELETE /api/projects/{pid}/shots/{shot_id}/references/{ref}` | remove one |

Shot-reference mutations go through `ProjectManager.update_shots_safely` (project_manager.py:72);
pool mutations mirror that lock pattern on `project_assets.json`. `{refs: [...]}` payloads accept
both shapes (`i/9f3ab21c`, `p/{pid}/images/shot_001_001.png`); refs are validated as resolvable on
write and returned fully resolved (title, type, `url`, `thumb_url`, source label) on read.

---

## 5. Frontend

### 5.1 New files

| File | Contents |
|---|---|
| `src/app/assets/page.tsx` | Global Asset Library browser |
| `src/app/asset/[...parts]/page.tsx` | Standalone detail page for `/asset/i/9f3ab21c` (the "new window" target) |
| `src/components/assets/AssetLibraryBrowser.tsx` | Sidebar tree + breadcrumb + grid + toolbar (shared by the page and the dialog's Library tab) |
| `src/components/assets/AssetFolderTree.tsx` | Recursive tree (`ChevronRight/Down`, counts) |
| `src/components/assets/AssetCard.tsx` | Thumbnail tile, type/duration badges, checkbox overlay, hover actions |
| `src/components/assets/AssetDetail.tsx` | Large preview + rename/move/type actions (rename & move are file ops — fast) |
| `src/components/assets/UploadZone.tsx` | Dashed drag-drop zone + hidden input, multi-file (pattern from `CharacterReferenceUpload.tsx:293-365`) |
| `src/components/assets/ShotReferencesDialog.tsx` | Three-tab Radix dialog on each shot: Project Assets / Asset Library / Project Library |
| `src/hooks/useAssets.ts` | `useAssetLibraries`, `useAssetTree`, `useAssets(cat)`, `useUploadAssets`, `useProjectAssets`, `useShotReferences` + mutations (react-query, invalidate `['shots', projectId]` / `['project', projectId]` / `['assets', ...]`) |
| `src/services/api.ts` | typed methods for all §4.2 endpoints |

Modified: `src/app/layout.tsx:35-50` (nav link "Assets"), `src/types/index.ts` (`Asset`,
`Shot.reference_asset_ids`), `src/components/shots/ShotCard.tsx` (reference button).

### 5.2 Global `/assets` page

```
┌ Assets ─────────────────────────────────────────────────────────────┐
│ [🔍 Search]  [Type: All|Images|Videos|Audio|Music ▾]                │
│ [+ Upload] [+ New Category] [+ Add Folder]                          │
│ ┌────────────┬───────────────────────────────────────────────────┐  │
│ │▾ Default ▾ │ Assets / Images / Characters                      │  │
│ │ ▸ Images 32│ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐                │  │
│ │ ▸ Videos 8 │ │    │ │    │ │    │ │    │ │📁  │                │  │
│ │ ▸ Audio 12 │ └────┘ └────┘ └────┘ └────┘ └────┘                │  │
│ │ ▸ Music  5 │  title   title  title  title  Subcategory        │  │
│ │────────────│                                                   │  │
│ │ ▸ Stock Pk │  ☑ multi-select → floating bar:                     │  │
│ └────────────┘  [Add N to Project…] [Move] [Delete]                │  │
└─────────────────────────────────────────────────────────────────────┘
```

- Explorer feel: breadcrumb (`Assets / Images / Characters`), folder tiles for subcategories,
  asset grid (`grid-cols-2 md:3 lg:4 xl:5`), hover overlay actions.
- Click asset → `AssetDetail` dialog with **“Open in new window”** (`window.open('/asset/i/9f3ab21c')`).
- Multi-select = checkbox overlay (same as ShotGrid) → floating bulk bar (pill style of
  ShotGrid.tsx:879-932): *Add to Project…*, *Move to Category*, *Delete*.
- Last location remembered in `localStorage` (`assets_last_location`).
- Library-root address bar trick: the breadcrumb mirrors the URL — deep-linking
  `/assets#/i/characters` (or query state) restores the exact folder.

### 5.3 Shot integration

**ShotCard action row** (ShotCard.tsx:621-817) — one new compact icon button, copying the
variations-count badge pattern (ShotCard.tsx:774-785):

```tsx
<button onClick={() => setReferencesOpen(true)} title="References"
        className="p-1 hover:bg-sky-50 text-sky-600 rounded relative">
  <Paperclip className="w-4 h-4" />
  {(shot.reference_asset_ids?.length ?? 0) > 0 && (
    <span className="absolute -top-1 -right-1 bg-sky-500 text-white text-[9px] font-bold
                     rounded-full w-3.5 h-3.5 flex items-center justify-center">
      {shot.reference_asset_ids.length}
    </span>
  )}
</button>
```

**ShotReferencesDialog** (Radix `Dialog`, `max-w-5xl h-[85vh] flex flex-col p-0`, segmented tab
strip like the Media Gallery in the edit page, lines 1031-1046):

```
┌─ Shot 12 — References ──────────────────────────────────────────────┐
│ [ Project Assets (5) ] [ Asset Library ] [ Project Library ]    (x) │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ Project Library tab:                                           │  │
│ │ ┌ projects ──┐  ┌────┐ ┌────┐ ┌────┐ ┌────┐                    │  │
│ │ │● This (12) │  │img │ │vid │ │aud │ │img │  click → detail     │  │
│ │ │ Ocean (34) │  │ IMG│ │ VID│ │ SFX│ │ IMG│  (new window)       │  │
│ │ │ City (21)  │  └────┘ └────┘ └────┘ └────┘                    │  │
│ │ └────────────┘  filter: [All][Images][Videos][Audio/Music]     │  │
│ └────────────────────────────────────────────────────────────────┘  │
│  Project Assets tab:  ✓ = attached to this shot; click to toggle    │
│  Asset Library tab:   checkbox multi-select →                       │
│                       [Add 3 to Project Assets]  (+ Add to Shot)    │
│  Project Library tab: pick a project → its media grid; per-card     │
│                       [Add to Shot] (+ Add to Project Assets);      │
│                       cards carry a “from Project X” badge          │
└─────────────────────────────────────────────────────────────────────┘
```

- **Project Assets tab**: grid of the project pool, per-card attach toggle (`✓ Attached` /
  `+ Attach`), remove-from-project in hover overlay, type filter chips.
- **Asset Library tab**: `AssetLibraryBrowser` in compact mode, checkbox multi-select →
  “Add N to Project Assets”, plus optional direct “Add to Shot” (see open question #1).
- **Project Library tab**: left project list (thumbnail, title, per-type media counts; current
  project pinned first with a “this project” badge), right media grid of the selected project with
  type filter chips. Per-card “Add to Shot” / “Add to Project Assets”; multi-select bulk add like
  the other tabs. Project refs store the file path — nothing is copied, so if the source project
  later regenerates that media, the reference follows the same filename only if it still exists
  (regenerated variants get new filenames and are re-attachable in one click).
- Badge on the shot card updates immediately (mutation invalidates `['shots', projectId]`).

---

## 6. Generation integration (Phase 3)

### 6.1 Image generation — primary target

`generation_service.regenerate_shot_image` (generation_service.py:1468-1528) already collects a
`reference_images: List[str]` (character references) that flows into every backend:

- ComfyUI: first path → workflow `LoadImage` node (`comfyui_image_generator.py:164-173`);
  **must** copy the asset file into ComfyUI's input dir first via the existing
  `prepare_comfyui_input_image` helper (`core/prompt_compiler.py`) since ComfyUI runs as a
  separate process.
- GeminiWeb / Gemini API: every path is passed (`--reference-image` subprocess args,
  `geminiweb_image_generator.py:497-502`).

Change: after character references are collected, resolve the shot's `reference_asset_ids` —
library refs (`i/…`) via id-prefix scan, project refs (`p/…`) via `config.resolve_path` + existence
check — and append `image`-type assets. Priority: **shot references first** (user explicitly chose
them), then character references. Log which references were used and include them in the progress
payload so the UI can show “N references used”.

### 6.2 Video generation

- **FLFI2V shots**: video assets can be used as `meeting_video_path` / `departure_video_path`
  sources. UX: in the references dialog, a video asset on a FLFI2V shot gets a “Use as THEN/NOW
  source” action that writes the existing fields — explicit, not auto-magic.
- **MiniMax H3**: its `video_prompt` already references `<Picture 1> (from [Shot N])`. Passing
  additional *video file* references needs a workflow spike (does the h3 workflow expose extra
  reference nodes?). Deferred behind a spike task; the ordered reference list keeps room for roles
  later.

### 6.3 Audio / Music

Not generation inputs in Phase 3. They participate via soundfx generation prompt context (mood/
style hint from attached music), the timeline editor, and final assembly. Badged `SFX` in the UI.

---

## 7. Edge cases & guards

- **Filename parsing**: split on the **first** `-`; ids are dash-free hex so this is unambiguous.
  Files not matching `{id}-{title}{ext}` are listed as *unmanaged* (warning icon) with an
  “Adopt” action that renames them into the scheme — never automatic.
- **Title sanitization**: strip Windows-illegal chars `\ / : * ? " < > |`, trim trailing dots/
  spaces; title required (fallback `Untitled`); de-dupe with ` (2)` suffix on collision.
- **Case-insensitive category matching** in URLs (Windows filesystems are case-insensitive
  anyway; this keeps Linux deploys consistent).
- **Delete referenced asset**: scan projects' shots for the ref; 409 with usage list; `force=true`
  strips refs from shots + pools.
- **Broken refs**: a library asset deleted or renamed out of the scheme, or a referenced project
  deleted, fails resolution — the tile renders with a broken-link state + “Remove” action, and
  generation skips missing refs with a warning in the progress payload (never hard-fails the shot).
- **Project media display names**: derived from filename patterns (`shot_001_001.png` → “Shot 1
  image”, `thumbnail_16_9.png` → “Thumbnail 16:9”), falling back to the raw filename.
- **Auto-route on upload**: a video dropped into `Images/City` is saved to `Videos/City`
  (mirrored category created); response reports the reroute via toast.
- **Unknown top-level folders**: ignored by browse, flagged in UI.
- **Multiple libraries**: first entry in `ASSET_LIBRARY_DIRS` is the default (serves the pretty
  URLs); others addressed by slug prefix in refs and `?library=` in browse endpoints.
- **Thumbnails**: `.thumbs/{letter}_{id}.jpg` at library root, generated lazily (video poster via
  ffmpeg), never scanned as assets; audio/music tiles use a lucide icon.
- **Concurrency**: per-library `asyncio.Lock` for mutations; single id-mint check per upload batch.
- **Performance**: per-folder mtime scan cache; tree returns counts only; `by-id` resolution scans
  one main-category subtree (small).

---

## 8. Implementation phases

**Phase 1 — Library foundation (backend + `/assets` page)**
1. `config.py`: `ASSET_LIBRARY_DIRS` + `ASSET_TYPES`.
2. `services/asset_service.py`: parse/format helpers, scan cache, tree, upload/rename/move/delete,
   thumbs, ref resolution.
3. `api/assets.py` (browse/mutate/serve) + `main.py` registration + `libraries` settings endpoints.
4. Frontend: `/assets` page, `AssetLibraryBrowser`, `AssetFolderTree`, `AssetCard`, `AssetDetail`,
   `UploadZone`, `useAssets`, api methods, nav link.

**Phase 2 — Project assets & shot references**
1. `models/shot.py` + `src/types/index.ts`: `reference_asset_ids`.
2. `project_assets.json` handling + project/shot endpoints (§4.2); both ref shapes.
3. `ShotReferencesDialog` (three tabs incl. Project Library) + ShotCard paperclip button + hooks;
   project-media listing endpoints (`/api/assets/projects`, `/api/assets/projects/{pid}/media`).
4. `/asset/[...parts]` detail page for new-window opens (library + project refs).

**Phase 3 — Generation wiring**
1. Image: append resolved asset refs in `regenerate_shot_image`; ComfyUI input copy; progress payload.
2. Video: FLFI2V “use as THEN/NOW source” action; H3 multi-video spike.
3. Audio: soundfx prompt context (optional).

**Phase 4 — Polish**
Save-to-library from shot results / media gallery, tags later if ever needed (would require a
sidecar), drag-drop move in browser, editor `AssetBrowser` integration.

---

## 9. Open questions

1. **Direct attach from browse tabs** — should “Add to Shot” from the Asset Library / Project
   Library tabs be allowed directly (auto-adding to the project pool too), or must everything pass
   through Project Assets first? (Recommend: allow both; pool stays the source of truth.)
2. **Library folders setting** — manage via a small section on `/config` (recommended, matches
   existing settings flow) or a settings dialog inside the `/assets` page?
3. **Top-level category set** — fixed to `Images/Videos/Audio/Music` (recommended for now), or
   should the letter map be user-extendable (e.g. `Documents→d`)?
