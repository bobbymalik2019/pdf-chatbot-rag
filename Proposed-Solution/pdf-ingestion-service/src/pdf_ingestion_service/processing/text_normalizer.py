# We'll build a TextNormalizer that:
# 1. Normalizes Unicode characters.
# 2. Removes unnecessary control characters.
# 3. Handles repeated whitespace.
# 4. Preserves meaningful paragraph and line boundaries.
# 5. Keeps the original extracted text available for debugging and citations.



import re
import unicodedata


class TextNormalizer:

    def normalize(self, text: str) -> str:
        if not text:
            return ""

        # 1. Normalize Unicode representation
        text = unicodedata.normalize("NFC", text)

        # 2. Standardize line endings
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # 3. Remove control characters except
        # newline and tab
        text = "".join(
            char for char in text
            if char in ("\n", "\t")
            or unicodedata.category(char) != "Cc"
        )

        # 4. Replace non-breaking spaces
        text = text.replace("\u00a0", " ")

        # 5. Remove unnecessary horizontal whitespace
        text = re.sub(r"[ \t]+", " ", text)

        # 6. Remove leading/trailing spaces per line
        text = "\n".join(
            line.strip()
            for line in text.split("\n")
        )

        # 7. Limit excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
