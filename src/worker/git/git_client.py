from worker.config import settings
from worker.git.github_client import GitHubClient


class GitClient:
    client: GitHubClient

    def __init__(self) -> None:
        if settings.git_client == "github":
            self.client = GitHubClient()
        elif settings.git_client == "gitlab":
            raise Exception("GitLab client is not supported yet")
        else:
            raise Exception(f"{settings.git_client} client is not supported")
