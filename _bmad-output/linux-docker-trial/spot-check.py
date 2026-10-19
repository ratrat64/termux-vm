"""LD01 only: check fresh contexts, write markers, probe approved public targets.

Run with Python 3, --image SHA256_ID --trial-dir PRIVATE_TRIAL_DIRECTORY.
Does not create containers, read VPN material, or start a VPN.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import re
import subprocess


def run(*command):
    return subprocess.check_output(command, text=True, timeout=30).strip()


def inside(container, *command):
    return run("docker", "exec", container, *command)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--trial-dir", type=Path, required=True)
    args = parser.parse_args()
    trial = args.trial_dir.resolve(strict=True)
    check(trial.parent == Path("/tmp/opencode"), "trial directory parent mismatch")
    check(trial.name.startswith("linux-docker-sharing-ld01."), "trial directory name mismatch")
    check(re.fullmatch(r"sha256:[0-9a-f]{64}", args.image), "expected a complete immutable image ID")
    evidence = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "image": args.image, "checks": {}, "status": "FAIL"}
    checks = evidence["checks"]
    try:
        a, b = "tvm-share-ld01-a", "tvm-share-ld01-b"
        resources = {r["name"]: r for r in json.loads((trial / "resources.json").read_text())["resources"]}
        labels = {"task": "linux-docker-sharing-trial", "trial": "ld01",
                  "owner": "opencode-linux-trial-preparation"}
        containers = json.loads(run("docker", "inspect", a, b))
        homes = []
        for obj in containers:
            name = obj["Name"].lstrip("/")
            check(all(obj["Config"]["Labels"].get(k) == v for k, v in labels.items()), f"{name}: container ownership mismatch")
            check(obj["Id"] == resources[name]["id"], f"{name}: recorded container ID mismatch")
            check(obj["Image"] == args.image, f"{name}: immutable image mismatch")
            check(obj["State"]["Running"], f"{name}: container is not running")
            check(obj["Config"]["User"] == "1001:1001", f"{name}: default user mismatch")
            host = obj["HostConfig"]
            check(not host["Privileged"] and host["NetworkMode"] != "host", f"{name}: unexpected privileged/host networking")
            check(host["CapDrop"] == ["ALL"], f"{name}: capability drop mismatch")
            check("no-new-privileges" in host["SecurityOpt"], f"{name}: no-new-privileges missing")
            check({cap.removeprefix("CAP_") for cap in host["CapAdd"] or []} == ({"NET_ADMIN"} if name == a else set()), f"{name}: capability grant mismatch")
            devices = host["Devices"] or []
            expected_devices = [{"PathOnHost": "/dev/net/tun", "PathInContainer": "/dev/net/tun", "CgroupPermissions": "rw"}] if name == a else []
            check(devices == expected_devices, f"{name}: device source/destination/permission mismatch")
            limits = {"Memory": 512 * 1024 * 1024, "MemorySwap": 512 * 1024 * 1024,
                      "NanoCpus": 1000000000, "PidsLimit": 128}
            check(all(host[k] == v for k, v in limits.items()), f"{name}: resource limit mismatch")
            check(host["RestartPolicy"]["Name"] == "no", f"{name}: restart policy mismatch")
            network_name = "tvm-share-ld01-net-" + name[-1]
            attached = obj["NetworkSettings"]["Networks"]
            check(set(attached) == {network_name}, f"{name}: network attachment mismatch")
            network = json.loads(run("docker", "network", "inspect", network_name))[0]
            check(network["Id"] == resources[network_name]["id"] == attached[network_name]["NetworkID"], f"{name}: recorded network ID mismatch")
            check(all(network["Labels"].get(k) == v for k, v in labels.items()), f"{name}: network ownership mismatch")
            mounts = {m["Destination"]: m for m in obj["Mounts"]}
            check(set(mounts) == {"/home/session", "/project"}, f"{name}: mount destinations mismatch")
            check(mounts["/project"]["Type"] == "bind" and mounts["/project"]["Source"] == str(trial / "project"), f"{name}: scratch bind mismatch")
            check(mounts["/home/session"]["Type"] == "volume", f"{name}: home is not a volume")
            homes.append(mounts["/home/session"]["Name"])
            check(homes[-1] == "tvm-share-ld01-home-" + name[-1], f"{name}: home volume name mismatch")
            volume = json.loads(run("docker", "volume", "inspect", homes[-1]))[0]
            check(all(volume["Labels"].get(k) == v for k, v in labels.items()), f"{name}: home volume ownership mismatch")
            checks[name] = {"id": obj["Id"], "mounts": obj["Mounts"], "labels": labels,
                             "networks": list(obj["NetworkSettings"]["Networks"]),
                            "network_id": network["Id"], "home": homes[-1], "volume_labels": volume["Labels"],
                            "cap_add": host["CapAdd"], "devices": devices,
                            "runtime_config": {k: host[k] for k in (*limits, "RestartPolicy", "CapDrop", "SecurityOpt", "Privileged", "NetworkMode")}}
        check(len(set(homes)) == 2, "home volumes are not distinct")
        namespaces = [os.readlink("/proc/self/ns/net")]
        namespaces += [inside(c, "readlink", "/proc/self/ns/net") for c in (a, b)]
        check(len(set(namespaces)) == 3, "host/A/B network namespaces are not distinct")
        checks["network_namespaces"] = namespaces

        payload = (
            "import json,os,time; "
            "print(json.dumps(dict(shell_pid=os.getppid(),uid=os.getuid(),"
            "home=os.environ['HOME'],net=os.readlink('/proc/self/ns/net')))); time.sleep(2)"
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(inside, a, "bash", "-c", 'python3 -c "$1"; :', "--", payload)
                       for _ in range(2)]
            shells = [json.loads(f.result()) for f in futures]
        check(shells[0]["shell_pid"] != shells[1]["shell_pid"], "joined shell PIDs are not distinct")
        check(all(s["uid"] == 1001 and s["home"] == "/home/session"
                  and s["net"] == namespaces[1] for s in shells), "joined shell user/home/namespace mismatch")
        checks["joined_shells"] = shells
        for c in (a, b):
            inside(c, "python3", "-c", "from pathlib import Path; import sys; "
                   "Path.home().joinpath('ld01-marker').write_text(sys.argv[1])", c)
        for c in (a, b):
            check(inside(c, "cat", "/home/session/ld01-marker") == c, f"{c}: private home marker mismatch")
        inside(a, "python3", "-c", "from pathlib import Path; "
               "Path('/project/ld01-shared').write_text('visible-from-a')")
        check(inside(b, "cat", "/project/ld01-shared") == "visible-from-a", "sibling scratch visibility mismatch")
        check((trial / "project/ld01-shared").read_text() == "visible-from-a", "host scratch visibility mismatch")
        checks["private_markers_and_selected_shared_file"] = "PASS; synthetic data only"

        for c in (a, b):
            checks[c]["shell_cap_eff"] = inside(c, "bash", "-c",
                'while read -r key value; do if [ "$key" = CapEff: ]; then printf "%s" "$value"; fi; done < /proc/self/status')
            check(int(checks[c]["shell_cap_eff"], 16) == 0, f"{c}: ordinary shell has effective capabilities")
            checks[c]["resolver"] = inside(c, "cat", "/etc/resolv.conf")
            checks[c]["routes"] = inside(c, "ip", "-j", "route", "show", "table", "all")
            checks[c]["ipv6_routes"] = inside(c, "ip", "-6", "-j", "route", "show", "table", "all")
            checks[c]["public_probe"] = json.loads(inside(c, "python3", "-c",
                "import socket,json; answers=socket.getaddrinfo('example.com',443,type=socket.SOCK_STREAM); "
                "s=socket.create_connection(('1.1.1.1',443),timeout=10); "
                "print(json.dumps(dict(dns=sorted({a[4][0] for a in answers}),peer=s.getpeername()))); s.close()"))
        run("docker", "exec", "--user", "0", a, "ip", "tuntap", "add", "dev", "ld01probe", "mode", "tun")
        try:
            checks["a_tun"] = inside(a, "ip", "-j", "link", "show", "dev", "ld01probe")
        finally:
            run("docker", "exec", "--user", "0", a, "ip", "link", "delete", "dev", "ld01probe")
        evidence["status"] = "PASS"
    except Exception as error:
        evidence["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        evidence["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        path = trial / ("spot-check-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        with open(path, "x", opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
            json.dump(evidence, stream, indent=2)
        print(f"{evidence['status']}: {path}")


if __name__ == "__main__":
    main()
