import os
import sys
import json
import base64
import urllib.parse
import shutil
import requests
import tempfile
import subprocess

def uri_encode_file(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    try:
        text = data.decode('utf-8')
        return urllib.parse.quote(text), "URI"
    except UnicodeDecodeError:
        return base64.b64encode(data).decode(), "b64"

def save_qf2(folder_path, output_path):
    qf2 = {"folder": os.path.basename(folder_path), "files": []}
    for root, _, files in os.walk(folder_path):
        if ".git" in root: continue
        for f in files:
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, folder_path)
            content, storetype = uri_encode_file(fp)
            qf2["files"].append({
                "path": rel.replace("\\", "/"),
                "storetype": storetype,
                "content": content
            })
    with open(output_path, 'w', encoding='utf-8') as out:
        json.dump(qf2, out, indent=2)

def load_qf2(path_or_text):
    if os.path.exists(path_or_text):
        with open(path_or_text, encoding='utf-8') as f:
            return json.load(f)
    return json.loads(path_or_text)

def build_qf2(qf2_data, output_dir=None):
    folder = qf2_data["folder"]
    target = output_dir or folder
    os.makedirs(target, exist_ok=True)
    for file in qf2_data["files"]:
        fpath = os.path.join(target, file["path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        data = (base64.b64decode(file["content"]) if file["storetype"] == "b64"
                else urllib.parse.unquote(file["content"]))
        with open(fpath, 'wb') as out:
            out.write(data.encode() if isinstance(data, str) else data)
    print(f"✔ Built into {target}")

def git_to_qf2(repo_url, output=None):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "--depth=1", repo_url, tmp], stdout=subprocess.DEVNULL)
        repo_name = os.path.basename(repo_url.rstrip("/")).replace(".git", "")
        output_name = output or f"{repo_name}.QF2"
        save_qf2(tmp, output_name)
        print(f"✔ Saved as {output_name}")

def folder_to_qf2(folder_path, output=None):
    output_name = output or os.path.basename(folder_path.rstrip("/")) + ".QF2"
    save_qf2(folder_path, output_name)
    print(f"✔ Saved as {output_name}")

def print_help():
    print("""
QStore - QF2 (QStore File 2) Code Packager

Commands:
  python3 QStore.py git <repo_url> [optional_output.QF2]
  python3 QStore.py store <folder_path> [optional_output.QF2]
  python3 QStore.py open <QF2 file or ?current to paste> [optional_output_folder]
  python3 QStore.py <file.QF2>

Special options:
  ?current   Use current working directory for output (instead of folder in QF2)
  --help, -h Show this help menu
""")

def main():
    args = sys.argv[1:]
    if not args or '--help' in args or '-h' in args:
        print_help()
        return

    cmd = args[0]

    if cmd == "git" and len(args) >= 2:
        repo_url = args[1]
        output = args[2] if len(args) > 2 else None
        if output == "?current":
            output = os.path.basename(repo_url.rstrip("/")).replace(".git", "") + ".QF2"
        git_to_qf2(repo_url, output)

    elif cmd == "store" and len(args) >= 2:
        folder = args[1]
        output = args[2] if len(args) > 2 else None
        if output == "?current":
            output = os.path.basename(os.path.abspath(folder)) + ".QF2"
        folder_to_qf2(folder, output)

    elif cmd == "open" and len(args) >= 2:
        qf2_source = args[1]
        output_dir = args[2] if len(args) > 2 else None
        if qf2_source == "?current":
            print("Paste QF2 JSON below:")
            qf2_data = json.loads(sys.stdin.read())
        else:
            qf2_data = load_qf2(qf2_source)
        out = os.getcwd() if output_dir == "?current" else output_dir
        build_qf2(qf2_data, out)

    elif cmd.endswith(".QF2"):
        qf2_data = load_qf2(cmd)
        build_qf2(qf2_data)

    else:
        print("Unknown command. Use --help for instructions.")

if __name__ == "__main__":
    main()