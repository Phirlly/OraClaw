import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from . import config


@dataclass(frozen=True)
class ModelInfo:
    name: str
    model_type: str  # "chat" | "embedding"
    oci_model_id: str


def normalize_model_name(name: str) -> str:
    if name.startswith("oci."):
        return name
    return f"oci.{name}"


def load_models_registry() -> Tuple[str, Dict[str, ModelInfo]]:
    """Return (endpoint, models_by_name). If file missing, models is empty."""
    try:
        with open(config.MODELS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return (config.OCI_ENDPOINT_DEFAULT, {})

    if not isinstance(raw, dict):
        raise RuntimeError(f"Invalid models registry (not an object): {config.MODELS_FILE}")

    endpoint = raw.get("endpoint") or config.OCI_ENDPOINT_DEFAULT
    models_raw = raw.get("models")
    if models_raw is None:
        return (endpoint, {})
    if not isinstance(models_raw, dict):
        raise RuntimeError(f"Invalid models registry (models not an object): {config.MODELS_FILE}")

    models: Dict[str, ModelInfo] = {}
    for k, v in models_raw.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            continue
        name = normalize_model_name(k)
        model_type = v.get("type")
        oci_model_id = v.get("oci_model_id")
        if model_type not in ("chat", "embedding"):
            continue
        if not isinstance(oci_model_id, str) or not oci_model_id.strip():
            continue
        models[name] = ModelInfo(name=name, model_type=model_type, oci_model_id=oci_model_id.strip())

    return (endpoint, models)


def resolve_chat_model_id(request_model: Optional[str]) -> str:
    if request_model and isinstance(request_model, str):
        rm = request_model.strip()
        if rm.startswith("ocid1."):
            return rm

        _endpoint, models = load_models_registry()
        mi = models.get(normalize_model_name(rm))
        if mi and mi.model_type == "chat":
            return mi.oci_model_id

    return config.OCI_MODEL_ID_FALLBACK


def resolve_embedding_model_id(request_model: Optional[str]) -> str:
    if request_model and isinstance(request_model, str):
        rm = request_model.strip()

        _endpoint, models = load_models_registry()
        mi = models.get(normalize_model_name(rm))
        if mi and mi.model_type == "embedding":
            return mi.oci_model_id

        if rm.startswith("ocid1.") or ("." in rm and not rm.startswith("oci.")):
            return rm

    raise ValueError("Embedding model is required. Provide a supported `model` or configure models.json.")
