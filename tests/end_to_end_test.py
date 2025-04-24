from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import codeowners_diff


def test_compare_two_branches(
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
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
