"""Tiny command line for the fixture company: fetches numbers from a server and prints their stats as JSON."""
import argparse
import json
import sys
import urllib.request


def main(argv=None):
    parser = argparse.ArgumentParser(prog="statscli")
    parser.add_argument("--url", required=True)
    parser.add_argument("--digits", type=int, default=1)
    args = parser.parse_args(argv)
    with urllib.request.urlopen(args.url + "/numbers", timeout=5) as response:
        values = json.load(response)["values"]
    print(json.dumps({"n": len(values), "mean": round(sum(values) / len(values), args.digits),
                      "stats": {"p99.9": max(values)}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
