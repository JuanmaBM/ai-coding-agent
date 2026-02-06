from worker.config import Settings
from worker.git.github_client import GitHubClient


class GitClient:
    client: GitHubClient

    def __init__(self) -> None:
        if Settings.git_client == "github":
            self.client = GitHubClient()
        elif Settings.git_client == "gitlab":
            raise Exception("GitLab client is not supported yet")
        else:
            raise Exception(f"{Settings.git_client} client is not supported")
