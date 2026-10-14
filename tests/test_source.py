"""validate / validate_file and format / format_file."""

import pytest

import pyd2
from pyd2 import D2Error

VALID = "user: User\napi: Auth API\nuser -> api: reset\n"


def test_validate_accepts_valid_source():
    assert pyd2.validate(VALID) is None


@pytest.mark.parametrize(
    "source, message",
    [
        ("a -> \n", "connection missing destination"),
        ("a: {\n", "maps must be terminated"),
        ("a.shape: not-a-shape\n", "unknown shape"),
        ("direction: sideways\n", "direction"),
        ("a: ${missing}\n", "missing"),
        ("a.style.opacity: 5\n", "opacity"),
    ],
)
def test_validate_reports_d2s_error(source, message):
    with pytest.raises(D2Error, match=message) as info:
        pyd2.validate(source)
    assert str(info.value).startswith("d2 failed on <text>: ") and "Cmd:" not in str(info.value)


def test_validate_resolves_imports_from_cwd(tmp_path):
    (tmp_path / "shared.d2").write_text("db: Database\n")
    pyd2.validate("...@shared.d2\napi -> db\n", cwd=tmp_path)
    with pytest.raises(D2Error, match="shared.d2"):
        pyd2.validate("...@shared.d2\n", cwd=tmp_path / "..")  # not found from there


def test_validate_file(tmp_path):
    (tmp_path / "shared.d2").write_text("db: Database\n")
    good = tmp_path / "good.d2"
    good.write_text("...@shared.d2\napi -> db\n")
    pyd2.validate_file(good)  # imports resolve next to the file
    (tmp_path / "shared.d2").unlink()
    with pytest.raises(D2Error, match="d2 failed on good.d2: .*shared.d2"):
        pyd2.validate_file(good)
    bad = tmp_path / "bad.d2"
    bad.write_text("a -> \n")
    with pytest.raises(D2Error, match="d2 failed on bad.d2: .*connection missing destination"):
        pyd2.validate_file(str(bad))
    with pytest.raises(FileNotFoundError):
        pyd2.validate_file(tmp_path / "missing.d2")


def test_format_text():
    assert pyd2.format("a->b\n  c:   x\n") == "a -> b\nc: x\n"
    assert pyd2.format("a -> b\n") == "a -> b\n"
    with pytest.raises(D2Error, match="d2 failed on <text>: .*connection missing destination"):
        pyd2.format("a -> \n")


def test_format_parses_but_does_not_compile():
    """Formatting is syntax only: an unknown shape is still formatted."""
    assert pyd2.format("a.shape:   not-a-shape\n") == "a.shape: not-a-shape\n"


def test_format_file_in_place(tmp_path):
    path = tmp_path / "flow.d2"
    path.write_text("a->b\n")
    assert pyd2.format_file(path) is True and path.read_text() == "a -> b\n"
    assert pyd2.format_file(str(path)) is False


def test_format_file_check_leaves_the_file(tmp_path):
    path = tmp_path / "flow.d2"
    path.write_text("a->b\n")
    assert pyd2.format_file(path, check=True) is True and path.read_text() == "a->b\n"
    path.write_text("a -> b\n")
    assert pyd2.format_file(path, check=True) is False


def test_format_file_errors(tmp_path):
    bad = tmp_path / "bad.d2"
    bad.write_text("a -> \n")
    with pytest.raises(D2Error, match="d2 failed on bad.d2: "):
        pyd2.format_file(bad)
    assert bad.read_text() == "a -> \n"
    with pytest.raises(FileNotFoundError):
        pyd2.format_file(tmp_path / "missing.d2")
