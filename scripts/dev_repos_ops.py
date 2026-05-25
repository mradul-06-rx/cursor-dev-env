#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_HOME = SCRIPT_DIR.parent
CONFIG_PATH = Path(os.environ.get("DEV_REPOS_CONFIG", REPO_HOME / "config" / "repos.json"))
DEV_ROOT = Path(os.environ.get("DEV_REPOS_ROOT", Path.home() / "workspace"))
CHECKOUT_ROOT = Path(os.environ.get("DEV_REPOS_CHECKOUT_ROOT", DEV_ROOT / "repos"))
WORKTREES_ROOT = Path(os.environ.get("DEV_REPOS_WORKTREES_ROOT", DEV_ROOT / "worktrees"))
GIT_PROTOCOL = os.environ.get("DEV_REPOS_GIT_PROTOCOL", "ssh")


def load_records(selectors: list[str]) -> list[dict]:
    """Loads selected repos from the manifest and fails on misspelled selectors."""
    with CONFIG_PATH.open() as config_file:
        config = json.load(config_file)

    default_branch = config.get("default_branch", "main")
    selector_set = set(selectors)
    matched: set[str] = set()
    records: list[dict] = []

    for repo in config.get("repos", []):
        full_name = f"{repo['org']}/{repo['name']}"
        if selector_set and repo["name"] not in selector_set and full_name not in selector_set:
            continue
        if repo["name"] in selector_set:
            matched.add(repo["name"])
        if full_name in selector_set:
            matched.add(full_name)
        repo = dict(repo)
        repo["default_branch"] = repo.get("default_branch", default_branch)
        records.append(repo)

    missing = selector_set - matched
    if missing:
        print(f"Unknown repo selector(s): {', '.join(sorted(missing))}", file=sys.stderr)
        raise SystemExit(2)
    return records


def run(command: list[str], cwd: Path | None = None, capture: bool = False) -> str:
    """Runs a command with inherited output unless callers need parsed stdout."""
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def git(path: Path, *args: str, capture: bool = False, check: bool = True) -> str:
    """Runs git inside a repo path and optionally lets callers handle failures."""
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and result.returncode != 0:
        if capture and result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    return result.stdout.strip() if capture and result.returncode == 0 else ""


def repo_path(repo: dict) -> Path:
    """Returns the canonical checkout path for a configured repository."""
    return CHECKOUT_ROOT / repo["org"] / repo["name"]


def repo_url(repo: dict) -> str:
    """Builds clone URLs without embedding credentials in config or images."""
    if GIT_PROTOCOL == "https":
        return f"https://github.com/{repo['org']}/{repo['name']}.git"
    return f"git@github.com:{repo['org']}/{repo['name']}.git"


def worktree_path(repo: dict, branch: str) -> Path:
    """Keeps worktrees grouped by org, repo, and a filesystem-safe branch slug."""
    branch_slug = branch.replace("/", "-").replace(" ", "-")
    return WORKTREES_ROOT / repo["org"] / repo["name"] / branch_slug


def is_dirty(path: Path) -> bool:
    """Detects local changes so bulk operations avoid overwriting work."""
    return bool(git(path, "status", "--porcelain", capture=True))


def is_repo(path: Path) -> bool:
    """Checks whether a checkout path already contains a git repository."""
    return (path / ".git").exists()


def ref_exists(path: Path, ref: str) -> bool:
    """Checks refs explicitly so branch/worktree decisions stay idempotent."""
    return subprocess.run(["git", "-C", str(path), "show-ref", "--verify", "--quiet", ref]).returncode == 0


def clone_repo(repo: dict) -> None:
    """Clones missing repos and refuses non-git directories at target paths."""
    path = repo_path(repo)
    full_name = f"{repo['org']}/{repo['name']}"
    if is_repo(path):
        print(f"exists: {full_name} -> {path}")
        return
    if path.exists():
        raise SystemExit(f"error: {path} exists but is not a git repo")
    path.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", repo_url(repo), str(path)])


def list_repo(repo: dict) -> None:
    """Prints manifest metadata for review before cloning or branching."""
    packages = ",".join(package_root or "." for package_root in repo.get("package_roots", []))
    print(f"{repo['org']}/{repo['name']}\tbranch={repo['default_branch']}\ttier={repo.get('tier', '')}\tpackages={packages}")


