"""Image based claim damage and vehicle part segmentation."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image, UnidentifiedImageError
from django.conf import settings


MODEL_DIR = Path(settings.BASE_DIR.parent) / "ml" / "models"
DAMAGE_MODEL_PATH = MODEL_DIR / "damage_model.pt"
PARTS_MODEL_PATH = MODEL_DIR / "parts_model.pt"
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
_model_lock = Lock()
_inference_lock = Lock()
_models = None
_model_mtimes = None


class DamageAnalysisUnavailable(RuntimeError):
    """Raised when visual claim analysis cannot run."""


def get_damage_model_status():
    try:
        import importlib.util

        ultralytics_installed = importlib.util.find_spec("ultralytics") is not None
    except (ImportError, ValueError):
        ultralytics_installed = False
    damage_exists = DAMAGE_MODEL_PATH.is_file()
    parts_exists = PARTS_MODEL_PATH.is_file()
    return {
        "damage_model": damage_exists,
        "parts_model": parts_exists,
        "ultralytics_installed": ultralytics_installed,
        "available": damage_exists and parts_exists and ultralytics_installed,
    }


def _load_models():
    global _models, _model_mtimes
    status = get_damage_model_status()
    if not status["available"]:
        missing = []
        if not status["damage_model"]:
            missing.append(str(DAMAGE_MODEL_PATH.name))
        if not status["parts_model"]:
            missing.append(str(PARTS_MODEL_PATH.name))
        if not status["ultralytics_installed"]:
            missing.append("Ultralytics Python package")
        raise DamageAnalysisUnavailable(
            "Visual damage analysis is not configured. Missing: " + ", ".join(missing)
        )

    mtimes = (DAMAGE_MODEL_PATH.stat().st_mtime_ns, PARTS_MODEL_PATH.stat().st_mtime_ns)
    with _model_lock:
        if _models is None or _model_mtimes != mtimes:
            try:
                from ultralytics import YOLO

                _models = (YOLO(str(DAMAGE_MODEL_PATH)), YOLO(str(PARTS_MODEL_PATH)))
                _model_mtimes = mtimes
            except Exception as exc:
                _models = None
                _model_mtimes = None
                raise DamageAnalysisUnavailable(f"Could not load the visual analysis models: {exc}") from exc
    return _models


def _resize_mask(mask, width, height):
    mask = np.asarray(mask, dtype=np.float32)
    if mask.shape != (height, width):
        mask_image = Image.fromarray((mask > 0.5).astype(np.uint8) * 255)
        mask = np.asarray(mask_image.resize((width, height), Image.Resampling.NEAREST)) > 0
    else:
        mask = mask > 0.5
    return mask


def _get_label(names, class_id):
    return str(names.get(class_id, class_id)) if isinstance(names, dict) else str(names[class_id])


def _analyze_image(image, damage_model, parts_model):
    width, height = image.size
    image_array = np.asarray(image.convert("RGB"))
    # These model files are trusted project assets and contain the Ultralytics model
    # object as well as its trained parameters.
    parts_result = parts_model.predict(source=image_array, task="segment", imgsz=640, conf=0.25, verbose=False)[0]
    damage_result = damage_model.predict(source=image_array, task="segment", imgsz=640, conf=0.25, verbose=False)[0]

    part_mask_map = np.zeros((height, width), dtype=np.int16)
    if parts_result.masks is not None:
        part_masks = parts_result.masks.data.cpu().numpy()
        part_classes = parts_result.boxes.cls.cpu().numpy().astype(int)
        for mask, class_id in zip(part_masks, part_classes):
            part_mask_map[_resize_mask(mask, width, height)] = class_id + 1

    detections = []
    if damage_result.boxes is None:
        return detections
    damage_classes = damage_result.boxes.cls.cpu().numpy().astype(int)
    confidences = damage_result.boxes.conf.cpu().numpy()
    boxes = damage_result.boxes.xyxy.cpu().numpy()
    damage_masks = damage_result.masks.data.cpu().numpy() if damage_result.masks is not None else None
    for index, class_id in enumerate(damage_classes):
        part_label = None
        if damage_masks is not None and index < len(damage_masks):
            overlap = part_mask_map[_resize_mask(damage_masks[index], width, height)]
            overlap = overlap[overlap > 0]
            if overlap.size:
                part_id = int(np.bincount(overlap).argmax()) - 1
                part_label = _get_label(parts_result.names, part_id)
        x1, y1, x2, y2 = (float(value) for value in boxes[index])
        detections.append({
            "damage": _get_label(damage_result.names, int(class_id)).strip().lower(),
            "part": part_label,
            "confidence": round(float(confidences[index]) * 100, 1),
            "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
        })
    return detections


def analyze_claim_photos(claim):
    """Analyze image documents attached to a claim and save the JSON result."""
    photos = [
        document
        for document in claim.documents.filter(document_type="photos").order_by("uploaded_at")
        if Path(document.original_name or document.file.name).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    if not photos:
        raise ValueError("This claim has no supported image files in its Photos documents. Upload JPG, PNG, WEBP, or BMP images first.")

    damage_model, parts_model = _load_models()
    image_results = []
    skipped = []
    with _inference_lock:
        for document in photos:
            try:
                if document.file.size > MAX_IMAGE_BYTES:
                    skipped.append({"document_id": document.id, "name": document.original_name, "reason": "Image exceeds the 20 MB analysis limit."})
                    continue
                with document.file.open("rb") as image_file:
                    raw = image_file.read()
                with Image.open(BytesIO(raw)) as source:
                    if source.width * source.height > MAX_IMAGE_PIXELS:
                        skipped.append({"document_id": document.id, "name": document.original_name, "reason": "Image exceeds the 25 megapixel analysis limit."})
                        continue
                    image = source.convert("RGB")
            except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
                skipped.append({"document_id": document.id, "name": document.original_name, "reason": "The file is not a readable image."})
                continue
            try:
                detections = _analyze_image(image, damage_model, parts_model)
            except Exception as exc:
                raise DamageAnalysisUnavailable(f"Analysis failed for {document.original_name}: {exc}") from exc
            image_results.append({
                "document_id": document.id,
                "name": document.original_name,
                "width": image.width,
                "height": image.height,
                "detections": detections,
            })

    if not image_results:
        raise ValueError("None of the claim's Photos files could be read as images.")
    analysis = {
        "model": "YOLOv8n segmentation (damage + vehicle parts)",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "images_analyzed": len(image_results),
        "detection_count": sum(len(item["detections"]) for item in image_results),
        "images": image_results,
        "skipped_images": skipped,
    }
    assessment = claim.ai_assessment if isinstance(claim.ai_assessment, dict) else {}
    assessment["visual_damage_analysis"] = analysis
    claim.ai_assessment = assessment
    claim.save(update_fields=["ai_assessment", "updated_at"])
    return analysis
