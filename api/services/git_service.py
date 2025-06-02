# services/git_service.py

import os
from git import Repo, GitCommandError
from pathlib import Path


class GitService:
    def __init__(self, repo_path: str, remote_url: str, token: str):
        self.repo_path = repo_path
        self.remote_url = self._inject_token(remote_url, token)

        if not os.path.exists(repo_path) or not (Path(repo_path) / ".git").exists():
            print(f"[GitService] Cloning repo to: {repo_path}")
            self.repo = Repo.clone_from(self.remote_url, repo_path)
        else:
            self.repo = Repo(repo_path)
            self.repo.remote("origin").set_url(self.remote_url)

        # Cấu hình user cho commit
        with self.repo.config_writer() as config:
            config.set_value("user", "name", "Zeki System")
            config.set_value("user", "email", "zeki@domain.com")

    def _inject_token(self, remote_url: str, token: str) -> str:
        # Nếu là GitLab: https://gitlab.com/user/repo.git → https://oauth2:TOKEN@gitlab.com/user/repo.git
        if "gitlab" in remote_url:
            return remote_url.replace("https://", f"https://oauth2:{token}@")
        # Nếu là GitHub
        return remote_url.replace("https://", f"https://{token}@")

    def write_file(self, content_id: str, version: int, content: str) -> str:
        dir_path = os.path.join(self.repo_path, content_id)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, f"v{version}.xml")
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def commit_and_tag(self, file_path: str, message: str, tag_name: str):
        self.repo.index.add([file_path])
        self.repo.index.commit(message)
        self.repo.create_tag(tag_name)

    def push_all(self):
        self.repo.remotes.origin.push()
        self.repo.remotes.origin.push("--tags")

    def get_versions(self, content_id: str):
        tags = self.repo.tags
        return [tag.name for tag in tags if tag.name.startswith(f"{content_id}_v")]

    def read_file_at_tag(self, tag_name: str, file_path: str) -> str:
        commit = self.repo.commit(tag_name)
        blob = commit.tree / file_path
        return blob.data_stream.read().decode()
