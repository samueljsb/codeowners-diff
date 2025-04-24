# Code Owner diff tool

This tool helps to identify which files in a repository are changing ownership
when a GitHub `CODEOWNERS` file changes.

## Usage

```console
$ codeowners-diff --help
usage: codeowners-diff [-h] [-C REPO_ROOT] [base_ref] [head_ref]

get a summary of the changes to code owners between two refs

positional arguments:
  base_ref      default: HEAD
  head_ref      default: the working tree

options:
  -h, --help    show this help message and exit
  -C REPO_ROOT  git repository to run the tool in (default: current directory)
```

By default,
the tool will show the changes in ownership
between the current revision and `main`.

The output is GitHub-flavoured Markdown.
