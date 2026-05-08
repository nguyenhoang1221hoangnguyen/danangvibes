from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FolderRoot:
    label: str
    path: Path


def allowed_roots() -> list[FolderRoot]:
    home = Path.home()
    candidates = [
        FolderRoot("Home", home),
        FolderRoot("Desktop", home / "Desktop"),
        FolderRoot("Pictures", home / "Pictures"),
        FolderRoot("Volumes", Path("/Volumes")),
    ]
    roots: list[FolderRoot] = []
    seen: set[Path] = set()
    for root in candidates:
        if not root.path.exists() or not root.path.is_dir():
            continue
        resolved = root.path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(FolderRoot(root.label, resolved))
    return roots


def resolve_allowed_folder(path_value: str | None) -> Path:
    roots = allowed_roots()
    if not roots:
        raise ValueError("No allowed folders are available")
    if not path_value:
        return roots[0].path
    candidate = Path(path_value).expanduser().resolve()
    if not candidate.is_dir():
        raise ValueError("Selected path is not a folder")
    for root in roots:
        if candidate == root.path or root.path in candidate.parents:
            return candidate
    raise ValueError("Selected folder is outside allowed locations")


def parent_within_roots(path: Path) -> Path | None:
    parent = path.parent.resolve()
    if parent == path:
        return None
    try:
        return resolve_allowed_folder(str(parent))
    except ValueError:
        return None


def list_child_directories(path: Path) -> list[Path]:
    children = []
    for child in path.iterdir():
        try:
            resolved = child.resolve()
        except OSError:
            continue
        if resolved.is_dir():
            try:
                resolve_allowed_folder(str(resolved))
            except ValueError:
                continue
            children.append(resolved)
    return sorted(children, key=lambda child: child.name.lower())


def count_direct_jpegs(path: Path) -> int:
    return sum(1 for child in path.iterdir() if child.is_file() and child.suffix.lower() in {".jpg", ".jpeg"})
