import sys
import clr
from collections import namedtuple

from .parser import get_installed_package_data

from ..logger import get_logger
logger = get_logger(__name__)

from ..config import HOME_DIR
from ..git import git
from ..userconfig import user_settings

from System import DateTime, DateTimeOffset


# Generic named tuple for passing repository information to other modules
PyRevitRepoInfo = namedtuple('PyRevitRepoInfo', ['directory', 'head_name', 'last_commit_hash', 'repo'])


# fixme: remove credentials on final release

def hndlr(url, uname, types):
    up = git.UsernamePasswordCredentials()
    up.Username = 'eirannejad@gmail.com'
    up.Password = 'ehsan2010'
    return up


def _make_pull_options():
    pull_ops = git.PullOptions()
    pull_ops.FetchOptions = git.FetchOptions()
    pull_ops.FetchOptions.CredentialsProvider = git.Handlers.CredentialsHandler(hndlr)
    return pull_ops


def _make_fetch_options():
    fetch_ops = git.FetchOptions()
    fetch_ops.CredentialsProvider = git.Handlers.CredentialsHandler(hndlr)
    return fetch_ops


def _make_pull_signature():
    return git.Signature('eirannejad', 'eirannejad@gmail.com', DateTimeOffset(DateTime.Now))


def get_pyrevit_repo():
    try:
        repo = git.Repository(HOME_DIR)
        return PyRevitRepoInfo(repo.Info.WorkingDirectory, repo.Head.Name, repo.Head.Tip.Id.Sha, repo)
    except Exception as err:
        logger.error('Can not create repo from home directory: {}'.format(HOME_DIR))


def get_thirdparty_pkg_repos():
    # get a list of all directories that could include packages
    # and ask parser for package info object
    pkgs = []
    logger.debug('Finding installed repos...')
    for root_dir in user_settings.get_package_root_dirs():
        pkg_info_list = get_installed_package_data(root_dir)
        for pkg_info in pkg_info_list:
            if pkg_info and git.Repository.IsValid(pkg_info.directory):
                pkgs.append(pkg_info)

    logger.debug('Valid third-party packages for update: {}'.format(pkgs))

    repos = []
    for pkg_info in pkgs:
        try:
            repo = git.Repository(pkg_info.directory)
            repo_info = PyRevitRepoInfo(repo.Info.WorkingDirectory, repo.Head.Name, repo.Head.Tip.Id.Sha, repo)
            repos.append(repo_info)
        except Exception as err:
            logger.error('Can not create repo from home directory: {}'.format(pkg_info.directory))

    return repos


def get_all_available_repos():
    repo_info_list = [get_pyrevit_repo()]      # pyrevit main repo
    repo_info_list.extend(get_thirdparty_pkg_repos())   # add all thirdparty repos
    return repo_info_list


def update_pyrevit(repo_info):
    # fixme: if core update is available, pull to a new branch, then merge on pyrevit restart
    repo = repo_info.repo
    logger.debug('Updating repo: {}'.format(repo_info.directory))
    head_msg = str(repo.Head.Tip.Message).replace('\n','')
    logger.debug('Current head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
    try:
        repo.Network.Pull(_make_pull_signature(), _make_pull_options())
        logger.debug('Successfully updated repo: {}'.format(repo_info.directory))
        head_msg = str(repo.Head.Tip.Message).replace('\n','')
        logger.debug('New head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
        return True

    except Exception as pull_err:
        logger.error('Failed updating: {} | {}'.format(repo_info.directory, pull_err))

    return False


def has_pending_updates(repo_info):
    repo = repo_info.repo
    logger.debug('Fetching updates for: {}'.format(repo_info.directory))
    repo_branches = repo.Branches
    logger.debug('Repo branches: {}'.format([b for b in repo_branches]))

    for remote in repo.Network.Remotes:
        logger.debug('Fetching remote: {} of {}'.format(remote.Name, repo_info.directory))
        try:
            repo.Network.Fetch(remote, _make_fetch_options())
        except Exception as fetch_err:
            logger.error('Failed fetching: {} | {}'.format(repo_info.directory, str(fetch_err).replace('\n', '')))

    for branch in repo_branches:
        if not branch.IsRemote:
            try:
                if branch.TrackedBranch:
                    logger.debug('Comparing heads: {} of {}'.format(branch.CanonicalName,
                                                                    branch.TrackedBranch.CanonicalName))
                    hist_div = repo.ObjectDatabase.CalculateHistoryDivergence(branch.Tip, branch.TrackedBranch.Tip)
                    if hist_div.BehindBy > 0:
                        return True
            except Exception as compare_err:
                logger.error('Can not compare branch {} in repo: {} | {}'.format(branch,
                                                                                 repo,
                                                                                 str(compare_err).replace('\n', '')))

    return False
