# Workflow

How work gets done in this repo, end to end. Applies to any change beyond a
trivial one-liner — use judgment for genuinely small stuff, but default to
the full loop.

## 0. Check state before starting anything

`git status` and `git log --oneline -10`. If there's uncommitted work or
unmerged branches you didn't expect, don't discard or silently fold it into
your own change — flag it and ask, or leave it alone. Multiple sessions can
end up working in the same directory; treat unexpected state as someone
else's in-progress work until proven otherwise.

## 1. Clarify the goal

For anything more than a small fix: get explicit agreement on scope before
writing code. Ask clarifying questions rather than assume. Document goals
and acceptance criteria — for a substantial change, that can be a Plan
(agreed with the user before implementation); for a normal-sized change, a
clear statement in chat is enough, and it becomes the PR description later.

Trivial changes (a copy tweak, a one-line config fix) don't need this
ceremony — just do it and say what you did.

## 2. Branch

Create a branch off the latest `master` (`git pull` first). Never commit
directly to `master` — everything lands there through a PR, no exceptions,
even for small stuff.

## 3. Implement

Run relevant tests locally as you go, not just at the end.

## 4. Before opening the PR

Run the full test suite locally (`pytest tests/ -v`). Manually verify
anything automated tests can't cover — a live check in the browser for UI
changes, a smoke test of a new route, etc.

Update `DEVELOPMENT_PLAN.md`, `FEATURE_BACKLOG.md`, and/or `TESTING.md` in
the same PR if the change affects what they describe. Don't let docs drift
from what the code actually does — stale docs describing unbuilt features
(or built features as unbuilt) have caused real confusion in this repo.

## 5. Open the PR

One PR per logical change. Summary + test plan in the description. Push
triggers CI automatically — no separate manual test-suite step needed here,
CI covers it.

## 6. Before asking to merge

Confirm CI is green (`gh pr checks <n>`) and the PR is mergeable with no
conflicts. Don't ask for merge approval on a red or conflicted PR.

## 7. Merge

Ask for explicit approval before merging to `master`. Don't merge on your
own judgment, even if CI is green.

## 8. Deploy

Ask for explicit approval before redeploying to Cloud Run — merging to
`master` does not imply deploy approval; treat them as separate asks unless
told otherwise.

"Redeploy" isn't done once `gcloud run deploy` exits successfully. After
deploying:
- Check all routes return 200 (a quick `curl` pass against the live URL)
- Check Cloud Run logs for errors (`gcloud run services logs read`)
- If the change added a migration (new/changed models), apply it to Neon:
  `gcloud run jobs execute burns-website-migrate --region us-central1` —
  a deploy with a pending migration will 500 on first request to the
  affected route, and has happened more than once here. See "Database
  migrations" in `DEVELOPMENT_PLAN.md` for the full workflow.

Don't report the deploy as done until this verification passes.

## 9. Clean up

Delete the merged branch, both locally (`git branch -d`) and on the remote
(`git push origin --delete`).
