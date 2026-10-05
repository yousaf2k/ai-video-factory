"""Smoke test for the /api/assets router (run: python tmp/test_assets_api.py)"""
import os
import sys
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

LIB1 = os.path.join(ROOT, "tmp", "asset_test_lib")
LIB2 = os.path.join(ROOT, "tmp", "asset_test_lib2")
os.environ["ASSET_LIBRARY_DIRS"] = f"{LIB1};{LIB2}"

import shutil
shutil.rmtree(LIB1, ignore_errors=True)
shutil.rmtree(LIB2, ignore_errors=True)

from fastapi.testclient import TestClient
from web_ui.backend.api.assets import router
from web_ui.backend.api import assets as assets_module
from web_ui.backend.api import projects as projects_module
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
app.include_router(assets_module.project_router)
app.include_router(projects_module.router)
client = TestClient(app)

# Phase 2: isolate projects dir (pool/shot-reference/media endpoints read it at call time)
import config
TMP_PROJECTS = os.path.join(ROOT, "tmp", "asset_test_projects")
shutil.rmtree(TMP_PROJECTS, ignore_errors=True)
os.makedirs(TMP_PROJECTS, exist_ok=True)
config.ABS_PROJECTS_DIR = TMP_PROJECTS
assets_module.project_service.project_manager.projects_dir = TMP_PROJECTS
# the projects router (media serving) has its own ProjectService instance
projects_module.project_service.project_manager.projects_dir = TMP_PROJECTS

import json


def make_project(pid, shots):
    pdir = os.path.join(TMP_PROJECTS, pid)
    os.makedirs(os.path.join(pdir, "images"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "videos"), exist_ok=True)
    with open(os.path.join(pdir, "shots.json"), "w", encoding="utf-8") as f:
        json.dump(shots, f)
    open(os.path.join(pdir, "images", "shot_001_001.png"), "wb").write(PNG_BYTES)
    open(os.path.join(pdir, "images", "shot_002_001.png"), "wb").write(PNG_BYTES)
    open(os.path.join(pdir, "videos", "shot_001_001.mp4"), "wb").write(b"0000ftypisom")

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d4944415478da63fcffff3f0300050201f34a24d500"
    "00000049454e44ae426082"
)

passed, failed = [], []


def check(name, cond, extra=""):
    (passed if cond else failed).append(name + (f"  {extra}" if extra and not cond else ""))


# --- libraries -------------------------------------------------------------
r = client.get("/api/assets/libraries")
check("libraries list", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code} {r.text[:200]}")
check("default library first", r.json()[0]["is_default"] and r.json()[0]["slug"] == "asset-test-lib", r.text[:200])

# --- upload images ---------------------------------------------------------
r = client.post("/api/assets/upload",
                files=[("files", ("rainy street.png", io.BytesIO(PNG_BYTES), "image/png")),
                       ("files", ("rainy   street?.png", io.BytesIO(PNG_BYTES + b"variant"), "image/png"))],
                data={"cat": "i/Characters/City"})
check("upload 200", r.status_code == 200, f"{r.status_code} {r.text[:300]}")
saved = r.json()["saved"]
check("upload saved 2", len(saved) == 2, r.text[:300])
check("upload skipped dup ext? no", len(r.json()["skipped"]) == 0)
e1, e2 = saved[0], saved[1]
check("entry fields", e1["letter"] == "i" and e1["type"] == "image" and e1["cat"] == "i/Characters/City", str(e1))
check("titles unique+sanitized", e1["title"] != e2["title"] and "?" not in e2["title"], str(e2["title"]))
check("url scheme", e1["url"].startswith("/api/assets/i/Characters/City/"), e1["url"])
ref1 = e1["ref"]
asset_id1 = e1["id"]

# --- auto-reroute video into image category --------------------------------
r = client.post("/api/assets/upload",
                files=[("files", ("clip.mp4", io.BytesIO(b"0000ftypisom"), "video/mp4"))],
                data={"cat": "i/Characters/City"})
check("upload reroute 200", r.status_code == 200, r.text[:300])
check("video rerouted to v/", r.json()["rerouted"] and r.json()["rerouted"][0]["to"].startswith("v/"), r.text[:300])
check("video saved under Videos", r.json()["saved"][0]["cat"].startswith("v/"), r.text[:300])

