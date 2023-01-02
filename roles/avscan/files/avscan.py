#!/usr/bin/env python3

import argparse
import os
import subprocess
from typing import Iterable

QUARANTINE_PATH: str = os.path.expanduser("~/quarantined")


def scan(extra_args: Iterable[str]):
    scan_result = subprocess.run(
        [
            "/opt/local/bin/clamdscan",
            "--multiscan",
            "--infected",
            "--no-summary",
            "--fdpass",
        ]
        + extra_args,
        stdout=subprocess.PIPE,
        check=False
    )
    if scan_result.returncode == 1:
        output = scan_result.stdout.decode("utf-8")
        quarantine_files(
            line.split(": ", maxsplit=1)[0] for line in output.splitlines()
        )
        notify_user_about_infections(output)
    else:
        scan_result.check_returncode()


def scan_file_list(file_list_path: str):
    scan(["--file-list", file_list_path])


def scan_paths(paths: Iterable[str]):
    files = [path for path in paths if os.path.isfile(path)]
    if files:
        scan(files)


def quarantine_path(path: str, suffix: int) -> str:
    suffix = f".{suffix}" if suffix > 0 else ""
    filename, ext = os.path.splitext(os.path.basename(path))
    return os.path.join(QUARANTINE_PATH, f"{filename}{suffix}{ext}")


def quarantine_files(paths: Iterable[str]):
    if not os.path.exists(QUARANTINE_PATH):
        os.mkdir(QUARANTINE_PATH)

    for path in paths:
        suffix = 0
        while os.path.exists(dest := quarantine_path(path, suffix)):
            suffix += 1
        try:
            os.rename(path, dest)
            os.chmod(dest, 0o200)
        except OSError as err:
            display_notitfication(
                "Failed to quarantine", f"Failed to quarantine infected file {path}."
            )


def display_notitfication(title: str, msg: str, *, subtitle: str = None):
    escaped_msg = msg.replace('"', r"\"")
    escaped_title = title.replace('"', r"\"")
    command = f'display notification "{escaped_msg}" with title "{escaped_title}"'
    if subtitle:
        escaped_subtitle = subtitle.replace('"', r"\"")
        command += f' subtitle "{escaped_subtitle}"'
    subprocess.check_call(["/usr/bin/osascript", "-e", command])


def notify_user_about_infections(msg: str):
    display_notitfication("Infected files", msg, subtitle=f"moved to {QUARANTINE_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan files with clamd and quarantine infected files with notification."
    )
    parser.add_argument(
        "--file-list", nargs=1, required=False, help="Scan files from given file."
    )
    parser.add_argument("files", nargs="*", help="Files to scan")
    args = parser.parse_args()

    if args.file_list:
        scan_file_list(args.file_list[0])
    scan_paths(args.files)
