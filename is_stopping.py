import argparse
import json
import os
import requests
import subprocess
import time

import schedule
import wandb


exit_flag = True


def parse_args():
    parser = argparse.ArgumentParser("In addition to the arguments below, os.environ['SLACK_WEBHOOK_URL'] is required.")
    parser.add_argument("run_path", type=str, nargs=1)
    parser.add_argument("-f", "--file_path", type=str, default="./log.txt")
    parser.add_argument("-i", "--interval_in_min", type=int, default=10)
    parser.add_argument("-s", "--step_per_sec_factor", type=float, default=4)
    return parser.parse_args()


def main():
    args = parse_args()
    slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]

    if os.path.isfile(args.file_path):
        subprocess.call(["rm", args.file_path])

    schedule.every(args.interval_in_min).minutes.do(
        job,
        run_path=args.run_path,
        file_path=args.file_path,
        step_per_sec_factor=args.step_per_sec_factor,
        slack_webhook_url=slack_webhook_url,
    )
    while exit_flag:
        schedule.run_pending()
        time.sleep(5)


def job(run_path, file_path, step_per_sec_factor, slack_webhook_url):
    run = wandb.Api().run(run_path)

    if os.path.isfile(file_path):
        with open(file_path, "r") as f:
            lines = [line.rstrip() for line in f.readlines()]
            lines = list(map(lambda line: list(map(float, line.split(","))), lines))
        if len(lines) == 3:
            if run.summary.get("_step", 0) == lines[-1][0]:
                prev_step_per_sec = (lines[1][0] - lines[0][0]) / (
                    lines[1][1] - lines[0][1]
                )

                now_step_per_sec = (run.summary.get("_step", 0) - lines[1][0]) / (
                    time.time() - lines[1][1]
                )

                if now_step_per_sec * step_per_sec_factor < prev_step_per_sec:
                    text = f"<!channel>\n{run.name}: Execution terminated or failed for unknown reason."
                    requests.post(slack_webhook_url, data=json.dumps({"text": text}))
                    global exit_flag
                    exit_flag = False
            else:
                with open(file_path, "w") as f:
                    f.write(f"{lines[1][0]},{lines[1][1]}\n")
                    f.write(f"{lines[2][0]},{lines[2][1]}\n")
                    f.write(f"{run.summary.get('_step', 0)},{time.time()}")
        else:
            if run.summary.get("_step", 0) != lines[-1][0]:
                with open(file_path, "w") as f:
                    for i in range(len(lines)):
                        f.write(f"{lines[i][0]},{lines[i][1]}\n")
                    f.write(f"{run.summary.get('_step', 0)},{time.time()}")

    else:
        with open(file_path, "w") as f:
            f.write(f"{run.summary.get('_step', 0)},{time.time()}")


if __name__ == "__main__":
    main()
