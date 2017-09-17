#!/usr/bin/env python3

from datetime import datetime, timezone, timedelta
import subprocess
import os

def run_task(task_args):
    """ run a command line command, return its output or error object. """
    try:
        output=subprocess.check_output(task_args, encoding='utf8')
        return output
    except Exception as e:
        return e

def daily_tasks(dt: datetime):
    """ Tasks that need to run every day. """
    if not os.path.isdir(os.path.abspath('.database')):
        os.mkdir(os.path.abspath('.database'))
    if not os.path.isdir(os.path.abspath('.build')):
        os.mkdir(os.path.abspath('.build'))
    run_task(['python3', 'safaribooksonline/safaribooksonline.py', 'fetch'])
    run_task(['python3', 'safaribooksonline/safaribooksonline.py', 'generate'])

def weekly_tasks(dt: datetime):
    """ Tasks that need to run every week. """
    pass

if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    daily_tasks(now)
    weekly_tasks(now)
