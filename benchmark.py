#!/usr/bin/env python3
import csv
from itertools import dropwhile
import os
import random
import subprocess
import time

GRAPH_FNAME = "graph.csv"
JOBS_FNAME = "tmp_jobs.csv"
TIME_LIMIT = 120


def max_vertex():
    max_so_far = 0
    with open(GRAPH_FNAME, "r") as f:
        graphreader = csv.reader(f, delimiter=' ')
        for line in graphreader:
            if not line[0].startswith("#"):
                max_so_far = max(
                    max_so_far,
                    max(map(int, line))
                    )
    return max_so_far


def get_unique(path):
    assert path.__class__ == list, "must be list"
    assert path[0].__class__ == list, "must be listof lists"
    list_length = len(path)
    last_vertex = path[-1][1]
    unique_reversed = list(dropwhile(
        lambda x: x[1] == last_vertex,
        reversed(path)))
    unique = (list(reversed(unique_reversed))
              + [[len(unique_reversed), last_vertex]])
    assert len(unique) <= list_length
    return unique, len(unique)


def plan_with_n_jobs(n_jobs, N):
    random.seed(1)
    starts = list(range(N))
    goals = list(range(N))
    random.shuffle(starts)
    random.shuffle(goals)
    starts = starts[:n_jobs]
    goals = goals[:n_jobs]
    try:
        os.remove(JOBS_FNAME)
    except FileNotFoundError:
        pass
    with open(JOBS_FNAME, "w") as f:
        jobswriter = csv.writer(f, delimiter=' ')
        for j in range(n_jobs):
            jobswriter.writerow([starts[j], goals[j]])
    start_time = time.time()
    cp = subprocess.run(
        ["./run.sh", "7", GRAPH_FNAME, JOBS_FNAME, str(TIME_LIMIT)],
        stdout=subprocess.PIPE
        )
    t = time.time() - start_time
    print("Took " + format(t, ".1f") + "s")
    # print(cp.stdout.decode('utf-8'))
    paths = filter(
        lambda l: l.startswith("Agent"),
        cp.stdout.decode('utf-8').split('\n'))
    os.remove(JOBS_FNAME)

    lengths = []
    for path in paths:
        path = list(map(
            lambda s: list(map(int, s.split(':'))),
            path.split(' ')[2:]))
        path, path_length = get_unique(path)
        lengths.append(path_length)
    cost = sum(lengths) / float(n_jobs)
    return cost, t

N = max_vertex()
ns = [1, 2, 3, 5, 10, 20, 30, 50, 100]
# ns = range(1, 20)
cs = []
for n_jobs in ns:
    cost, _ = plan_with_n_jobs(n_jobs, N)
    cs.append(cost)
    print("n_jobs: %d -> c: %.2f"%(n_jobs, cost))
assert len(cs) == len(ns), "all ns should have a cost"
