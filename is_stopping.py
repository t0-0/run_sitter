import json
import os
import subprocess
import time

import requests
import schedule
import wandb

flag = True


def job(run_path, file_path):
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

                    if now_step_per_sec * 3 < prev_step_per_sec:
                        webhook_url = "https://hooks.slack.com/services/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"
                        text = f"{run.name}の実行が終了または不明な理由で停止しました"
                        requests.post(webhook_url, data=json.dumps({"text": text}))
                        global flag
                        flag = False
                else:
                    with open(file_path, "w") as f:
                        f.write(f"{lines[1][0]},{lines[1][1]}\n")
                        f.write(f"{lines[2][0]},{lines[2][1]}\n")
                        f.write(f"{run.summary.get('_step', 0)},{time.time()}")
            else:
                if run.summary.get("_step", 0) != lines[-1][0]:
                    with open(file_path, "a") as f:
                        f.write(f"\n{run.summary.get('_step', 0)},{time.time()}")

    else:
        with open(file_path, "w") as f:
            f.write(f"{run.summary.get('_step', 0)},{time.time()}")


if __name__ == "__main__":
    run_path = "your/wandb/run/path"
    file_path = "log/txt/file"

    if os.path.isfile(file_path):
        subprocess.call(["rm", file_path])

    schedule.every(10).minutes.do(job, run_path=run_path, file_path=file_path)
    while flag:
        schedule.run_pending()
        time.sleep(1)