def status_repo(repo: dict) -> None:
    """Shows branch and dirty state for safe multi-repo decision making."""
    path = repo_path(repo)
    full_name = f"{repo['org']}/{repo['name']}"
    if not is_repo(path):
        print(f"missing: {full_name} -> {path}")
        return
    branch = git(path, "symbolic-ref", "--quiet", "--short", "HEAD", capture=True, check=False)
    branch = branch or git(path, "rev-parse", "--short", "HEAD", capture=True)
    state = "dirty" if is_dirty(path) else "clean"
    summary = git(path, "status", "-sb", capture=True).removeprefix("## ")
    print(f"{full_name}\t{branch}\t{state}\t{summary}")


def fetch_repo(repo: dict) -> None:
    """Fetches remote refs while leaving the current checkout untouched."""
    path = repo_path(repo)
    if not is_repo(path):
        print(f"skip missing: {repo['org']}/{repo['name']}")
        return
    git(path, "fetch", "--prune", "origin")


def update_repo(repo: dict) -> None:
    """Fast-forwards the current branch only when the repo is clean."""
    path = repo_path(repo)
    full_name = f"{repo['org']}/{repo['name']}"
    if not is_repo(path):
        print(f"skip missing: {full_name}")
        return
    if is_dirty(path):
        print(f"skip dirty: {full_name}")
        return
    git(path, "fetch", "--prune", "origin")
    upstream = git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", capture=True, check=False)
    if not upstream:
        print(f"skip no-upstream: {full_name}")
        return
    git(path, "pull", "--ff-only")


def sync_default_repo(repo: dict) -> None:
    """Moves the canonical checkout to the default branch and fast-forwards it."""
    clone_repo(repo)
    path = repo_path(repo)
    if is_dirty(path):
        print(f"skip dirty: {repo['org']}/{repo['name']}")
        return
    branch = repo["default_branch"]
    git(path, "fetch", "--prune", "origin")
    if ref_exists(path, f"refs/heads/{branch}"):
        git(path, "checkout", branch)
    else:
        git(path, "checkout", "-B", branch, f"origin/{branch}")
    git(path, "pull", "--ff-only", "origin", branch)


def branch_create_repo(repo: dict, branch: str) -> None:
    """Creates or checks out one named branch across selected repositories."""
    clone_repo(repo)
    path = repo_path(repo)
    if is_dirty(path):
        print(f"skip dirty: {repo['org']}/{repo['name']}")
        return
    git(path, "fetch", "--prune", "origin")
    if ref_exists(path, f"refs/heads/{branch}"):
        git(path, "checkout", branch)
    elif ref_exists(path, f"refs/remotes/origin/{branch}"):
        git(path, "checkout", "--track", f"origin/{branch}")
    else:
        sync_default_repo(repo)
        git(path, "checkout", "-b", branch)


def worktree_add_repo(repo: dict, branch: str) -> None:
    """Adds a worktree for parallel branch work without moving the main checkout."""
    clone_repo(repo)
    path = repo_path(repo)
    target = worktree_path(repo, branch)
    if target.exists():
        print(f"exists: {repo['org']}/{repo['name']} worktree -> {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    git(path, "fetch", "--prune", "origin")
    if ref_exists(path, f"refs/heads/{branch}"):
        git(path, "worktree", "add", str(target), branch)
    elif ref_exists(path, f"refs/remotes/origin/{branch}"):
        git(path, "worktree", "add", "--track", "-b", branch, str(target), f"origin/{branch}")
    else:
        git(path, "worktree", "add", "-b", branch, str(target), f"origin/{repo['default_branch']}")


def worktree_remove_repo(repo: dict, branch: str) -> None:
    """Removes an expected worktree path and skips repos where it is absent."""
    path = repo_path(repo)
    target = worktree_path(repo, branch)
    if not is_repo(path):
        print(f"skip missing: {repo['org']}/{repo['name']}")
        return
    if not target.exists():
        print(f"skip missing worktree: {repo['org']}/{repo['name']} -> {target}")
        return
    git(path, "worktree", "remove", str(target))


def package_roots_repo(repo: dict) -> None:
    """Prints package paths for optional install/search automation."""
    path = repo_path(repo)
    for package_root in repo.get("package_roots", []):
        print(path / package_root if package_root else path)

