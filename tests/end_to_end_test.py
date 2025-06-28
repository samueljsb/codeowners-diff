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

    codeowners_diff.main(('branch-a', 'branch-b', '-C', str(tmp_path)))

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `branch-a`   | `branch-b`    |
|:-----------------|:-------------|:--------------|
| `source_code.py` | @some-user   | @another/team |
"""
    assert captured.err == ''


def test_compare_working_tree_with_another_branch(
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _create_git_repo(tmp_path)
    _create_branch(tmp_path, 'branch-a', '@some-user')

    # Change the working copy of the CODEOWNERS file,
    # without committing it.
    subprocess.run(('git', 'switch', 'main'), cwd=tmp_path)
    (tmp_path / '.github').mkdir(exist_ok=True)
    (tmp_path / '.github' / 'CODEOWNERS').write_text("""\
* @another/team
""")

    codeowners_diff.main(('branch-a', '-C', str(tmp_path)))

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `branch-a`   | working tree   |
|:-----------------|:-------------|:---------------|
| `source_code.py` | @some-user   | @another/team  |
"""
    assert captured.err == ''


def test_compare_working_tree_with_HEAD(
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _create_git_repo(tmp_path)  # HEAD

    # Change the working copy of the CODEOWNERS file,
    # without committing it.
    (tmp_path / '.github').mkdir(exist_ok=True)
    (tmp_path / '.github' / 'CODEOWNERS').write_text("""\
* @some-user
""")

    codeowners_diff.main(('-C', str(tmp_path)))

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `HEAD`   | working tree   |
|:-----------------|:---------|:---------------|
| `source_code.py` |          | @some-user     |
"""
    assert captured.err == ''


def test_limit_is_respected(
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _create_git_repo(tmp_path)
    _create_branch(tmp_path, 'branch-a', '@some-user')
    _create_branch(tmp_path, 'branch-b', '@another/team')

    codeowners_diff.main(
        ('branch-a', 'branch-b', '-C', str(tmp_path), '--limit', '0'),
    )

    captured = capsys.readouterr()
    assert captured.out == """\
1 files have changed ownership:

| file             | `branch-a`   | `branch-b`    |
|:-----------------|:-------------|:--------------|

Note that the above table was truncated to 0 items.
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
