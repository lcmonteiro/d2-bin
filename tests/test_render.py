"""The Python render API: options, themes, text and file rendering, errors."""

import pytest

import pyd2
from pyd2 import D2Error, Options, render, render_file

FLOW = 'user: User\napi: Auth API\nuser -> api: "POST /reset {email}"\n'


def test_render_text_to_svg():
    svg = render(FLOW)
    assert svg.startswith("<?xml") and svg.rstrip().endswith("</svg>") and "Auth API" in svg


def test_options_change_the_output():
    assert render(FLOW, theme="c4") != render(FLOW) != render(FLOW, sketch=True)


def test_render_file_defaults_to_svg_next_to_source(tmp_path):
    source = tmp_path / "flow.d2"
    source.write_text(FLOW)
    out = render_file(source, theme="dark-mauve")
    assert out == tmp_path / "flow.svg" and "Auth API" in out.read_text()
    (tmp_path / "out").mkdir()
    assert render_file(str(source), tmp_path / "out" / "other.svg").is_file()


def test_render_file_matches_render(tmp_path):
    (tmp_path / "flow.d2").write_text(FLOW)
    assert render_file(tmp_path / "flow.d2", layout="elk").read_text() == render(FLOW, layout="elk")


def test_relative_imports_resolve_from_cwd(tmp_path):
    (tmp_path / "shared.d2").write_text("db: Database\n")
    svg = render("...@shared.d2\napi -> db\n", cwd=tmp_path)
    assert "Database" in svg


def test_errors_carry_d2s_message(tmp_path):
    with pytest.raises(D2Error, match=r"d2 failed on <text>: .*connection missing destination") as info:
        render("a -> \n")
    assert "connection missing destination" in info.value.stderr
    (tmp_path / "bad.d2").write_text("a -> {\n")
    with pytest.raises(D2Error, match="d2 failed on bad.d2"):
        render_file(tmp_path / "bad.d2")
    with pytest.raises(FileNotFoundError):
        render_file(tmp_path / "missing.d2")


def test_options_args_and_defaults():
    assert Options().args() == ["--theme=0", "--layout=dagre", "--pad=100", "--omit-version"]
    opts = Options(theme="Colorblind Clear", dark_theme="dark_mauve", layout="elk", sketch=True, pad=24, omit_version=False)
    assert (opts.theme, opts.dark_theme) == (8, 200)
    assert opts.args() == ["--theme=8", "--layout=elk", "--pad=24", "--dark-theme=200", "--sketch"]
    assert Options(theme="7") == Options(theme=7) == Options(theme="aubergine")


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"theme": "nope"}, "unknown D2 theme 'nope'"),
        ({"theme": -1}, "unknown D2 theme -1"),
        ({"dark_theme": True}, "unknown D2 theme True"),
        ({"layout": "tala"}, "use dagre or elk"),
        ({"pad": -5}, "pad must be"),
    ],
)
def test_invalid_options(kwargs, message):
    with pytest.raises(ValueError, match=message):
        Options(**kwargs)


def test_options_object_or_keywords_not_both():
    with pytest.raises(TypeError, match="not both"):
        render(FLOW, Options(), theme=1)
    assert render(FLOW, Options(theme=1)) == render(FLOW, theme=1)


def test_theme_names():
    assert pyd2.theme_id("C4") == 303 and pyd2.theme_name(303) == "c4" and pyd2.theme_name(999) == "999"
    assert set(pyd2.THEMES) == set(pyd2.LIGHT_THEMES) | set(pyd2.DARK_THEMES)


def test_another_pyd2ary_can_be_used(tmp_path):
    with pytest.raises((FileNotFoundError, PermissionError, OSError)):
        render(FLOW, d2=str(tmp_path / "no-such-d2"))
