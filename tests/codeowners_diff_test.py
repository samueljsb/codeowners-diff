from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import codeowners_diff


def test_find_affected_globs() -> None:
    file_a = """\
foo/ @some/team
foo/bar/ @some-user
foo/baz/ @another-user
"""
    file_b = """\
# Team Rules
foo/ @some/team

# User Rules
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
def test_path_to_glob(path: str, glob: str) -> None:
    assert codeowners_diff._path_to_glob(path) == glob


@pytest.fixture(scope='session')
def repo_with_files(tmp_path_factory: pytest.TempPathFactory) -> Path:
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
        ('/does/not/exist', frozenset()),
    ),
)
def test_find_affected_files(
        path: str, expected_files: set[str], repo_with_files: Path,
) -> None:
    """Check that GitHub CODEOWNERS patters are interpreted correctly."""
    affected_files = codeowners_diff.find_affected_files(
        path, codeowners_diff.GitRepo(str(repo_with_files)),
    )
    assert affected_files == expected_files


class TestGitRepo:
    def test_handle_missing_codeowners_file(
            self, tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        # create a git repo
        repo_root = tmp_path_factory.mktemp('repo_with_files')
        subprocess.run(('git', 'init'), cwd=repo_root)

        git_repo = codeowners_diff.GitRepo(str(repo_root))

        codeowners_file = git_repo.load_codeowners_file('HEAD')

        assert codeowners_file == ''


class TestMarkdownPrinter:
    def test_render_lines(self) -> None:
        printer = codeowners_diff.MarkdownPrinter(
            {
                'foo/bar/baz.py': {
                    'base': ('@some-owner', '@some/team'),
                    'HEAD': ('@another/team',),
                },
                'foo/bar/bang.py': {
                    'base': ('@some/team',),
                    'HEAD': ('@another/team', '@some-user'),
                },
            }, None,
        )

        lines = printer.render_lines()
        assert '\n'.join(lines) == """\
2 files have changed ownership:

| file              | `base`                  | `HEAD`                    |
|:------------------|:------------------------|:--------------------------|
| `foo/bar/bang.py` | @some/team              | @another/team, @some-user |
| `foo/bar/baz.py`  | @some-owner, @some/team | @another/team             |"""

    def test_no_changes(self) -> None:
        printer = codeowners_diff.MarkdownPrinter({}, None)

        lines = printer.render_lines()
        assert '\n'.join(lines) == 'No files have changed ownership.'

    def test_max_files_to_print(self) -> None:
        printer = codeowners_diff.MarkdownPrinter(
            {
                'foo/bar/baz.py': {
                    'base': ('@some-owner', '@some/team'),
                    'HEAD': ('@another/team',),
                },
                'foo/bar/bash.py': {
                    'base': ('@some-owner', '@some/team'),
                    'HEAD': ('@another/team',),
                },
                'foo/bar/bang.py': {
                    'base': ('@some/team',),
                    'HEAD': ('@another/team', '@some-user'),
                },
            }, None,
        )

        lines = printer.render_lines()
        assert '\n'.join(lines) == """\
3 files have changed ownership:

| file              | `base`                  | `HEAD`                    |
|:------------------|:------------------------|:--------------------------|
| `foo/bar/bang.py` | @some/team              | @another/team, @some-user |
| `foo/bar/baz.py`  | @some-owner, @some/team | @another/team             |

Note that the above table was truncated to 2 items."""
