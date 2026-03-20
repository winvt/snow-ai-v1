"""Photo metadata helpers for delivery uploads."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps, TiffImagePlugin, UnidentifiedImageError, ExifTags


JPEG_EXTENSIONS = {".jpg", ".jpeg"}


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


def _supports_exif(filename: str, content_type: Optional[str]) -> bool:
    suffix = Path(filename or "").suffix.lower()
    if suffix in JPEG_EXTENSIONS:
        return True
    return (content_type or "").lower() in {"image/jpeg", "image/jpg"}


def embed_exif_metadata(
    *,
    payload: bytes,
    filename: str,
    content_type: Optional[str],
    latitude: float,
    longitude: float,
    accuracy_m: Optional[float],
    captured_at_client: datetime,
) -> bytes:
    """Write GPS and capture timestamp metadata into supported image payloads."""
    if not payload or not _supports_exif(filename, content_type):
        return payload

    try:
        with Image.open(BytesIO(payload)) as image:
            image = ImageOps.exif_transpose(image)
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

            output = BytesIO()
            save_kwargs = {"format": "JPEG", "exif": exif}
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            image.save(output, **save_kwargs)
            return output.getvalue()
    except (OSError, UnidentifiedImageError, ValueError, KeyError, TypeError):
        return payload