# --- tree / list -----------------------------------------------------------
r = client.get("/api/assets/tree")
check("tree 200", r.status_code == 200, r.text[:200])
images_node = next(n for n in r.json() if n["letter"] == "i")
city = next(c for c in images_node["children"] if c["name"] == "Characters")
check("tree has nested City", any(c["name"] == "City" for c in city["children"]), r.text[:400])

r = client.get("/api/assets/list", params={"cat": "I/CHARACTERS/CITY"})
check("list case-insensitive cat", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code} {r.text[:200]}")

# --- serving ----------------------------------------------------------------
r = client.get(e1["url"])
check("serve file", r.status_code == 200 and r.content == PNG_BYTES, f"{r.status_code} {len(r.content)}")
r = client.get(e1["url"].lower())
check("serve lowercase url", r.status_code == 200, f"{r.status_code}")
r = client.get(e1["url"] + "/thumb")
check("image thumb = original", r.status_code == 200 and r.content == PNG_BYTES)
r = client.get("/api/assets/i/nonexistent")
check("serve unknown id -> 404", r.status_code == 404, f"{r.status_code}")

# --- entry / search ----------------------------------------------------------
r = client.get("/api/assets/entry", params={"ref": ref1, "probe": "true"})
check("entry 200", r.status_code == 200 and r.json()["ref"] == ref1, r.text[:200])
check("entry probe has width", r.json().get("media", {}).get("width") == 1, r.text[:300])
r = client.get("/api/assets/search", params={"q": e1["title"][:6].lower()})
check("search finds", r.status_code == 200 and any(a["ref"] == ref1 for a in r.json()), r.text[:200])

# --- rename / move -----------------------------------------------------------
r = client.put("/api/assets/rename", json={"ref": ref1, "title": 'Renamed: "Title" <2>'})
check("rename 200", r.status_code == 200, f"{r.status_code} {r.text[:300]}")
check("rename sanitized", r.json()["title"] == "Renamed Title 2", r.text[:200])
new_url = r.json()["url"]
r = client.get(new_url)
check("serve after rename (same id)", r.status_code == 200 and r.content == PNG_BYTES)

r = client.put("/api/assets/move", json={"ref": ref1, "to_cat": "i/Environments"})
check("move 200", r.status_code == 200 and r.json()["cat"] == "i/Environments", f"{r.status_code} {r.text[:300]}")
r = client.get("/api/assets/i/Environments/" + asset_id1)
check("serve after move", r.status_code == 200, f"{r.status_code}")
r = client.put("/api/assets/move", json={"ref": ref1, "to_cat": "v/Environments"})
check("cross-type move rejected", r.status_code == 400, f"{r.status_code}")

