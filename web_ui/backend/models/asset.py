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


class TextContent(BaseModel):
    """Full text of a Guides (text-type) asset."""
    ref: str
    id: str = ""
    title: str
    filename: str
    ext: str
    content: str


class GenerateAssetRequest(BaseModel):
    """Generate an image/video/sound asset directly into a library category."""
    kind: str  # "image" | "video" | "audio"
    prompt: str
    cat: Optional[str] = None  # target category ("i", "i/Characters", ...); defaults to the kind's type root
    title: Optional[str] = None
    library: Optional[str] = None
    workflow: Optional[str] = None  # workflow key; None = configured default
    aspect_ratio: Optional[str] = None  # image/video: "16:9", "9:16", ...
    seed: Optional[int] = None
    duration: Optional[float] = None  # video clip length in seconds
    image_ref: Optional[str] = None  # video: source image asset ref (required)
    video_ref: Optional[str] = None  # audio: source video asset ref (required)
    reference_refs: Optional[List[str]] = None  # image: extra reference image refs


class GenerationStatus(BaseModel):
    id: str
    kind: str
    status: str  # queued | running | completed | failed | cancelled
    progress: int = 0
    message: Optional[str] = None
    prompt: str = ""
    cat: str = ""
    title: Optional[str] = None
    library: Optional[str] = None
    workflow: Optional[str] = None
    aspect_ratio: Optional[str] = None
    seed: Optional[int] = None
    duration: Optional[float] = None
    image_ref: Optional[str] = None
    video_ref: Optional[str] = None
    reference_refs: List[str] = []
    ref: Optional[str] = None  # asset ref once completed
    url: Optional[str] = None
    thumb_url: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class GenerateOptions(BaseModel):
    """Available workflows/choices for the generate dialog."""
    image_workflows: List[dict] = []
    video_workflows: List[dict] = []
    soundfx_workflows: List[dict] = []
    video_mode: str = "comfyui"
    aspect_ratios: List[str] = ["16:9", "9:16", "1:1", "4:3", "3:4"]
