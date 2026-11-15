
from pdf_ingestion_service.processing.text_normalizer import TextNormalizer


def test_normalize_whitespace():
    normalizer = TextNormalizer()

    text = "Hello     World"
    assert normalizer.normalize(text) == "Hello World"


def test_preserve_line_breaks():
    normalizer = TextNormalizer()

    text = "Line 1\nLine 2"
    assert normalizer.normalize(text) == "Line 1\nLine 2"


def test_remove_excessive_blank_lines():
    normalizer = TextNormalizer()

    text = "Paragraph 1\n\n\n\nParagraph 2"

    assert normalizer.normalize(text) == (
        "Paragraph 1\n\nParagraph 2"
    )


def test_normalize_line_endings():
    normalizer = TextNormalizer()

    text = "Line 1\r\nLine 2\rLine 3"

    assert normalizer.normalize(text) == (
        "Line 1\nLine 2\nLine 3"
    )


def test_preserve_java_code():
    normalizer = TextNormalizer()

    text = "public class Example {\n    int value = 10;\n}"

    result = normalizer.normalize(text)

    assert "public class Example {" in result
    assert "int value = 10;" in result
    assert "}" in result


def test_empty_text():
    normalizer = TextNormalizer()

    assert normalizer.normalize("") == ""
