"""
Pydantic models for the asset library API
"""
from pydantic import BaseModel
from typing import List, Optional


class AssetLibraryInfo(BaseModel):
    slug: str
    name: str
    path: str
    is_default: bool
    exists: bool


class UpdateLibrariesRequest(BaseModel):
    paths: List[str]


class AssetEntry(BaseModel):
    ref: str
    library: Optional[str] = None
    id: str
    title: str
    type: str
    letter: str
    cat: str
    category: str
    filename: str
    ext: str
    url: str
    thumb_url: Optional[str] = None
    size_bytes: int = 0
    modified_at: Optional[str] = None
    media: Optional[dict] = None


class AssetTreeNode(BaseModel):
    name: str
    letter: str
    path: str
    count: int
    children: List["AssetTreeNode"]


AssetTreeNode.model_rebuild()


class UploadResult(BaseModel):
    saved: List[AssetEntry]
    skipped: List[dict]
    rerouted: List[dict]


class RenameAssetRequest(BaseModel):
    ref: str
    title: str


class MoveAssetRequest(BaseModel):
    ref: str
    to_cat: str


class AdoptAssetRequest(BaseModel):
    ref_path: str
    library: Optional[str] = None


class CreateCategoryRequest(BaseModel):
    cat: str
    name: str
    library: Optional[str] = None


class DeleteCategoryRequest(BaseModel):
    cat: str
    library: Optional[str] = None


class MoveCategoryRequest(BaseModel):
    cat: str
    to_parent: str
    library: Optional[str] = None


class RenameCategoryRequest(BaseModel):
    cat: str
    name: str
    library: Optional[str] = None


class ResolvedAssetRef(BaseModel):
    """A reference resolved to a concrete file, from either the asset library
    (kind='library') or another project's media (kind='project')."""
    ref: str
    kind: str = "library"
    title: str
    type: str
    letter: Optional[str] = None
    url: str = ""
    thumb_url: Optional[str] = None
    source: Optional[str] = None
    exists: bool = True
    size_bytes: int = 0
    modified_at: Optional[str] = None
    added_at: Optional[str] = None
    media: Optional[dict] = None


class UpdateRefsRequest(BaseModel):
    refs: List[str]


class UseAsSourceRequest(BaseModel):
    ref: str
    slot: str  # "then" (meeting video) | "now" (departure video)


class ImportAssetRequest(BaseModel):
    ref: str  # "p/{pid}/{dir}/{filename}" or library ref
    cat: str  # target category, e.g. "i/Characters"
    title: Optional[str] = None
    library: Optional[str] = None
