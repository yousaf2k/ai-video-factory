"""
Assets API endpoints

Library browsing/mutation plus the file-serving URL scheme:
    GET /api/assets/{letter}/{category_path}/{id}        -> the asset file
    GET /api/assets/{letter}/{category_path}/{id}/thumb  -> cached thumbnail
where letter is the type alias from config.ASSET_TYPES (i/v/a/m).

A second router (no prefix) hosts the per-project asset pool and per-shot
reference endpoints under the existing /api/projects/... URL shapes.
"""
import json
import os
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse

import config
from core.config_utils import update_env_config
from web_ui.backend.models.asset import (
    AssetEntry, AssetLibraryInfo, AssetTreeNode, UploadResult, ResolvedAssetRef,
    RenameAssetRequest, MoveAssetRequest, AdoptAssetRequest,
    CreateCategoryRequest, MoveCategoryRequest, RenameCategoryRequest,
    UpdateLibrariesRequest, UpdateRefsRequest, UseAsSourceRequest, ImportAssetRequest,
)
from web_ui.backend.services.asset_service import get_asset_service
from web_ui.backend.services.project_service import ProjectService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assets", tags=["assets"])
project_router = APIRouter(tags=["assets"])

asset_service = get_asset_service()
project_service = ProjectService()


def _http_error(e: Exception) -> HTTPException:
    if isinstance(e, FileNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if isinstance(e, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    logger.error(f"Asset API error: {e}", exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Asset operation failed: {str(e)}"
    )


# ------------------------------------------------------------------
# Libraries (multiple asset folders, persisted in .env ASSET_LIBRARY_DIRS)
# ------------------------------------------------------------------

@router.get("/libraries", response_model=List[AssetLibraryInfo])
async def list_libraries():
    return asset_service.list_libraries()


@router.post("/libraries", response_model=List[AssetLibraryInfo])
async def update_libraries(request: UpdateLibrariesRequest):
    """Replace the configured asset library folders (first = default)."""
    paths = []
    for raw in request.paths:
        path = raw.strip().strip('"')
        if not path:
            continue
        paths.append(config.resolve_path(path))
    if not paths:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one library folder is required")
    try:
        for path in paths:
            os.makedirs(path, exist_ok=True)
        joined = ";".join(paths)
        update_env_config({"ASSET_LIBRARY_DIRS": joined}, env_path=os.path.join(config.PROJECT_ROOT, ".env"))
        os.environ["ASSET_LIBRARY_DIRS"] = joined
        return asset_service.list_libraries()
    except Exception as e:
        raise _http_error(e)


# ------------------------------------------------------------------
# Browse
# ------------------------------------------------------------------

@router.get("/tree", response_model=List[AssetTreeNode])
async def get_tree(library: Optional[str] = None):
    try:
        return asset_service.get_tree(library)
    except Exception as e:
        raise _http_error(e)


@router.get("/list", response_model=List[AssetEntry])
async def list_assets(
    cat: str = Query(..., description='Category, e.g. "i/Characters"'),
    library: Optional[str] = None,
):
    try:
        return asset_service.list_category(cat, library)
    except Exception as e:
        raise _http_error(e)


@router.get("/search", response_model=List[AssetEntry])
async def search_assets(
    q: str = Query(..., min_length=1),
    library: Optional[str] = None,
    type: Optional[str] = Query(None, description="Filter by asset type: image/video/audio/music"),
):
    try:
        results = asset_service.list_all(library)
        needle = q.lower()
        return [a for a in results if needle in a["title"].lower() or needle in a["filename"].lower()]
    except Exception as e:
        raise _http_error(e)


@router.get("/entry")
async def get_entry(ref: str = Query(..., description='Asset ref: "i/9f3ab21c" (library) or "p/{project_id}/{media_dir}/{filename}" (project media)'), probe: bool = False):
    try:
        if ref.startswith("p/"):
            return asset_service.resolve_ref(ref, probe=probe)
        return asset_service.get_entry(ref, probe=probe)
    except Exception as e:
        raise _http_error(e)


@router.get("/projects/{project_id}/media", response_model=List[ResolvedAssetRef])
async def get_project_media(project_id: str):
    """All media files of one project as attachable asset entries (Project Library tab)."""
    try:
        return asset_service.list_project_media(project_id)
    except Exception as e:
        raise _http_error(e)


# ------------------------------------------------------------------
# Mutations
# ------------------------------------------------------------------

@router.post("/upload", response_model=UploadResult)
async def upload_assets(
    files: List[UploadFile] = File(...),
    cat: str = Form(..., description='Target category, e.g. "i/Characters"'),
    library: Optional[str] = Form(None),
):
    try:
        payloads = [(f.filename or "untitled", f.file) for f in files]
        return asset_service.upload(payloads, cat, library)
    except Exception as e:
        raise _http_error(e)


@router.post("/import", response_model=UploadResult)
async def import_asset(request: ImportAssetRequest):
    """Copy an existing media file into the library (save-to-library).
    `ref` may be a project-media ref ("p/{pid}/{dir}/{filename}") or a library ref
    (copies across categories). Content duplicates in the target category are skipped."""
    try:
        entry = asset_service.resolve_ref(request.ref)
        if not entry.get("exists") or not entry.get("path"):
            raise FileNotFoundError(f"Source not found: {request.ref}")
        result = asset_service.import_file(entry["path"], request.cat, request.title, request.library)
        return result
    except Exception as e:
        raise _http_error(e)


@router.put("/rename", response_model=AssetEntry)
async def rename_asset(request: RenameAssetRequest):
    try:
        return asset_service.rename(request.ref, request.title)
    except Exception as e:
        raise _http_error(e)


@router.put("/move", response_model=AssetEntry)
async def move_asset(request: MoveAssetRequest):
    try:
        return asset_service.move(request.ref, request.to_cat)
    except Exception as e:
        raise _http_error(e)


@router.delete("/delete")
async def delete_asset(
    ref: str = Query(...),
    force: bool = Query(False, description="Delete even if referenced by shots (strips the references)"),
):
    try:
        result = asset_service.delete(ref, force)
        if not result.get("deleted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Asset is referenced by shots", "projects": result.get("usage", [])},
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise _http_error(e)


@router.post("/categories")
async def create_category(request: CreateCategoryRequest):
    try:
        return asset_service.create_category(request.cat, request.name, request.library)
    except Exception as e:
        raise _http_error(e)


@router.delete("/categories")
async def delete_category(
    cat: str = Query(...),
    force: bool = Query(False, description="Recursively delete even if the category contains assets/subcategories"),
    library: Optional[str] = None,
):
    try:
        result = asset_service.delete_category(cat, library, force)
        if not result.get("deleted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Category is not empty",
                    "cat": result.get("cat"),
                    "assets": result.get("assets", 0),
                    "subcategories": result.get("subcategories", 0),
                },
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise _http_error(e)


@router.put("/categories/move")
async def move_category(request: MoveCategoryRequest):
    """Move a category (and everything in it) under a new parent, e.g.
    i/Characters/City -> i/Environments/City."""
    try:
        return asset_service.move_category(request.cat, request.to_parent, request.library)
    except Exception as e:
        raise _http_error(e)


@router.put("/categories/rename")
async def rename_category(request: RenameCategoryRequest):
    try:
        return asset_service.rename_category(request.cat, request.name, request.library)
    except Exception as e:
        raise _http_error(e)


@router.post("/adopt", response_model=AssetEntry)
async def adopt_asset(request: AdoptAssetRequest):
    """Rename a non-scheme file (e.g. "i/Characters/myphoto.png") into {id}-{Title}.ext."""
    try:
        return asset_service.adopt(request.ref_path, request.library)
    except Exception as e:
        raise _http_error(e)


# ------------------------------------------------------------------
# File serving (the /api/assets/{letter}/.../{id} URL scheme)
# NOTE: thumb routes must be registered before the plain file routes —
# the {category_path:path} converter would otherwise swallow "/thumb".
# ------------------------------------------------------------------

@router.get("/{letter}/{category_path:path}/{asset_id}/thumb", response_class=FileResponse)
async def get_asset_thumb(letter: str, asset_id: str, category_path: str = "", library: Optional[str] = None):
    try:
        thumb_path = asset_service.get_thumb(letter, category_path, asset_id, library)
        return FileResponse(thumb_path)
    except HTTPException:
        raise
    except Exception as e:
        raise _http_error(e)


@router.get("/{letter}/{asset_id}/thumb", response_class=FileResponse)
async def get_asset_thumb_root(letter: str, asset_id: str, library: Optional[str] = None):
    return await get_asset_thumb(letter, asset_id, "", library)


@router.get("/{letter}/{category_path:path}/{asset_id}", response_class=FileResponse)
async def get_asset_file(letter: str, asset_id: str, category_path: str = "", library: Optional[str] = None):
    try:
        file_path = asset_service.resolve_file(letter, category_path, asset_id, library)
        return FileResponse(file_path)
    except Exception as e:
        raise _http_error(e)


@router.get("/{letter}/{asset_id}", response_class=FileResponse)
async def get_asset_file_root(letter: str, asset_id: str, library: Optional[str] = None):
    return await get_asset_file(letter, asset_id, "", library)


# ======================================================================
# Project asset pool + per-shot references (second router, explicit paths)
# Pool file: {project}/project_assets.json = {"version":1,"assets":[{ref, added_at}]}
# Shot field: reference_asset_ids: [ref, ...] (ordered, first = primary)
# ======================================================================

def _pool_path(project_id: str) -> str:
    return os.path.join(config.ABS_PROJECTS_DIR, project_id, "project_assets.json")


def _read_pool(project_id: str) -> List[dict]:
    path = _pool_path(project_id)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("assets", []) if isinstance(data, dict) else []
    except (OSError, ValueError):
        return []


def _write_pool(project_id: str, assets: List[dict]) -> None:
    path = _pool_path(project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "assets": assets}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _validate_project(project_id: str) -> None:
    if not os.path.isdir(os.path.join(config.ABS_PROJECTS_DIR, project_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")


def _validate_refs(refs: List[str]) -> None:
    """All refs must resolve to an existing file."""
    resolved = asset_service.resolve_refs(refs)
    missing = [r["ref"] for r in resolved if not r.get("exists")]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Some references could not be resolved", "missing": missing},
        )
    return resolved


def _resolve_shot_sync(project_id: str, shot_id_or_index: str):
    """Resolve a shot by stable id or 1-based index (sync variant of shots._resolve_shot)."""
    shots = project_service.project_manager.get_shots(project_id) or []
    for i, shot in enumerate(shots):
        if shot.get("id") == str(shot_id_or_index):
            return shot, i + 1
    if str(shot_id_or_index).isdigit():
        idx = int(shot_id_or_index)
        if 1 <= idx <= len(shots):
            return shots[idx - 1], idx
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Shot '{shot_id_or_index}' not found in project {project_id}"
    )


@project_router.get("/api/projects/{project_id}/assets", response_model=List[ResolvedAssetRef])
async def get_project_assets(project_id: str):
    """The project's asset pool, fully resolved."""
    _validate_project(project_id)
    pool = _read_pool(project_id)
    result = []
    for item in pool:
        entry = asset_service.resolve_ref(item.get("ref", ""))
        entry["added_at"] = item.get("added_at")
        result.append(entry)
    return result


@project_router.post("/api/projects/{project_id}/assets", response_model=List[ResolvedAssetRef])
async def add_project_assets(project_id: str, request: UpdateRefsRequest):
    """Add refs (library or project-media shape) to the project pool."""
    _validate_project(project_id)
    _validate_refs(request.refs)
    pm = project_service.project_manager
    with pm.lock_project(project_id):
        pool = _read_pool(project_id)
        known = {item.get("ref") for item in pool}
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        added = []
        for ref in request.refs:
            if ref not in known:
                pool.append({"ref": ref, "added_at": now})
                known.add(ref)
                added.append(ref)
        _write_pool(project_id, pool)
    result = []
    for item in pool:
        entry = asset_service.resolve_ref(item.get("ref", ""))
        entry["added_at"] = item.get("added_at")
        result.append(entry)
    return result


@project_router.delete("/api/projects/{project_id}/assets/{ref:path}")
async def remove_project_asset(project_id: str, ref: str, strip: bool = Query(True, description="Also remove the ref from all shots of this project")):
    """Remove a ref from the project pool (and by default from every shot using it)."""
    _validate_project(project_id)
    pm = project_service.project_manager
    with pm.lock_project(project_id):
        pool = [item for item in _read_pool(project_id) if item.get("ref") != ref]
        _write_pool(project_id, pool)
    if strip:
        def modify(shots):
            for shot in shots:
                refs = shot.get("reference_asset_ids") or []
                if ref in refs:
                    refs = [r for r in refs if r != ref]
                    shot["reference_asset_ids"] = refs
        pm.update_shots_safely(project_id, modify)
    return {"removed": ref, "pool_size": len(pool)}


@project_router.get("/api/projects/{project_id}/shots/{shot_id}/references", response_model=List[ResolvedAssetRef])
async def get_shot_references(project_id: str, shot_id: str):
    """The shot's attached references, fully resolved and ordered."""
    _validate_project(project_id)
    shot, _ = _resolve_shot_sync(project_id, shot_id)
    return asset_service.resolve_refs(shot.get("reference_asset_ids") or [])


@project_router.put("/api/projects/{project_id}/shots/{shot_id}/references", response_model=List[ResolvedAssetRef])
async def set_shot_references(project_id: str, shot_id: str, request: UpdateRefsRequest):
    """Replace the shot's ordered reference list."""
    _validate_project(project_id)
    _validate_refs(request.refs)
    _apply_shot_refs(project_id, shot_id, request.refs)
    shot, _ = _resolve_shot_sync(project_id, shot_id)
    return asset_service.resolve_refs(shot.get("reference_asset_ids") or [])


@project_router.post("/api/projects/{project_id}/shots/{shot_id}/references", response_model=List[ResolvedAssetRef])
async def add_shot_references(project_id: str, shot_id: str, request: UpdateRefsRequest):
    """Append refs to the shot's reference list (duplicates ignored).
    Only the incoming refs are validated — pre-existing broken refs are left alone."""
    _validate_project(project_id)
    _validate_refs(request.refs)
    shot, _ = _resolve_shot_sync(project_id, shot_id)
    merged = list(dict.fromkeys((shot.get("reference_asset_ids") or []) + request.refs))
    _apply_shot_refs(project_id, shot_id, merged)
    shot, _ = _resolve_shot_sync(project_id, shot_id)
    return asset_service.resolve_refs(shot.get("reference_asset_ids") or [])


@project_router.delete("/api/projects/{project_id}/shots/{shot_id}/references/{ref:path}", response_model=List[ResolvedAssetRef])
async def remove_shot_reference(project_id: str, shot_id: str, ref: str):
    """Remove one ref from the shot's reference list."""
    _validate_project(project_id)
    shot, _ = _resolve_shot_sync(project_id, shot_id)
    merged = [r for r in (shot.get("reference_asset_ids") or []) if r != ref]
    _apply_shot_refs(project_id, shot_id, merged)
    shot, _ = _resolve_shot_sync(project_id, shot_id)
    return asset_service.resolve_refs(shot.get("reference_asset_ids") or [])


@project_router.post("/api/projects/{project_id}/shots/{shot_id}/references/use-as-source")
async def use_reference_as_source(project_id: str, shot_id: str, request: UseAsSourceRequest):
    """Use an attached video reference as a FLFI2V THEN (meeting) or NOW (departure)
    source for the shot. Writes the existing meeting_video_path / departure_video_path
    fields (and their rendered flags so generation is runnable)."""
    _validate_project(project_id)
    if request.slot not in ("then", "now"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slot must be 'then' or 'now'")
    entry = asset_service.resolve_ref(request.ref)
    if not entry.get("exists"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reference not found: {request.ref}")
    if entry.get("type") != "video" or not entry.get("path"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only existing video assets can be used as THEN/NOW sources")

    shot, shot_index = _resolve_shot_sync(project_id, shot_id)
    field = "meeting_video_path" if request.slot == "then" else "departure_video_path"
    flag = "meeting_video_rendered" if request.slot == "then" else "departure_video_rendered"
    rel_path = project_service.project_manager.relativize_path(entry["path"])
    updates = {field: rel_path, flag: True}
    project_service.project_manager.update_shot_metadata(
        project_id, updates,
        shot_id=shot.get("id"),
        shot_index=None if shot.get("id") else shot_index,
    )
    return {"shot_id": shot.get("id") or shot_index, "slot": request.slot, "field": field, "path": rel_path, "ref": request.ref}


def _apply_shot_refs(project_id: str, shot_id: str, refs: List[str]) -> None:
    """Write reference_asset_ids on the shot (resolved by id first, then 1-based index)
    under the project lock."""
    pm = project_service.project_manager

    def modify(shots):
        target = None
        for shot in shots:
            if shot.get("id") == str(shot_id):
                target = shot
                break
        if target is None and str(shot_id).isdigit():
            idx = int(shot_id)
            if 1 <= idx <= len(shots):
                target = shots[idx - 1]
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot '{shot_id}' not found in project {project_id}"
            )
        target["reference_asset_ids"] = list(dict.fromkeys(refs))

    pm.update_shots_safely(project_id, modify)
