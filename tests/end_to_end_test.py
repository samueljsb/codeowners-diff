from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import codeowners_diff


def test_compare_two_branches(
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _create_git_repo(tmp_path)
    _create_branch(tmp_path, 'branch-a', '@some-user')
    _create_branch(tmp_path, 'branch-b', '@another/team')

    codeowners_diff.main(('branch-a', 'branch-b', '--repo-root', str(tmp_path)))

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `branch-a`   | `branch-b`    |
|:-----------------|:-------------|:--------------|
| `source_code.py` | @some-user   | @another/team |
"""
    assert captured.err == ''


def test_compare_HEAD_with_another_branch(
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _create_git_repo(tmp_path)
    _create_branch(tmp_path, 'branch-a', '@some-user')
    _create_branch(tmp_path, 'branch-b', '@another/team')  # HEAD

    codeowners_diff.main(('branch-a', '--repo-root', str(tmp_path)))

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `branch-a`   | `HEAD`        |
|:-----------------|:-------------|:--------------|
| `source_code.py` | @some-user   | @another/team |
"""
    assert captured.err == ''


def test_compare_HEAD_with_main(
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _create_git_repo(tmp_path)
    _create_branch(tmp_path, 'branch-a', '@some-user')  # HEAD

    codeowners_diff.main(('--repo-root', str(tmp_path)))

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `main`   | `HEAD`     |
|:-----------------|:---------|:-----------|
| `source_code.py` |          | @some-user |
"""
    assert captured.err == ''


def _create_git_repo(root_dir: Path) -> None:
    subprocess.run(('git', 'init'), cwd=root_dir)

    (root_dir / 'source_code.py').touch()
    subprocess.run(('git', 'add', '.'), cwd=root_dir)
    subprocess.run(('git', 'commit', '--no-gpg-sign', '-m', 'initial'), cwd=root_dir)


def _create_branch(repo_root: Path, branch_name: str, code_owner: str) -> None:
    subprocess.run(('git', 'switch', '-c', branch_name), cwd=repo_root)
    (repo_root / '.github').mkdir(exist_ok=True)
    (repo_root / '.github' / 'CODEOWNERS').write_text(f"""\
* {code_owner}
""")
    subprocess.run(('git', 'add', '.'), cwd=repo_root)
    subprocess.run(
        ('git', 'commit', '--no-gpg-sign', '-m', 'add code owners'),
        cwd=repo_root,
    )