# --- categories ---------------------------------------------------------------
r = client.post("/api/assets/categories", json={"cat": "i/Environments", "name": "Forest"})
check("create category", r.status_code == 200 and r.json()["cat"] == "i/Environments/Forest", r.text[:200])
r = client.delete("/api/assets/categories", params={"cat": "i/Environments/Forest"})
check("delete empty category", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
r = client.delete("/api/assets/categories", params={"cat": "i/Environments"})
check("delete non-empty category rejected (409 + stats)", r.status_code == 409 and r.json()["detail"]["assets"] >= 1,
      f"{r.status_code} {r.text[:200]}")
r = client.delete("/api/assets/categories", params={"cat": "i"})
check("delete type root rejected", r.status_code == 400, f"{r.status_code}")

# --- adopt --------------------------------------------------------------------
r = client.post("/api/assets/upload",
                files=[("files", ("raw photo.png", io.BytesIO(PNG_BYTES), "image/png"))],
                data={"cat": "i/Raw"})
# manually break the scheme: rename the saved file to a non-scheme name
saved_raw = r.json()["saved"][0]
raw_dir = os.path.join(LIB1, "Images", "Raw")
raw_file = os.path.join(raw_dir, saved_raw["filename"])
os.rename(raw_file, os.path.join(raw_dir, "unmanaged.png"))
r = client.get("/api/assets/list", params={"cat": "i/Raw"})
check("unmanaged file excluded from list", len(r.json()) == 0, r.text[:200])
r = client.post("/api/assets/adopt", json={"ref_path": "i/Raw/unmanaged.png"})
check("adopt 200", r.status_code == 200, f"{r.status_code} {r.text[:300]}")
check("adopted into scheme", r.json().get("title") == "unmanaged", r.text[:200])
adopted_ref = r.json()["ref"] if r.status_code == 200 else None

# --- delete ---------------------------------------------------------------------
r = client.delete("/api/assets/delete", params={"ref": adopted_ref})
check("delete 200", r.status_code == 200 and r.json()["deleted"] is True, f"{r.status_code} {r.text[:200]}")
r = client.delete("/api/assets/delete", params={"ref": "i/12345678"})
check("delete unknown -> 404", r.status_code == 404, f"{r.status_code}")

# --- category move / rename / force delete --------------------------------------
from urllib.parse import quote

r = client.post("/api/assets/categories", json={"cat": "i", "name": "MoveSrc"})
check("create MoveSrc", r.status_code == 200, r.text[:200])
r = client.post("/api/assets/categories", json={"cat": "i", "name": "MoveDst"})
r = client.post("/api/assets/upload",
                files=[("files", ("cat test.png", io.BytesIO(PNG_BYTES), "image/png"))],
                data={"cat": "i/MoveSrc"})
moved_entry = r.json()["saved"][0]
old_url = moved_entry["url"]

r = client.put("/api/assets/categories/move", json={"cat": "i/MoveSrc", "to_parent": "i/MoveDst"})
check("move category 200", r.status_code == 200 and r.json()["new_cat"] == "i/MoveDst/MoveSrc",
      f"{r.status_code} {r.text[:200]}")
r = client.get(old_url)
check("old asset url gone after category move", r.status_code == 404, f"{r.status_code}")
r = client.get(f"/api/assets/i/MoveDst/MoveSrc/{moved_entry['id']}")
check("asset served at new category path", r.status_code == 200 and r.content == PNG_BYTES, f"{r.status_code}")
r = client.get("/api/assets/list", params={"cat": "i/MoveDst/MoveSrc"})
check("list sees moved category assets", r.status_code == 200 and len(r.json()) == 1, r.text[:200])

r = client.put("/api/assets/categories/rename", json={"cat": "i/MoveDst/MoveSrc", "name": "Renamed Cat"})
check("rename category 200", r.status_code == 200 and r.json()["new_cat"] == "i/MoveDst/Renamed Cat",
      f"{r.status_code} {r.text[:200]}")
r = client.get(quote(f"/api/assets/i/MoveDst/Renamed Cat/{moved_entry['id']}"))
check("serve after category rename", r.status_code == 200 and r.content == PNG_BYTES, f"{r.status_code}")

r = client.put("/api/assets/categories/move", json={"cat": "i/MoveDst", "to_parent": "i/MoveDst/Renamed Cat"})
check("move into own subcategory rejected", r.status_code == 400, f"{r.status_code}")
r = client.put("/api/assets/categories/move", json={"cat": "i/MoveDst/Renamed Cat", "to_parent": "v"})
check("cross-type category move rejected", r.status_code == 400, f"{r.status_code}")
r = client.put("/api/assets/categories/move", json={"cat": "i/MoveDst/Renamed Cat", "to_parent": "i/MoveDst"})
check("move onto same path rejected", r.status_code == 400, f"{r.status_code}")
r = client.post("/api/assets/categories", json={"cat": "i", "name": "Clash"})
r = client.post("/api/assets/categories", json={"cat": "i/Clash", "name": "Renamed Cat"})
r = client.put("/api/assets/categories/move", json={"cat": "i/MoveDst/Renamed Cat", "to_parent": "i/Clash"})
check("move onto existing category rejected", r.status_code == 400, f"{r.status_code}")
r = client.put("/api/assets/categories/rename", json={"cat": "i", "name": "Nope"})
check("rename type root rejected", r.status_code == 400, f"{r.status_code}")

r = client.delete("/api/assets/categories", params={"cat": "i/MoveDst"})
check("delete non-empty -> 409", r.status_code == 409, f"{r.status_code} {r.text[:200]}")
r = client.delete("/api/assets/categories", params={"cat": "i/MoveDst", "force": "true"})
check("force delete non-empty", r.status_code == 200 and r.json()["deleted"] is True and r.json()["assets"] == 1,
      f"{r.status_code} {r.text[:200]}")
check("folder really gone", not os.path.isdir(os.path.join(LIB1, "Images", "MoveDst")))
r = client.delete("/api/assets/categories", params={"cat": "i/Clash/Renamed Cat"})
check("delete empty nested category", r.status_code == 200 and r.json()["deleted"] is True, f"{r.status_code} {r.text[:200]}")
check("parent category kept after subcategory delete", os.path.isdir(os.path.join(LIB1, "Images", "Clash")))

# --- Phase 2: project media, pool, shot references -------------------------------
make_project("proj_a", [
    {"id": "aaaa0001", "index": 1, "image_prompt": "a", "motion_prompt": "m", "camera": "pan", "narration": ""},
    {"id": "aaaa0002", "index": 2, "image_prompt": "b", "motion_prompt": "m", "camera": "pan", "narration": ""},
])
make_project("proj_b", [
    {"id": "bbbb0001", "index": 1, "image_prompt": "c", "motion_prompt": "m", "camera": "pan", "narration": ""},
])

proj_img_ref = "p/proj_a/images/shot_001_001.png"

r = client.get("/api/assets/projects/proj_a/media")
check("project media listing", r.status_code == 200 and len(r.json()) == 3, f"{r.status_code} {r.text[:300]}")
titles = {e["title"] for e in r.json()}
check("pretty media titles", {"Shot 1 image", "Shot 2 image", "Shot 1 video"} <= titles, str(titles))
img_entry = next(e for e in r.json() if e["ref"] == proj_img_ref)
check("project ref url/type", img_entry["url"] == "/api/projects/proj_a/images/shot_001_001.png" and img_entry["type"] == "image", str(img_entry))
r = client.get(img_entry["url"])
check("serve project media via existing route", r.status_code == 200 and r.content == PNG_BYTES, f"{r.status_code}")

r = client.get("/api/assets/entry", params={"ref": proj_img_ref, "probe": "true"})
check("entry resolves project ref", r.status_code == 200 and r.json()["kind"] == "project" and r.json()["exists"] is True, r.text[:200])
r = client.get("/api/assets/entry", params={"ref": "p/proj_a/images/missing.png"})
check("missing project ref exists=false", r.status_code == 200 and r.json()["exists"] is False, r.text[:200])

r = client.post("/api/projects/proj_b/assets", json={"refs": [ref1, proj_img_ref]})
check("add to pool", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code} {r.text[:300]}")
check("pool resolved kinds", {e["kind"] for e in r.json()} == {"library", "project"}, r.text[:200])
r = client.post("/api/projects/proj_b/assets", json={"refs": [ref1]})
check("pool dedupes", r.status_code == 200 and len(r.json()) == 2)
r = client.post("/api/projects/proj_b/assets", json={"refs": ["i/00000000"]})
check("pool bad ref -> 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")
r = client.get("/api/projects/proj_b/assets")
check("get pool with added_at", r.status_code == 200 and len(r.json()) == 2 and r.json()[0]["added_at"], r.text[:200])

r = client.put("/api/projects/proj_b/shots/bbbb0001/references", json={"refs": [proj_img_ref, ref1]})
check("set shot refs", r.status_code == 200 and [e["ref"] for e in r.json()] == [proj_img_ref, ref1], f"{r.status_code} {r.text[:300]}")
with open(os.path.join(TMP_PROJECTS, "proj_b", "shots.json"), encoding="utf-8") as f:
    shot_on_disk = json.load(f)[0]
check("refs persisted ordered", shot_on_disk.get("reference_asset_ids") == [proj_img_ref, ref1], str(shot_on_disk.get("reference_asset_ids")))
r = client.post("/api/projects/proj_b/shots/1/references", json={"refs": ["p/proj_a/videos/shot_001_001.mp4"]})
check("append ref by index", r.status_code == 200 and len(r.json()) == 3, f"{r.status_code} {r.text[:300]}")
r = client.post("/api/projects/proj_b/shots/1/references", json={"refs": ["p/proj_a/videos/shot_001_001.mp4"]})
check("append dedupes", len(r.json()) == 3)
r = client.delete(f"/api/projects/proj_b/shots/1/references/{quote(ref1)}")
check("remove one ref", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code} {r.text[:200]}")
r = client.put("/api/projects/proj_b/shots/bbbb0001/references", json={"refs": ["i/00000000"]})
check("set refs bad -> 400", r.status_code == 400, f"{r.status_code}")
r = client.get("/api/projects/proj_b/shots/zzzz/references")
check("unknown shot -> 404", r.status_code == 404, f"{r.status_code}")

r = client.delete(f"/api/projects/proj_b/assets/{quote(proj_img_ref)}")
check("remove from pool", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
r = client.get("/api/projects/proj_b/shots/bbbb0001/references")
check("strip removed ref from shot", all(e["ref"] != proj_img_ref for e in r.json()), r.text[:300])
r = client.get("/api/projects/proj_b/assets")
check("pool now has 1", len(r.json()) == 1)
r = client.get("/api/projects/does_not_exist/assets")
check("unknown project -> 404", r.status_code == 404, f"{r.status_code}")

# --- Phase 3: generation reference collection + use-as-source ---------------------
from web_ui.backend.services.asset_service import get_asset_service
svc = get_asset_service()

# upload a video asset to the library for the use-as-source test
r = client.post("/api/assets/upload",
                files=[("files", ("entry walk.mp4", io.BytesIO(b"0000ftypisom"), "video/mp4"))],
                data={"cat": "v/Characters"})
vid_entry = r.json()["saved"][0]
vid_ref = vid_entry["ref"]
vid_path = svc.get_entry(vid_ref)["path"]

r = client.post("/api/assets/upload",
                files=[("files", ("broken ref.png", io.BytesIO(PNG_BYTES), "image/png"))],
                data={"cat": "i/Characters"})
broken_entry = r.json()["saved"][0]
os.remove(svc.get_entry(broken_entry["ref"])["path"])  # make it missing on disk

r = client.post("/api/projects/proj_b/assets", json={"refs": [vid_ref]})
check("pool accepts video ref", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code} {r.text[:200]}")
r = client.post("/api/projects/proj_b/assets", json={"refs": [broken_entry["ref"]]})
check("pool rejects already-missing ref", r.status_code == 400, f"{r.status_code}")

# collect_shot_image_refs: image-type only, ordered, skips missing (broken refs can
# appear when a file is deleted after attaching — validated on write, not forever)
r = client.put("/api/projects/proj_b/shots/bbbb0001/references",
               json={"refs": [ref1, vid_ref, proj_img_ref]})
check("set mixed refs", r.status_code == 200 and len(r.json()) == 3, f"{r.status_code} {r.text[:300]}")
paths = svc.collect_shot_image_refs({"reference_asset_ids": [ref1, vid_ref, "i/deadbeef", proj_img_ref]})
check("collect returns image refs ordered", len(paths) == 2 and paths[0].endswith(".png") and os.path.isfile(paths[0]), str(paths))
check("collect includes project ref path", any(p.endswith("shot_001_001.png") and "proj_a" in p for p in paths), str(paths))
check("collect empty for no refs", svc.collect_shot_image_refs({}) == [])

# use-as-source endpoint
r = client.post("/api/projects/proj_b/shots/bbbb0001/references/use-as-source",
                json={"ref": vid_ref, "slot": "then"})
check("use-as-source 200", r.status_code == 200 and r.json()["field"] == "meeting_video_path", f"{r.status_code} {r.text[:300]}")
with open(os.path.join(TMP_PROJECTS, "proj_b", "shots.json"), encoding="utf-8") as f:
    s = json.load(f)[0]
resolved_meeting = config.resolve_path(s.get("meeting_video_path"))
check("meeting path set + resolvable",
      os.path.normpath(resolved_meeting).lower() == os.path.normpath(vid_path).lower()
      and os.path.isfile(resolved_meeting), str(s.get("meeting_video_path")))
check("meeting rendered flag set", s.get("meeting_video_rendered") is True)
r = client.post("/api/projects/proj_b/shots/bbbb0001/references/use-as-source",
                json={"ref": vid_ref, "slot": "later"})
check("bad slot -> 400", r.status_code == 400, f"{r.status_code}")
r = client.post("/api/projects/proj_b/shots/bbbb0001/references/use-as-source",
                json={"ref": ref1, "slot": "now"})
check("image ref as source -> 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")
r = client.post("/api/projects/proj_b/shots/bbbb0001/references/use-as-source",
                json={"ref": "p/proj_a/videos/shot_001_001.mp4", "slot": "now"})
check("project video ref as source", r.status_code == 200 and r.json()["field"] == "departure_video_path", f"{r.status_code} {r.text[:200]}")

# --- Phase 4: import (save-to-library) + content dedup ---------------------------
r = client.post("/api/assets/import", json={"ref": proj_img_ref, "cat": "i/Imported", "title": "Imported Shot"})
check("import project media", r.status_code == 200 and len(r.json()["saved"]) == 1, f"{r.status_code} {r.text[:300]}")
imp = r.json()["saved"][0]
check("import title honored", imp["title"] == "Imported Shot", str(imp))
check("import file exists", os.path.isfile(os.path.join(LIB1, "Images", "Imported", imp["filename"])))

r = client.post("/api/assets/import", json={"ref": proj_img_ref, "cat": "i/Imported"})
check("import duplicate skipped", r.status_code == 200 and len(r.json()["saved"]) == 0
      and "Duplicate of" in r.json()["skipped"][0]["reason"], r.text[:300])
check("no duplicate file on disk", len([f for f in os.listdir(os.path.join(LIB1, "Images", "Imported"))]) == 1)

r = client.post("/api/assets/upload",
                files=[("files", ("same as imported.png", io.BytesIO(PNG_BYTES), "image/png"))],
                data={"cat": "i/Imported"})
check("upload duplicate skipped", r.status_code == 200 and len(r.json()["saved"]) == 0
      and "Duplicate of" in r.json()["skipped"][0]["reason"], r.text[:300])
r = client.post("/api/assets/upload",
                files=[("files", ("different file.png", io.BytesIO(PNG_BYTES + b"x"), "image/png"))],
                data={"cat": "i/Imported"})
check("different content not skipped", r.status_code == 200 and len(r.json()["saved"]) == 1, r.text[:300])
r = client.post("/api/assets/import", json={"ref": "p/proj_a/images/missing.png", "cat": "i"})
check("import missing ref -> 404", r.status_code == 404, f"{r.status_code}")

# --- Guides (text) assets ----------------------------------------------------
MD_CONTENT = "# Setup Guide\n\nRun `npm install`.\n"
r = client.post("/api/assets/upload",
                files=[("files", ("setup guide.md", io.BytesIO(MD_CONTENT.encode("utf-8")), "text/markdown"))],
                data={"cat": "g/Setup"})
check("guides upload 200", r.status_code == 200, f"{r.status_code} {r.text[:300]}")
g_saved = r.json()["saved"]
check("guides saved 1", len(g_saved) == 1, r.text[:300])
g_entry = g_saved[0]
check("guides entry type text", g_entry["letter"] == "g" and g_entry["type"] == "text"
      and g_entry["cat"] == "g/Setup" and g_entry["ext"] == "md", str(g_entry))
check("guides no thumb_url", g_entry["thumb_url"] is None, str(g_entry.get("thumb_url")))
r = client.get("/api/assets/tree")
check("tree has Guides root", any(n["letter"] == "g" and n["name"] == "Guides" for n in r.json()), r.text[:300])
r = client.get("/api/assets/content", params={"ref": g_entry["ref"]})
check("guides content", r.status_code == 200 and r.json()["content"] == MD_CONTENT
      and r.json()["title"] == "setup guide" and r.json()["ext"] == "md", r.text[:300])
r = client.get(g_entry["url"])
check("guides file served", r.status_code == 200 and "Setup Guide" in r.text, f"{r.status_code}")
r = client.get(g_entry["url"] + "/thumb")
check("guides thumb -> 404", r.status_code == 404, f"{r.status_code}")
r = client.get("/api/assets/content", params={"ref": e1["ref"]})
check("content of image -> 400", r.status_code == 400, f"{r.status_code}")
r = client.post("/api/assets/upload",
                files=[("files", ("script.py", io.BytesIO(b"print(1)"), "text/plain"))],
                data={"cat": "g"})
check("unsupported text ext skipped", r.status_code == 200 and len(r.json()["saved"]) == 0, r.text[:200])

# --- Generate into the library ------------------------------------------------
# The generation runs as an asyncio task on the app's loop, so these tests use a
# context-managed TestClient (single long-lived loop) and monkeypatch the runners.
import time
from web_ui.backend.services import asset_generation as ag_module

async def _fake_run_image(self, gen):
    self._set(gen, progress=50)
    with open(gen["path"], "wb") as f:
        f.write(PNG_BYTES)

ag_module.AssetGenerationService._run_image = _fake_run_image

with TestClient(app) as gclient:
    r = gclient.get("/api/assets/generate/options")
    check("generate options 200", r.status_code == 200 and "aspect_ratios" in r.json(), f"{r.status_code}")

    r = gclient.post("/api/assets/generate",
                     json={"kind": "image", "prompt": "a red cube on marble", "cat": "i/Generated"})
    check("generate image 200", r.status_code == 200, f"{r.status_code} {r.text[:300]}")
    gen = r.json() if r.status_code == 200 else {}
    gid = gen.get("id", "")
    check("generate initial status", gen.get("status") in ("queued", "running"), str(gen))
    for _ in range(60):
        r = gclient.get(f"/api/assets/generate/{gid}")
        if r.status_code == 200 and r.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    check("generate image completed", r.status_code == 200 and r.json()["status"] == "completed", r.text[:300])
    gref = r.json().get("ref", "")
    check("generate entry ref", gref.startswith("i/"), gref)
    if gref:
        r = gclient.get(r.json()["url"])
        check("generated file served", r.status_code == 200 and r.content == PNG_BYTES, f"{r.status_code}")
        r = gclient.get("/api/assets/list", params={"cat": "i/Generated"})
        check("generated file listed", r.status_code == 200 and len(r.json()) == 1, r.text[:200])

    # Validation errors
    r = gclient.post("/api/assets/generate", json={"kind": "image", "prompt": "   "})
    check("generate empty prompt -> 400", r.status_code == 400, f"{r.status_code}")
    r = gclient.post("/api/assets/generate", json={"kind": "video", "prompt": "x", "cat": "i/Nope", "image_ref": "i/abc"})
    check("generate video wrong cat -> 400", r.status_code == 400, f"{r.status_code}")
    r = gclient.post("/api/assets/generate", json={"kind": "video", "prompt": "x", "cat": "v"})
    check("generate video missing image_ref -> 400", r.status_code == 400, f"{r.status_code}")
    r = gclient.post("/api/assets/generate", json={"kind": "audio", "prompt": "x", "cat": "a"})
    check("generate audio missing video_ref -> 400", r.status_code == 400, f"{r.status_code}")
    r = gclient.post("/api/assets/generate", json={"kind": "music", "prompt": "x"})
    check("generate bogus kind -> 400", r.status_code == 400, f"{r.status_code}")

    # Failure path: runner raises, partial file is cleaned up
    async def _failing_run_video(self, gen):
        with open(gen["path"], "wb") as f:
            f.write(b"partial")
        raise RuntimeError("boom")

    ag_module.AssetGenerationService._run_video = _failing_run_video
    vdir = os.path.join(LIB1, "Videos")
    files_before = set()
    for root, _dirs, files in os.walk(vdir):
        files_before.update(files)
    r = gclient.post("/api/assets/generate",
                     json={"kind": "video", "prompt": "fly over city", "cat": "v", "image_ref": e1["ref"]})
    check("generate video started", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    vid = r.json().get("id", "")
    for _ in range(60):
        r = gclient.get(f"/api/assets/generate/{vid}")
        if r.status_code == 200 and r.json()["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.05)
    check("generate video failed", r.status_code == 200 and r.json()["status"] == "failed"
          and "boom" in (r.json().get("error") or ""), r.text[:300])
    files_after = set()
    for root, _dirs, files in os.walk(vdir):
        files_after.update(files)
    check("failed video leaves no partial file", files_after == files_before, str(files_after - files_before))

    r = gclient.get("/api/assets/generate")
    check("generate list", r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 2, r.text[:200])
    r = gclient.delete(f"/api/assets/generate/{gid}")
    check("cancel finished is noop", r.status_code == 200 and r.json()["status"] == "completed", r.text[:200])

print("PASSED:", len(passed))
for p in passed:
    print("  ok:", p)
print("FAILED:", len(failed))
for f in failed:
    print("  FAIL:", f)
sys.exit(1 if failed else 0)
