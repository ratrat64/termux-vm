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
- Use Conventional Commit PR titles. Squash-merge only after another human
  developer approves and applicable checks pass.
- Commit, push, or open PRs only when explicitly requested.
  Obtain human authorization before merging or creating release tags.
- Create vMAJOR.MINOR.PATCH release tags from main; use the same PR process
  for hotfixes.
- Keep credentials, trial media, token-bearing state, and generated private
  reports out of Git. Preserve implementation source under _bmad-output.

<!-- /bmad:context -->
