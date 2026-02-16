The correct Git workflow (first-timer safe version)
🔹 Option A (recommended): You stay in control
Run Codex tasks

Review changes locally

You manually:

git status
git diff
git add .
git commit -m "Codex: add runbook, golden-path test, CI hardening"
git push
Merge as usual

This is the cleanest and safest path.

🔹 Option B (advanced): Let Codex handle the branch
Only do this after you trust it.

You explicitly tell Codex:

Create a new git branch named codex/hardening-pass.
Apply the approved changes.
Commit them with clear messages per logical change.
Do not push.
Then you:

git checkout codex/hardening-pass
git log
git diff main..codex/hardening-pass
git merge
Codex will obey only if told.

2️⃣ “Physically, how does this get into my repo? GitHub? Branch? Merge?”
After Codex finishes any writing step:

git status
git diff
If you like it:

git checkout -b codex/baseline-hardening
git add .
git commit -m "Codex: baseline hardening, golden-path test, CI gates"
git push origin codex/baseline-hardening


Then:
open PR
review
merge