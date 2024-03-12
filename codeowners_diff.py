from __future__ import annotations

import argparse
import difflib
import functools
import glob
import operator
import os.path
import re
import subprocess
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence

import codeowners
from tabulate import tabulate


class GitRepo:
    def __init__(self, root_dir: str | None = None) -> None:
        if root_dir:  # pragma: no cover
            self.root_dir = root_dir

    @functools.cached_property
    def root_dir(self) -> str:  # pragma: no cover
        return subprocess.check_output(
            ('git', 'rev-parse', '--show-toplevel'),
            text=True,
        ).strip()

    def load_codeowners_file(self, ref: str) -> str:
        return subprocess.check_output(
            ('git', 'cat-file', 'blob', f'{ref}:.github/CODEOWNERS'),
            cwd=self.root_dir,
            text=True,
        )

    def ls_files(self, paths: Sequence[str]) -> frozenset[str]:
        if not paths:
            return frozenset()

        return frozenset(
            subprocess.check_output(
                ('git', 'ls-files', '--', *paths),
                cwd=self.root_dir,
                text=True,
            )
            .strip()
            .splitlines(),
        )


class CodeOwners:
    def __init__(self, src: str) -> None:
        self.code_owners = codeowners.CodeOwners(src)

    def of(self, filepath: str) -> tuple[str, ...]:
        return tuple(owner[1] for owner in self.code_owners.of(filepath))


class MarkdownPrinter:
    def __init__(
        self, changed_owners: Mapping[str, Mapping[str, tuple[str, ...]]],
    ) -> None:
        self.changed_owners = changed_owners

    def render_lines(self) -> Iterator[str]:
        if not self.changed_owners:
            yield 'No files have changed ownership.'
            return

        yield f'{len(self.changed_owners)} files have changed ownership:'
        yield ''
        yield from tabulate(
            sorted(
                (
                    {
                        'file': f'`{file}`',
                        **{
                            f'`{ref}`': ', '.join(owners_)
                            for ref, owners_ in owners.items()
                        },
                    }
                    for file, owners in self.changed_owners.items()
                ),
                key=operator.itemgetter('file'),  # type: ignore[arg-type]
            ),
            headers='keys',
            tablefmt='pipe',
        ).splitlines()


def find_affected_paths(a: str, b: str) -> frozenset[str]:
    diff_generator = difflib.Differ().compare(a.splitlines(), b.splitlines())
    pattern = re.compile(r'^[+-] *(?P<path>[^# ]+)')
    return frozenset(
        match.group('path')
        for line in diff_generator
        if (match := pattern.match(line))
    )


def _path_to_glob(path: str) -> str:
    if path.startswith('/'):
        return path[1:]  # remove leading '/'
    else:
        return os.path.join(
            '**', path,
        )  # add leading '**/' to match anywhere in the repo


def find_affected_files(path: str, repo: GitRepo) -> frozenset[str]:
    glob_ = _path_to_glob(path)
    paths = glob.glob(
        glob_, root_dir=repo.root_dir, recursive=True,
    )
    return repo.ls_files(paths)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='get a summary of the changes to code owners between two refs',
    )
    parser.add_argument(
        'base_ref',
        nargs='?', default='main',
        help='default: %(default)s',
    )
    parser.add_argument(
        'head_ref',
        nargs='?', default='HEAD',
        help='default: %(default)s',
    )
    parser.add_argument(
        '-r', '--repo-root',
        default=None,
        help='git repository to run the tool in (default: current directory)',
    )
    args = parser.parse_args(argv)

    git_repo = GitRepo(args.repo_root)

    base_code_owners_src = git_repo.load_codeowners_file(args.base_ref)
    head_code_owners_src = git_repo.load_codeowners_file(args.head_ref)

    affected_paths = find_affected_paths(base_code_owners_src, head_code_owners_src)
    affected_files = {
        file
        for path in affected_paths
        for file in find_affected_files(path, git_repo)
    }

    base_code_owners = CodeOwners(base_code_owners_src)
    head_code_owners = CodeOwners(head_code_owners_src)

    base_file_owners = {file: base_code_owners.of(file) for file in affected_files}
    head_file_owners = {file: head_code_owners.of(file) for file in affected_files}

    changed_file_owners = {
        file: {
            args.base_ref: base_file_owners[file],
            args.head_ref: head_file_owners[file],
        }
        for file in affected_files
        if base_file_owners[file] != head_file_owners[file]
    }

    printer = MarkdownPrinter(changed_file_owners)
    print(*printer.render_lines(), sep='\n')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
