
from abc import ABC, abstractmethod


class EmbeddingGenerator(ABC):

    @abstractmethod
    def generate(
        self,
        texts: list[str]
    ) -> list[list[float]]:
        """
        Generate one embedding vector for each input text.

        The returned embeddings must preserve
        the order of the input texts.
        """
        pass