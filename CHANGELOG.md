# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

## [0.2.0] - 2025-04-25

## Changed

- `--repo-root` option is now `-C`.
  This matches the `git` CLI.
- The arguments passed to `codeowners-diff`
  now behave like the arguments `git diff`:

  command                   | previous comparison | new comparison
  ------------------------- | ------------------- | ------------------------
  `codeowners-diff foo bar` | `bar` from `foo`    | `bar` from `foo`
  `codeowners-diff foo`     | `HEAD` from `foo`   | working tree from `foo`
  `codeowners-diff`         | `HEAD` from `main`  | working tree from `HEAD`

## v0.1.1 (2024-03-12)

### Fixed

- Ignore blank lines and comments in `CODEOWNERS` file.
  Fixed in [#1](https://github.com/samueljsb/codeowners-diff/pull/1).
- Handle invalid paths in `CODEOWNERS` file.
  Non-existent paths used to accidentally match *every* file in the repository.
  Fixed in [#3](https://github.com/samueljsb/codeowners-diff/pull/3).

## v0.1.0

First release.
