"""List, inspect and join existing LD01 contexts using normal Docker access."""

import argparse
import json
import os
import re
import subprocess
import sys


PREFIX = "tvm-share-ld01-"
LABELS = {"task": "linux-docker-sharing-trial", "trial": "ld01",
          "owner": "opencode-linux-trial-preparation"}
STATES = {"created", "running", "paused", "restarting", "removing", "exited", "dead"}
LABEL_FORMAT = ','.join(
    '"' + key + '":{{json (index .Config.Labels "' + key + '")}}'
    for key in LABELS
)
LIST_FORMAT = ('{"name":{{json .Names}},"state":{{json .State}},' + ','.join(
    '"' + key + '":{{json (.Label "' + key + '")}}' for key in LABELS
) + '}')
# Count HOME entries without returning any of the environment to the client.
INSPECT_FORMAT = (
    '{{$seen := false}}{{$unique := true}}{{$home := false}}'
    '{{range .Config.Env}}'
    '{{if eq (index (split . "=") 0) "HOME"}}'
    '{{if $seen}}{{$unique = false}}{{end}}'
    '{{$seen = true}}{{$home = eq . "HOME=/home/session"}}'
    '{{end}}{{end}}'
    '{"name":{{json .Name}},"id":{{json .Id}},' + LABEL_FORMAT + ','
    '"state":{{json .State.Status}},"running":{{json .State.Running}},'
    '"paused":{{json .State.Paused}},"restarting":{{json .State.Restarting}},'
    '"dead":{{json .State.Dead}},"user":{{json .Config.User}},'
    '"workdir":{{json .Config.WorkingDir}},'
    '"privileged":{{json .HostConfig.Privileged}},'
    '"home_supported":{{and $seen $unique $home}}}'
)


def metadata(*arguments):
    try:
        result = subprocess.run(
            ["docker", *arguments], stdin=subprocess.DEVNULL,
            capture_output=True, text=True, check=True, timeout=30,
        )
        records = [json.loads(line) for line in result.stdout.split("\n") if line.strip()]
    except (OSError, subprocess.SubprocessError, ValueError):
        raise ValueError("Docker metadata request failed") from None
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("invalid Docker metadata")
    return records


def eligible(record):
    name = record.get("name")
    return (isinstance(name, str) and name.startswith(PREFIX)
            and all(record.get(key) == value for key, value in LABELS.items()))


def identity_supported(record):
    return (record.get("user") == "1001:1001"
            and record.get("workdir") == "/project"
            and record.get("home_supported") is True
            and record.get("privileged") is False)


def valid_state(record):
    state = record.get("state")
    if not isinstance(state, str) or state not in STATES:
        raise ValueError("invalid Docker state metadata")
    return state


def select(name):
    if not name.startswith(PREFIX):
        raise ValueError("unknown or ineligible context")
    records = metadata("container", "inspect", "--format", INSPECT_FORMAT, "--", name)
    if len(records) != 1:
        raise ValueError("unknown or ineligible context")
    record = records[0]
    # Docker inspection can also resolve IDs/prefixes; only accept the exact name.
    if record.get("name") != "/" + name:
        raise ValueError("unknown or ineligible context")
    record["name"] = name
    if not eligible(record):
        raise ValueError("unknown or ineligible context")
    identifier = record.get("id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{64}", identifier):
        raise ValueError("invalid Docker container ID metadata")
    valid_state(record)
    return record


def list_contexts():
    filters = ["--filter", "name=" + PREFIX]
    for key, value in LABELS.items():
        filters.extend(["--filter", f"label={key}={value}"])
    records = metadata("container", "ls", "--all", *filters, "--format", LIST_FORMAT)
    contexts = sorted((r for r in records if eligible(r)), key=lambda r: r["name"])
    rows = [(r["name"], valid_state(r)) for r in contexts]
    if not rows:
        print("No eligible LD01 contexts found.")
        return
    print("NAME\tSTATE")
    for name, state in rows:
        print(f"{name}\t{state}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list existing LD01 contexts, including stopped ones")
    for command in ("status", "join"):
        subparser = commands.add_parser(command)
        subparser.add_argument("name", metavar="NAME", help="exact existing Docker container name")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            list_contexts()
        else:
            record = select(args.name)
            supported = identity_supported(record)
            if args.command == "status":
                print("NAME\tSTATE\tIDENTITY_SUPPORTED")
                print(f'{record["name"]}\t{record["state"]}\t{str(supported).lower()}')
            else:
                if not supported:
                    raise ValueError("unsupported daily identity configuration")
                if (record["state"] != "running" or record.get("running") is not True
                        or any(record.get(flag) is not False
                               for flag in ("paused", "restarting", "dead"))):
                    raise ValueError("context is not running and joinable")
                if not (sys.stdin is not None and sys.stdout is not None
                        and sys.stdin.isatty() and sys.stdout.isatty()):
                    raise ValueError("interactive stdin and stdout TTY required")
                command = ["docker", "exec", "-it", "--user", "1001:1001",
                           "--workdir", "/project", record["id"], "bash", "--noprofile", "--norc"]
                try:
                    os.execvp("docker", command)
                except OSError:
                    raise ValueError("could not execute Docker") from None
    except ValueError as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
