from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class ThumbnailMetadata(TypedDict):
    width: int
    height: int
    file_size: int


class ThumbnailService:
    def __init__(self, size: tuple[int, int] = (800, 600), quality: int = 85) -> None:
        self.size = size
        self.quality = quality

    def generate(self, source: Path, output: Path) -> ThumbnailMetadata:
        try:
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise RuntimeError("Install Pillow to generate thumbnails: pip install pillow") from exc

        output.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as source_image:
            image = ImageOps.exif_transpose(source_image).copy()
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.thumbnail(self.size, Image.Resampling.LANCZOS)
            image.save(output, "JPEG", quality=self.quality, optimize=True)
            return {"width": image.width, "height": image.height, "file_size": output.stat().st_size}

    def image_metadata(self, source: Path) -> tuple[int | None, int | None, str | None, str]:
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Install Pillow to read image metadata: pip install pillow") from exc

        with Image.open(source) as image:
            capture_time = None
            exif_payload: dict[str, str] = {}
            raw_exif = image.getexif()
            for tag_id, value in raw_exif.items():
                if tag_id in {306, 36867, 36868} and capture_time is None:
                    capture_time = str(value)
                if tag_id in {271, 272, 306, 36867, 36868}:
                    exif_payload[str(tag_id)] = str(value)
            import json

            return image.width, image.height, capture_time, json.dumps(exif_payload)
