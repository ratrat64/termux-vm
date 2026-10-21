<!-- bmad:context -->
<!-- Verified 2026-10-19 against 92beaae6599b3f6c035ad064e35f19b95a8e147c. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## Policy

- Use main as the integration branch; submit changes through pull requests.
- Assign one owner, branch, and separate Git worktree to each task.
  Never run concurrent agents in the same working directory.
- Name task branches feat/<task>, fix/<task>, docs/<task>, or chore/<task>.
- Coordinate overlapping file changes with the other task owner before editing.
  Do not overwrite, reset, or stash another worker's changes.
- Keep each PR scoped to one task. Describe its purpose, relevant checks,
  results, and any checks that could not run.
- Rebase unpublished work only. Merge origin/main into published task branches;
  never force-push shared history.
- Use Conventional Commit PR titles. Squash-merge only after applicable checks
  pass.
- Create vMAJOR.MINOR.PATCH release tags from main; use the same PR process
  for hotfixes.
- Keep credentials, trial media, token-bearing state, and generated private
  reports out of Git. Preserve implementation source under _bmad-output.

<!-- /bmad:context -->

## Version-control authorization

Agents may create local commits, push task branches, open pull requests, merge
pull requests and create release tags as part of assigned work without separate
approval. This policy supersedes any contrary approval requirements regenerated
in the managed block above. Task isolation, applicable checks, squash merges and
release-versioning rules still apply.

## Completion criteria

- Always commit task changes and push the task branch before reporting work
  complete. Stage only intended task files and run applicable checks first.
- Features are done only when applicable checks pass, their changes are committed
  and pushed, and a pull request against `main` has been created. Include the PR
  URL in the completion report.
- If checks, commit, push or required PR creation fail, report the blocker rather
  than claiming completion.
