import os
import sys
import json
import shutil
import urllib.parse as urlparse
import subprocess
import base64
import glob
import re
import tempfile

def is_text(content_bytes):
    try:
        content_bytes.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False

def folder_to_json(folder_path, folder_name_override=None):
    files = []
    for root, dirs, filenames in os.walk(folder_path):
        if '.git' in dirs:
            dirs.remove('.git')
        for name in filenames:
            if name.startswith('.git'):
                continue
            filepath = os.path.join(root, name)
            relpath = os.path.relpath(filepath, folder_path).replace(os.sep, "/")
            with open(filepath, "rb") as f:
                content = f.read()
                if is_text(content):
                    files.append({
                        "path": relpath,
                        "content": urlparse.quote(content.decode('utf-8')),
                        "storetype": "URI"
                    })
                else:
                    files.append({
                        "path": relpath,
                        "content": base64.b64encode(content).decode('ascii'),
                        "storetype": "b64"
                    })
    return {
        "folder": folder_name_override if folder_name_override else os.path.basename(folder_path),
        "files": files
    }

def get_repo_name_from_git_config(git_folder):
    config_path = os.path.join(git_folder, ".git", "config")
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            if "url =" in line:
                url = line.split("=", 1)[1].strip()
                return url.rstrip("/").split("/")[-1].replace(".git", "")
    return None

def clone_and_convert(git_url):
    with tempfile.TemporaryDirectory() as tmp:
        print(f"🔃 Cloning {git_url} ...")
        result = subprocess.run(["git", "clone", "--depth", "1", git_url, tmp], capture_output=True)
        if result.returncode != 0:
            print("❌ Git clone failed:")
            print(result.stderr.decode())
            sys.exit(1)
        repo_name = get_repo_name_from_git_config(tmp) or "ClonedRepo"
        print(f"✅ Repo detected as: {repo_name}")
        return folder_to_json(tmp, folder_name_override=repo_name), repo_name

def write_from_qf2(json_data, use_current=False):
    target_folder = os.getcwd() if use_current else json_data['folder']
    if not use_current and os.path.exists(target_folder):
        print(f"⚠️ Deleting existing folder: {target_folder}")
        shutil.rmtree(target_folder)

    for file in json_data['files']:
        path = os.path.join(target_folder, file['path']) if not use_current else os.path.join(os.getcwd(), file['path'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if file.get("storetype", "URI") == "b64":
            with open(path, 'wb') as f:
                f.write(base64.b64decode(file['content']))
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(urlparse.unquote(file['content']))
        print(f"✅ Created: {path}")

def show_help():
    help_text = """
QStore CLI - QStore.py

Usage:
  python QStore.py --git <repo-url>        Convert Git repo (excludes .git) to QF2 .QF2 file
  python QStore.py --make <folder>         Convert local folder to QF2 (.QF2 file)
  python QStore.py file.QF2 [--uc]         Build files from a saved QF2 file
  python QStore.py [--uc]                  Paste QF2 JSON manually and build

Options:
  --git <repo-url>       Clone and convert a Git repo (ignores .git)
  --make <folder>        Convert folder to QF2 JSON file
  --uc / --use-current   Output files into current directory
  --help / --h / -h      Show this help message
"""
    print(help_text)

if __name__ == "__main__":
    args = sys.argv[1:]
    use_current = "--uc" in args or "--use-current" in args
    file_args = [a for a in args if not a.startswith('--') and a.endswith(('.qf2', '.QF2', '.txt'))]

    if any(arg in ["--help", "--h", "-h"] for arg in args):
        show_help()
        sys.exit(0)

    if "--git" in args:
        try:
            idx = args.index("--git")
            url = args[idx + 1]
            result, repo_name = clone_and_convert(url)
            out_file = f"{repo_name}.QF2"
            with open(out_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"✅ Saved QF2 file to: {out_file}")
        except Exception as e:
            print("❌ Error during --git:", e)
        sys.exit()

    if "--make" in args:
        try:
            idx = args.index("--make")
            pattern = args[idx + 1]
            matches = glob.glob(pattern)
            if not matches:
                print("❌ No folder matched:", pattern)
                sys.exit(1)
            folder_path = matches[0]
            result = folder_to_json(folder_path)
            out_file = f"{result['folder']}.QF2"
            with open(out_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"✅ Saved QF2 file to: {out_file}")
        except Exception as e:
            print("❌ Error during --make:", e)
        sys.exit()

    if file_args:
        try:
            with open(file_args[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                write_from_qf2(data, use_current=use_current)
        except Exception as e:
            print(f"❌ Failed to load {file_args[0]}:", e)
        sys.exit()

    print("📝 Paste QF2 JSON below (Ctrl+D to finish):")
    try:
        input_text = sys.stdin.read()
        data = json.loads(input_text)
        write_from_qf2(data, use_current=use_current)
    except Exception as e:
        print("❌ Error processing input:", e)