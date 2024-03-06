from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import codeowners_diff


def test_find_affected_globs():
    file_a = """\
foo/ @some/team
foo/bar/ @some-user
foo/baz/ @another-user
"""
    file_b = """\
foo/ @some/team
foo/bar/ @another-user
foo/baz/ @another-user
"""

    changed_globs = codeowners_diff.find_affected_paths(file_a, file_b)

    assert set(changed_globs) == {'foo/bar/'}


@pytest.mark.parametrize(
    'path, glob',
    (
        ('foo/bar', '**/foo/bar'),
        ('foo/bar/', '**/foo/bar/'),
        ('/foo/bar', 'foo/bar'),
        ('/foo/bar/', 'foo/bar/'),
        ('/foo/bar.py', 'foo/bar.py'),
        ('foo/b*', '**/foo/b*'),
    ),
)
def test_path_to_glob(path: str, glob: str):
    assert codeowners_diff._path_to_glob(path) == glob


@pytest.fixture(scope='session')
def repo_with_files(tmp_path_factory: pytest.TempPathFactory):
    """Set up a git repo with a nested file structure:

    foo/
    ├── bar/
    │  └── baz.py
    ├── baz.py
    └── fizz/
        └── buzz/
            └── bang.py
    """
    tmp_path = tmp_path_factory.mktemp('repo_with_files')
    (tmp_path / 'foo').mkdir()
    (tmp_path / 'foo' / 'baz.py').touch()
    (tmp_path / 'foo' / 'bar').mkdir()
    (tmp_path / 'foo' / 'bar' / 'baz.py').touch()
    (tmp_path / 'foo' / 'fizz').mkdir()
    (tmp_path / 'foo' / 'fizz' / 'buzz').mkdir()
    (tmp_path / 'foo' / 'fizz' / 'buzz' / 'bang.py').touch()
    subprocess.run(('git', 'init'), cwd=tmp_path)
    subprocess.run(('git', 'add', '.'), cwd=tmp_path)
    subprocess.run(('git', 'commit', '-m', '...'), cwd=tmp_path)

    return tmp_path


@pytest.mark.parametrize(
    'path, expected_files',
    (
        ('foo/bar', {'foo/bar/baz.py'}),
        ('foo/bar/', {'foo/bar/baz.py'}),
        ('/foo/bar', {'foo/bar/baz.py'}),
        ('/foo/bar/', {'foo/bar/baz.py'}),
        ('foo/bar/baz.py', {'foo/bar/baz.py'}),
        ('/foo/fizz', {'foo/fizz/buzz/bang.py'}),
    ),
)
def test_find_affected_files(
        path: str, expected_files: set[str], repo_with_files: Path,
):
    """Check that GitHub CODEOWNERS patters are interpreted correctly."""
    affected_files = codeowners_diff.find_affected_files(
        path, codeowners_diff.GitRepo(str(repo_with_files)),
    )
    assert affected_files == expected_files


class TestMarkdownPrinter:
    def test_render_lines(self):
        printer = codeowners_diff.MarkdownPrinter({
            'foo/bar/baz.py': {
                'base': ('@some-owner', '@some/team'),
                'HEAD': ('@another/team',),
            },
            'foo/bar/bang.py': {
                'base': ('@some/team',),
                'HEAD': ('@another/team', '@some-user'),
            },
        })

        lines = printer.render_lines()
        assert '\n'.join(lines) == """\
2 files have changed ownership:

| file              | `base`                  | `HEAD`                    |
|:------------------|:------------------------|:--------------------------|
| `foo/bar/bang.py` | @some/team              | @another/team, @some-user |
| `foo/bar/baz.py`  | @some-owner, @some/team | @another/team             |"""

    def test_no_changes(self):
        printer = codeowners_diff.MarkdownPrinter({})

        lines = printer.render_lines()
        assert '\n'.join(lines) == 'No files have changed ownership.'


def test_codeowners_diff(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """End-to-end test of the CLI."""
    # set up a git repo with a file in it
    (tmp_path / 'source_code.py').touch()
    subprocess.run(('git', 'init'), cwd=tmp_path)
    subprocess.run(('git', 'add', '.'), cwd=tmp_path)
    subprocess.run(('git', 'commit', '--no-gpg-sign', '-m', 'initial'), cwd=tmp_path)

    # create a CODEOWNERS file in a branch
    subprocess.run(('git', 'switch', '-c', 'branch-a'), cwd=tmp_path)
    (tmp_path / '.github').mkdir(exist_ok=True)
    (tmp_path / '.github' / 'CODEOWNERS').write_text("""\
* @some-user
""")
    subprocess.run(('git', 'add', '.'), cwd=tmp_path)
    subprocess.run(
        ('git', 'commit', '--no-gpg-sign', '-m', 'add code owners'),
        cwd=tmp_path,
    )

    # create a different CODEOWNERS file in another branch
    subprocess.run(('git', 'switch', '-c', 'branch-b', 'main'), cwd=tmp_path)
    (tmp_path / '.github').mkdir(exist_ok=True)
    (tmp_path / '.github' / 'CODEOWNERS').write_text("""\
* @another/team
""")
    subprocess.run(('git', 'add', '.'), cwd=tmp_path)
    subprocess.run(
        ('git', 'commit', '--no-gpg-sign', '-m', 'add code owners'),
        cwd=tmp_path,
    )

    codeowners_diff.main(('branch-a', 'branch-b', '--repo-root', str(tmp_path)))

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `branch-a`   | `branch-b`    |
|:-----------------|:-------------|:--------------|
| `source_code.py` | @some-user   | @another/team |
"""
    assert captured.err == ''
