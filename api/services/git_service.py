# services/git_service.py

import os
from git import Repo, GitCommandError
from pathlib import Path


class GitService:
    def __init__(self, repo_path: str, remote_url: str, token: str):
        self.repo_path = os.path.abspath(repo_path)  # resolve thành đường dẫn tuyệt đối
        self.remote_url = self._inject_token(remote_url, token)

        if not os.path.exists(self.repo_path) or not (Path(self.repo_path) / ".git").exists():
            print(f"[GitService] Cloning repo to: {self.repo_path}")
            self.repo = Repo.clone_from(self.remote_url, self.repo_path, branch="dev")
        else:
            self.repo = Repo(self.repo_path)
            self.repo.remote("origin").set_url(self.remote_url)
            self.repo.git.fetch()
            if self.repo.active_branch.name != "dev":
                self.repo.git.checkout("dev")
            self.repo.git.pull("origin", "dev")

        with self.repo.config_writer() as config:
            config.set_value("user", "name", "viettt")
            config.set_value("user", "email", "konno.zeki@gmail.com")
            config.set_value("user", "email", "konno.zeki@gmail.com")

    def _inject_token(self, remote_url: str, token: str) -> str:
        # Nếu là GitLab: https://gitlab.com/user/repo.git → https://oauth2:TOKEN@gitlab.com/user/repo.git
        if "github" not in remote_url:
            return remote_url.replace("https://", f"https://oauth2:{token}@")
        # Nếu là GitHub
        return remote_url.replace("https://", f"https://{token}@")

    def write_file(self, content_id: str, filename: str, content: str, system: str) -> str:
        dir_path = os.path.join(self.repo_path, system)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "w") as f:
            f.write(content)

        return file_path

    def commit_and_tag(self, file_path: str, message: str, tag_name: str = None):
        self.repo.index.add([file_path])
        self.repo.index.commit(message)
        if tag_name:
            self.repo.create_tag(tag_name)

    def push_all(self):
        origin = self.repo.remotes.origin
        results = origin.push()
        for result in results:
            print("Push result:", result.summary, "-", result.flags)
