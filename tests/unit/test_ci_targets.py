"""CI runs the suite against the stand; one workflow of its own reads the public site.

Two workflows, and the line between them is the point. `ci.yml` is everything
that is a fact about this code -- every suite, against the stand this
repository ships -- and it is what the README badge reads and what publishes
the showcase. `drift.yml` is the one check that leaves the repository: nightly
and on request, the read-only smoke set against the public site the stand
reproduces. Kept apart, a slow or changed public site can colour neither the
badge nor the page; let a job of one creep into the other and it can again,
without anything looking wrong in either file.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
PUBLIC_SITE = "automationexercise.com"
RUNNER = "ubuntu-24.04"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


CI = _load("ci.yml")
DRIFT = _load("drift.yml")
JOBS = CI["jobs"]
DRIFT_JOBS = DRIFT["jobs"]

#: The selection that makes the drift check safe to point at somebody else's
#: site: the smoke set minus everything that creates an account or places an
#: order. It is also how that step is found below, because a step's position in
#: a list is not a fact about the step -- a cache step inserted above it would
#: move the old `steps[-2]` onto the upload, and the check would then read an
#: environment that is not there without ever saying it had lost the step.
SMOKE_SELECTION = '-m "smoke and not destructive"'

#: The two actions that put a site on GitHub Pages. A job using either of them
#: is a job that can replace what visitors see.
PAGES_ACTIONS = ("actions/upload-pages-artifact", "actions/deploy-pages")


def _triggers(workflow: dict) -> set[str]:
    """The events a workflow runs on.

    YAML 1.1 reads a bare `on` as the boolean true, and PyYAML follows it, so
    the key GitHub calls `on` comes back as `True`. Reading only one spelling
    would find no triggers at all and let any assertion about them pass.
    """
    on = workflow.get("on", workflow.get(True))
    assert on, "the workflow declares no triggers this reader can find"
    return {on} if isinstance(on, str) else set(on)


def _run_lines(job: dict) -> str:
    """Everything a job runs, and everything it is handed while running it.

    A workflow names its target in two places, and reading only one of them is
    what lets the other change unnoticed: `run:` is the command, and `env:` --
    on the job, or on a single step -- is the configuration that command reads.
    This suite takes its target from the environment, so `BASE_URL:
    https://somebody-elses-site` on a step points a job at that site exactly as
    surely as typing the address into the command, and a reader that looked
    only at `run:` would call the job local.

    Both are stringified rather than walked: the question is whether a name
    appears anywhere in what the job executes or is given, and a YAML mapping
    rendered as text answers it without this having to know the shape of every
    value GitHub Actions allows.
    """
    parts = [str(job.get("env", ""))]
    for step in job["steps"]:
        parts.append(step.get("run", ""))
        parts.append(str(step.get("env", "")))
    return "\n".join(parts)


def _needs(job: dict) -> list[str]:
    """A job's `needs`, always as a list.

    GitHub Actions accepts one dependency written bare (`needs: reachable`) and
    several as a list, and both are ordinary. Comparing the raw value against a
    string passes for the list form without looking inside it, so
    `needs: [reachable]` would have satisfied "this job does not wait for the
    probe" while waiting for exactly that.
    """
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


def _step_running(job: dict, fragment: str, job_name: str) -> dict:
    """The one step of a job whose command contains `fragment`."""
    matching = [step for step in job["steps"] if fragment in step.get("run", "")]
    assert len(matching) == 1, (
        f"expected exactly one step of the `{job_name}` job to run `{fragment}`, "
        f"found {len(matching)}. Either the step stopped running that selection or "
        f"another one started running it too, and in both cases what this test "
        f"checks is no longer where it thinks it is."
    )
    return matching[0]


def _step_using(job: dict, action: str) -> dict:
    """The one step of a job that uses `action`, at whatever version."""
    matching = [step for step in job["steps"] if step.get("uses", "").startswith(f"{action}@")]
    assert len(matching) == 1, f"expected one step using {action}, found {len(matching)}"
    return matching[0]


def _deploys_pages(job: dict) -> bool:
    return any(step.get("uses", "").startswith(PAGES_ACTIONS) for step in job.get("steps", []))


# -- ci.yml: this code, and nothing else -----------------------------------------


def test_ci_runs_on_changes_and_by_hand_never_on_a_schedule() -> None:
    """The badge reads this workflow, so nothing in it may run on a clock.

    A nightly run of a deterministic suite against its own stand repeats what
    the push already proved; the only nightly worth having is the drift check,
    and that is drift.yml's.
    """
    assert _triggers(CI) == {"push", "pull_request", "workflow_dispatch"}


def test_no_job_in_ci_names_the_public_site() -> None:
    naming = {name for name, job in JOBS.items() if PUBLIC_SITE in _run_lines(job)}
    assert not naming, naming
    assert PUBLIC_SITE not in str(CI.get("env", "")), "ci.yml hands every job the public site"
    for name, job in JOBS.items():
        assert "TEST_ENV" not in _run_lines(job), (
            f"`{name}` sets TEST_ENV; in ci.yml every job runs against the stand, "
            f"which is the default"
        )


def test_the_publication_waits_for_every_suite_and_publishes_from_main_only() -> None:
    job = JOBS["showcase"]
    assert sorted(_needs(job)) == ["api", "framework", "ui"]
    assert job["if"] == "github.ref == 'refs/heads/main'"


def test_the_publication_never_puts_an_older_commit_over_a_newer_one() -> None:
    """Runs finish out of order, and a re-run builds its old commit.

    The job asks which commit main is at before it builds anything, and every
    step from the checkout to the deployment waits for that answer. A step
    without the condition would run on a stale commit; a check placed after
    the deployment would come too late to matter.
    """
    steps = JOBS["showcase"]["steps"]
    check = steps[0]
    assert check.get("id") == "current", "the first step of `showcase` is the head-of-main check"
    assert "git/ref/heads/main" in check["run"] and "RUN_SHA" in check["run"]
    assert check["env"]["RUN_SHA"] == "${{ github.sha }}"
    condition = "steps.current.outputs.current == 'true'"
    unguarded = [step.get("name") or step.get("uses") for step in steps[1:] if step.get("if") != condition]
    assert not unguarded, f"steps of `showcase` that run whatever main is at: {unguarded}"


# -- drift.yml: the one workflow that leaves ------------------------------------


def test_the_drift_check_runs_nightly_and_by_hand_only() -> None:
    assert _triggers(DRIFT) == {"schedule", "workflow_dispatch"}
    crons = [entry["cron"] for entry in DRIFT.get("on", DRIFT.get(True))["schedule"]]
    assert crons == ["0 6 * * *"], "the README and the pipeline figure say nightly at 06:00 UTC"


def test_the_drift_check_runs_only_the_non_destructive_smoke_set_against_the_public_site() -> None:
    job = DRIFT_JOBS["external"]
    drift = _step_running(job, SMOKE_SELECTION, "external")
    assert drift["env"]["TEST_ENV"] == "prod"
    assert _run_lines(job).count("pytest") == 1, "the drift job runs one pytest, the smoke set"


def test_an_unreachable_site_skips_the_drift_check_and_drift_turns_it_red() -> None:
    """Skipped, not failed, when the site does not answer; red when it changed.

    The probe gates the job, so a site that does not answer 200 skips it and
    the run stays green with a notice. The job itself carries no
    `continue-on-error`: once the site did answer, a failing smoke set is the
    one thing this workflow exists to report.
    """
    probe = DRIFT_JOBS["reachable"]
    assert "::notice" in _run_lines(probe)
    job = DRIFT_JOBS["external"]
    assert _needs(job) == ["reachable"]
    assert job["if"] == "needs.reachable.outputs.status == '200'"
    assert "continue-on-error" not in job


def test_the_drift_check_publishes_nothing() -> None:
    """Nothing it finds may land on the showcase, or over it."""
    assert DRIFT.get("permissions") == {"contents": "read"}
    for name, job in DRIFT_JOBS.items():
        assert "permissions" not in job, f"`{name}` asks for more than reading the code"
        assert not _deploys_pages(job), f"`{name}` deploys to GitHub Pages"


# -- both -----------------------------------------------------------------------


def test_every_job_runs_on_the_pinned_runner_image() -> None:
    """`ubuntu-latest` moves under a pipeline without a commit to say so."""
    for workflow, jobs in (("ci.yml", JOBS), ("drift.yml", DRIFT_JOBS)):
        for name, job in jobs.items():
            assert job["runs-on"] == RUNNER, f"{workflow}: `{name}` runs on {job['runs-on']}"


def test_every_job_that_deploys_pages_shares_one_uncancelled_group() -> None:
    """Two publications that overlap read the same history and lose a run.

    Every workflow file is read, not just the two this module knows by name,
    so a third one that learns to deploy has to join the group too.
    """
    deploying = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        for name, job in yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"].items():
            if _deploys_pages(job):
                deploying.append(f"{path.name}:{name}")
                assert job.get("concurrency") == {"group": "pages", "cancel-in-progress": False}, (
                    f"{path.name}: `{name}` deploys to GitHub Pages outside the `pages` group"
                )
    assert deploying == ["ci.yml:showcase"], deploying
    for action in PAGES_ACTIONS:
        _step_using(JOBS["showcase"], action)


def test_the_readme_badge_reads_the_push_runs_of_ci_on_main() -> None:
    """The badge says one word about this code, so it reads the workflow that tests it.

    Filtered to pushes on main: a pull request or a manual run of the same
    workflow is somebody trying something, not the state of the branch.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    badges = re.findall(r"https://github\.com/[^)\s]+/badge\.svg[^)\s]*", readme)
    assert badges == [
        "https://github.com/WolfGung/Marketplace-Test-Automation-Framework"
        "/actions/workflows/ci.yml/badge.svg?branch=main&event=push"
    ], badges
