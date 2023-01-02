#!/usr/bin/env python3

import argparse
import os.path
import subprocess
import sys
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from typing import Optional, TextIO


def is_on_ac_power() -> bool:
    return "Now drawing from 'AC Power'" in subprocess.check_output(
        ["/usr/bin/pmset", "-g", "ps"]
    ).decode("utf-8")


def get_time_last_run(timestamp_file: str) -> Optional[datetime]:
    if not os.path.exists(timestamp_file):
        return None
    with open(timestamp_file, "r") as f:
        return datetime.fromtimestamp(float(f.readline()))


def set_time_last_run(timestamp_file: str, time: datetime):
    with open(timestamp_file, "w") as f:
        f.write(str(time.timestamp()))


def gather_file_list(output: TextIO, basedir: str, modified_last_days: int = None):
    command = ["/usr/bin/find", basedir, "-type", "f", "-size", "+0"]
    if modified_last_days is not None:
        command += ["-mtime", f"-{modified_last_days}"]
    # Do not check return value as it might be != 0 when access to some files is prohibited.
    subprocess.call(command, stdout=output, stderr=subprocess.PIPE)


def scan_file_list(file_list: str, avscan_path: str):
    subprocess.check_call([avscan_path, "--file-list", file_list])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a full virus scan.")
    parser.add_argument(
        "--timestamp-file",
        nargs=1,
        required=True,
        help="File storing the scan timestamp.",
    )
    parser.add_argument(
        "--if-last-scan-age",
        type=int,
        nargs=1,
        required=False,
        help="Only run scan if the last scan age exceeds the given number of seconds.",
    )
    parser.add_argument(
        "--modified-last-days",
        type=int,
        nargs=1,
        required=False,
        help="Only scan file modified during the last n days.",
    )
    parser.add_argument(
        "--require-ac",
        action="store_true",
        help="Only run if Mac is connected to AC power.",
    )
    parser.add_argument(
        "--avscan-path",
        nargs=1,
        required=False,
        default=["avscan.py"],
        help="Path to avscan.py.",
    )
    parser.add_argument("basedirs", nargs="+", help="Directories to scan.")
    args = parser.parse_args()

    if args.require_ac and not is_on_ac_power():
        print("Skipping as not on AC power.")
        sys.exit(0)

    timestamp_file = os.path.expanduser(args.timestamp_file[0])
    started_at = datetime.now()
    last_run = get_time_last_run(timestamp_file)
    if (
        args.if_last_scan_age
        and last_run is not None
        and last_run + timedelta(seconds=args.if_last_scan_age[0]) > started_at
    ):
        print("Skipping scan as last scan is still recent.")
        sys.exit(0)

    for basedir in args.basedirs:
        with NamedTemporaryFile() as file_list:
            gather_file_list(
                file_list, os.path.expanduser(basedir), args.modified_last_days[0]
            )
            scan_file_list(file_list.name, args.avscan_path[0])

    set_time_last_run(timestamp_file, started_at)
