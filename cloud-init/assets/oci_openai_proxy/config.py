import os


def env_str(key: str, default: str) -> str:
    v = os.getenv(key)
    if v is None or not str(v).strip():
        return default
    return str(v)


def env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default


OCI_COMPARTMENT_ID: str = env_str(
    "OCI_COMPARTMENT_ID",
    "ocid1.compartment.oc1..aaaaaaaajk6ueeu6g4ofk4dlhhnaofrgs3wr4moxo7nwzu2q3jt4a3xaet5a",
)

# Default endpoint (may be overridden by models registry endpoint)
OCI_ENDPOINT_DEFAULT: str = env_str(
    "OCI_GENAI_ENDPOINT",
    "https://inference.generativeai.us-ashburn-1.oci.oraclecloud.com",
)

# Backward-compatible fallback model id, used only if models registry is missing.
OCI_MODEL_ID_FALLBACK: str = env_str(
    "OCI_GENAI_MODEL_ID",
    "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyaxdbqgulqgbgxeojnobskzgtpbk3dt576t35j7cvcosta",
)

MODELS_FILE: str = env_str("OCI_OPENAI_PROXY_MODELS_FILE", "/etc/oci-openai-proxy/models.json")

PROXY_API_KEY = os.getenv("PROXY_API_KEY")

PROXY_HOST: str = env_str("PROXY_HOST", "127.0.0.1")
PROXY_PORT: int = env_int("PROXY_PORT", 8000)
