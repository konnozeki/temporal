# services/git_service.py

import os
from functools import lru_cache
from pathlib import Path

from git import Repo

from config.configuration import GIT_REPO_PATH


class GitService:
    """
    Dịch vụ quản lý Git cho các thao tác với repository.
    - Khởi tạo với đường dẫn repository, URL remote và token xác thực.
    - Tự động clone repository nếu chưa tồn tại hoặc cập nhật nếu đã có.
    - Cung cấp các phương thức để ghi file, commit, tag và push lên remote.
    - Hỗ trợ cả GitHub và GitLab với token xác thực.
    - Tạo thư mục hệ thống nếu chưa tồn tại khi ghi file.
    - Đảm bảo sử dụng nhánh `dev` cho các thao tác.
    - Tham số khởi tạo:
        + `repo_path`: Đường dẫn đến thư mục chứa repository.
        + `remote_url`: URL của remote repository (GitHub hoặc GitLab).
        + `token`: Token xác thực để push lên remote repository.
    - Các phương thức:
        + `_inject_token(remote_url, token)`: Chèn token vào URL remote để xác thực.
        + `write_file(content_id, filename, content, system)`: Ghi nội dung vào file trong thư mục hệ thống.
        + `commit_and_tag(file_path, message, tag_name=None)`: Commit file đã thay đổi và tạo tag nếu cần.
        + `push_all()`: Đẩy tất cả thay đổi lên remote repository.
    """

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

    def _inject_token(self, remote_url: str, token: str) -> str:
        """
        Inject token vào URL remote để có thể push lên GitHub hoặc GitLab.
        - Nếu là GitLab, sử dụng định dạng `https://oauth2:TOKEN@` để xác thực.
        - Nếu là GitHub, sử dụng định dạng `https://TOKEN@`.
        """
        if not token:
            return remote_url
        # Nếu là GitLab: https://gitlab.com/user/repo.git → https://oauth2:TOKEN@gitlab.com/user/repo.git
        if "github" not in remote_url:
            return remote_url.replace("https://", f"https://oauth2:{token}@")
        # Nếu là GitHub
        return remote_url.replace("https://", f"https://{token}@")

    def write_file(self, content_id: str, filename: str, content: str, system: str) -> str:
        """
        Ghi nội dung vào file trong thư mục tương ứng với hệ thống.
        - Tạo thư mục nếu chưa tồn tại.
        - Trả về đường dẫn đầy đủ của file đã ghi.
        """
        dir_path = os.path.join(self.repo_path, system)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "w") as f:
            f.write(content)

        return file_path

    def build_relative_path(self, filename: str, system: str) -> str:
        return Path(system).joinpath(filename).as_posix()

    def commit_and_tag(self, file_path: str, message: str, tag_name: str = None):
        """
        Commit file đã thay đổi và tạo tag nếu cần.
        """
        self.repo.index.add([file_path])
        self.repo.index.commit(message)
        if tag_name:
            self.repo.create_tag(tag_name)

    def push_all(self):
        """
        Đẩy tất cả thay đổi lên remote repository.
        """
        origin = self.repo.remotes.origin
        results = origin.push()
        for result in results:
            print("Push result:", result.summary, "-", result.flags)

    def fetch(self):
        self.repo.remote("origin").fetch()

    def get_status(self) -> dict:
        try:
            staged_files = sorted({item.a_path for item in self.repo.index.diff("HEAD")})
        except Exception:
            staged_files = []
        unstaged_files = sorted({item.a_path for item in self.repo.index.diff(None)})
        untracked_files = sorted(self.repo.untracked_files)

        ahead = 0
        behind = 0
        remote_error = None
        try:
            self.fetch()
            tracking_branch = f"origin/{self.repo.active_branch.name}"
            counts = self.repo.git.rev_list("--left-right", "--count", f"HEAD...{tracking_branch}").split()
            ahead = int(counts[0])
            behind = int(counts[1])
        except Exception as exc:
            remote_error = str(exc)

        return {
            "branch": self.repo.active_branch.name,
            "dirty": self.repo.is_dirty(untracked_files=True),
            "ahead": ahead,
            "behind": behind,
            "staged_files": staged_files,
            "unstaged_files": unstaged_files,
            "untracked_files": untracked_files,
            "has_local_changes": bool(staged_files or unstaged_files or untracked_files),
            "has_remote_changes": behind > 0,
            "sync_needed": bool(staged_files or unstaged_files or untracked_files or behind > 0),
            "remote_error": remote_error,
        }

    def list_repo_xml_files(self) -> dict[str, dict[str, str]]:
        files: dict[str, dict[str, str]] = {}
        for path in Path(self.repo_path).rglob("*.xml"):
            if ".git" in path.parts:
                continue
            relative_path = path.relative_to(self.repo_path).as_posix()
            files[relative_path] = {
                "filename": path.name,
                "relative_path": path.relative_to(self.repo_path).as_posix(),
                "content": path.read_text(encoding="utf-8"),
            }
        return files


@lru_cache(maxsize=1)
def get_git_service() -> GitService:
    remote_url = os.getenv("GIT_REPO_URL", "").strip()
    token = os.getenv("GIT_ACCESS_TOKEN", "").strip()
    if not remote_url:
        raise ValueError("GIT_REPO_URL is not set")
    return GitService(repo_path=GIT_REPO_PATH, remote_url=remote_url, token=token)
