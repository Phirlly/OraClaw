import oci


def genai_client(service_endpoint: str) -> oci.generative_ai_inference.GenerativeAiInferenceClient:
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    return oci.generative_ai_inference.GenerativeAiInferenceClient(
        config={},
        signer=signer,
        service_endpoint=service_endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240),
    )
