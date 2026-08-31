from typing import Any, Dict
from story.vectordb.VectorEnums import VectorDBProvider
from story.vectordb.providers.chroma_provider import ChromaProvider
from story.vectordb.providers.mock_provider import MockVectorDBProvider

_PROVIDER_MAP = {
    VectorDBProvider.CHROMA: ChromaProvider,
    VectorDBProvider.MOCK:   MockVectorDBProvider,
}


class VectorDBProviderFactory:
    """
    Factory class that returns the chosen VectorDB provider client.
    """

    @staticmethod
    def create(config: Dict[str, Any]):
        provider_name = config.get("provider", "chroma").lower()
        try:
            provider_enum = VectorDBProvider(provider_name)
        except ValueError:
            raise ValueError(
                f"Unknown VectorDB provider: '{provider_name}'. "
                f"Available: {[p.value for p in VectorDBProvider]}"
            )

        provider_cls = _PROVIDER_MAP.get(provider_enum)
        if not provider_cls:
            raise NotImplementedError(f"VectorDB Provider '{provider_name}' is registered but not implemented.")

        return provider_cls(config)
