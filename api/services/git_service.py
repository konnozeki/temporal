# import os
# import git
# from datetime import datetime

# GIT_REMOTE_URL = "git@gitlab.com:yourgroup/yourrepo.git"
# GIT_LOCAL_PATH = "/tmp/git_repo"  # hoặc cấu hình từ ENV


# def clone_or_pull_repo():
#     if not os.path.exists(GIT_LOCAL_PATH):
#         print("Cloning repo...")
#         return git.Repo.clone_from(GIT_REMOTE_URL, GIT_LOCAL_PATH)
#     else:
#         print("Pulling latest...")
#         repo = git.Repo(GIT_LOCAL_PATH)
#         origin = repo.remotes.origin
#         origin.pull()
#         return repo


# def save_xml_to_repo(module: str, category: str, filename: str, content: str, commit_message: str = ""):
#     repo = clone_or_pull_repo()

#     target_dir = os.path.join(GIT_LOCAL_PATH, module, category)
#     os.makedirs(target_dir, exist_ok=True)

#     target_path = os.path.join(target_dir, filename)
#     with open(target_path, "w", encoding="utf-8") as f:
#         f.write(content)

#     repo.git.add(target_path)
#     repo.index.commit(commit_message or f"Update {filename} at {datetime.now()}")
#     repo.remotes.origin.push()

#     print(f"Pushed {filename} to remote git.")
#     return target_path
