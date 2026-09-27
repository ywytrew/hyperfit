"""Guard complete translations and distributable, synchronized browser manuals."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
import pytest
from tools.build_manuals import render

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "hyperfit/frontend"


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.keys = []
        self.links = []
        self.ids = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "data-i18n" in attributes:
            self.keys.append(attributes["data-i18n"])
        if "href" in attributes:
            self.links.append(attributes["href"])
        if "id" in attributes:
            self.ids.append(attributes["id"])


def test_locale_keys_and_placeholders_match():
    translations = {lang: json.loads((FRONTEND / f"locales/{lang}.json").read_text(encoding="utf-8"))
                    for lang in ("zh", "en", "ja")}
    reference = translations["en"]
    for messages in translations.values():
        assert messages.keys() == reference.keys()
        for key, value in messages.items():
            assert value.strip(), key
            assert sorted(re.findall(r"\{\w+\}", value)) == sorted(re.findall(r"\{\w+\}", reference[key])), key
    page = Page((FRONTEND / "index.html").read_text(encoding="utf-8-sig"))
    assert len(page.ids) == len(set(page.ids))
    assert set(page.keys) <= reference.keys()
    for file in FRONTEND.glob("*.js"):
        for key in re.findall(r'\bt\("([^"]+)"', file.read_text(encoding="utf-8")):
            if not key.endswith("."):
                assert key in reference, (file.name, key)


@pytest.mark.parametrize("lang", ["zh", "en", "ja"])
@pytest.mark.parametrize("kind", ["manual", "deployment"])
def test_browser_document_matches_source_and_local_links_exist(lang, kind):
    text = (ROOT / "docs" / f"{kind}.{lang}.md").read_text(encoding="utf-8")
    html = (FRONTEND / f"{kind}-{lang}.html").read_text(encoding="utf-8")
    assert html == render(text, lang)
    for link in Page(html).links:
        if not link.startswith(("https://", "http://", "./?")):
            assert (FRONTEND / link).is_file(), link
