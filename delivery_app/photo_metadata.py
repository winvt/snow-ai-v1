"""Photo metadata and image-variant helpers for delivery uploads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Dict, Optional

from PIL import Image, ImageOps, TiffImagePlugin, UnidentifiedImageError, ExifTags


JPEG_EXTENSIONS = {".jpg", ".jpeg"}
PHOTO_VARIANTS = {"original", "display", "thumb"}
DISPLAY_MAX_LONG_EDGE = 1600
THUMBNAIL_SIZE = (640, 480)
ORIGINAL_JPEG_QUALITY = 96
DISPLAY_JPEG_QUALITY = 88
THUMBNAIL_JPEG_QUALITY = 82


@dataclass(frozen=True)
class PhotoVariant:
    payload: bytes
    content_type: str


def decimal_to_dms_rationals(value: float):
    """Convert decimal degrees into EXIF D/M/S rationals."""
    absolute = abs(float(value))
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60 * 10000)
    return (
        TiffImagePlugin.IFDRational(degrees, 1),
        TiffImagePlugin.IFDRational(minutes, 1),
        TiffImagePlugin.IFDRational(int(seconds), 10000),
    )


def supports_jpeg_variants(filename: str, content_type: Optional[str]) -> bool:
    """Return whether the input can be safely rewritten as a JPEG variant set."""
    suffix = Path(filename or "").suffix.lower()
    if suffix in JPEG_EXTENSIONS:
        return True
    return (content_type or "").lower() in {"image/jpeg", "image/jpg"}


def build_variant_object_key(object_key: str, variant: str) -> str:
    """Return the object key for the requested stored variant."""
    if variant not in PHOTO_VARIANTS:
        raise ValueError(f"Unknown photo variant: {variant}")
    if variant == "original":
        return object_key

    path = PurePosixPath(object_key)
    suffix = path.suffix or ".jpg"
    return str(path.with_name(f"{path.stem}__{variant}{suffix}"))


def _serialize_jpeg(image: Image.Image, *, exif=None, quality: int) -> bytes:
    """Serialize a PIL image to a high-quality JPEG."""
    output = BytesIO()
    working = image.convert("RGB") if image.mode != "RGB" else image
    save_kwargs = {
        "format": "JPEG",
        "quality": quality,
        "subsampling": 0,
        "optimize": True,
        "progressive": True,
    }
    if exif is not None:
        save_kwargs["exif"] = exif
    working.save(output, **save_kwargs)
    return output.getvalue()


def _build_exif(image: Image.Image, *, latitude: float, longitude: float, accuracy_m: Optional[float], captured_at_client: datetime):
    """Build the EXIF payload written into the archived original JPEG."""
    exif = image.getexif()
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)

    gps_ifd[ExifTags.GPS.GPSLatitudeRef] = "N" if latitude >= 0 else "S"
    gps_ifd[ExifTags.GPS.GPSLatitude] = decimal_to_dms_rationals(latitude)
    gps_ifd[ExifTags.GPS.GPSLongitudeRef] = "E" if longitude >= 0 else "W"
    gps_ifd[ExifTags.GPS.GPSLongitude] = decimal_to_dms_rationals(longitude)
    gps_ifd[ExifTags.GPS.GPSDateStamp] = captured_at_client.strftime("%Y:%m:%d")
    if accuracy_m is not None and accuracy_m >= 0:
        gps_ifd[ExifTags.GPS.GPSHPositioningError] = TiffImagePlugin.IFDRational(
            int(round(accuracy_m * 100)),
            100,
        )

    exif[ExifTags.Base.GPSInfo] = gps_ifd
    exif[ExifTags.Base.DateTimeOriginal] = captured_at_client.strftime("%Y:%m:%d %H:%M:%S")
    exif[ExifTags.Base.DateTimeDigitized] = captured_at_client.strftime("%Y:%m:%d %H:%M:%S")
    exif[ExifTags.Base.DateTime] = datetime.utcnow().strftime("%Y:%m:%d %H:%M:%S")
    return exif


def _build_display_variant(image: Image.Image) -> bytes:
    """Create the medium-sized display image used outside the admin grid."""
    display = image.copy()
    display.thumbnail((DISPLAY_MAX_LONG_EDGE, DISPLAY_MAX_LONG_EDGE), Image.Resampling.LANCZOS)
    return _serialize_jpeg(display, quality=DISPLAY_JPEG_QUALITY)


def _build_thumbnail_variant(image: Image.Image) -> bytes:
    """Create the small admin-card thumbnail."""
    thumbnail = ImageOps.fit(
        image.copy(),
        THUMBNAIL_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    return _serialize_jpeg(thumbnail, quality=THUMBNAIL_JPEG_QUALITY)


def build_photo_variants(
    *,
    payload: bytes,
    filename: str,
    content_type: Optional[str],
    latitude: float,
    longitude: float,
    accuracy_m: Optional[float],
    captured_at_client: datetime,
) -> Dict[str, PhotoVariant]:
    """Generate upload payloads for original, display, and thumbnail variants."""
    default_content_type = content_type or "application/octet-stream"
    if not payload or not supports_jpeg_variants(filename, content_type):
        return {"original": PhotoVariant(payload=payload, content_type=default_content_type)}

    try:
        with Image.open(BytesIO(payload)) as opened:
            opened.load()
            image = ImageOps.exif_transpose(opened)
            exif = _build_exif(
                image,
                latitude=latitude,
                longitude=longitude,
                accuracy_m=accuracy_m,
                captured_at_client=captured_at_client,
            )
            original_payload = _serialize_jpeg(image, exif=exif, quality=ORIGINAL_JPEG_QUALITY)
            display_payload = _build_display_variant(image)
            thumbnail_payload = _build_thumbnail_variant(image)
    except (OSError, UnidentifiedImageError, ValueError, KeyError, TypeError):
        return {"original": PhotoVariant(payload=payload, content_type=default_content_type)}

    return {
        "original": PhotoVariant(payload=original_payload, content_type="image/jpeg"),
        "display": PhotoVariant(payload=display_payload, content_type="image/jpeg"),
        "thumb": PhotoVariant(payload=thumbnail_payload, content_type="image/jpeg"),
    }
