#!/usr/bin/env python2
import csv
from itertools import dropwhile
from matplotlib import pyplot as plt
import os
import logging
import random
import subprocess
import sys
import time

GRAPH_FNAME = "graph.csv"
GRAPH_UNDIR_FNAME = "graph_undir.csv"
TMP_JOBS_FNAME = "tmp_jobs.csv"
TIME_LIMIT = 60
SPLIT_LEVEL = 2

logging.getLogger().setLevel(logging.DEBUG)


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
    return unique


def plan_with_n_jobs(n_jobs, N, graph_fname):
    # random.seed(1)
    starts = list(range(N))
    goals = list(range(N))
    random.shuffle(starts)
    random.shuffle(goals)
    starts = starts[:n_jobs]
    goals = goals[:n_jobs]
    paths, t = plan(starts, goals, N, graph_fname)

    lengths = []
    for path in paths:
        lengths.append(len(path))
    cost = sum(lengths) / float(n_jobs)
    return cost, t


def plan(starts, goals, N, graph_fname, timeout=TIME_LIMIT):
    assert len(starts) == len(goals)
    with open(TMP_JOBS_FNAME, "w") as f:
        jobswriter = csv.writer(f, delimiter=' ')
        for j in range(len(starts)):
            jobswriter.writerow([starts[j], goals[j]])
    start_time = time.time()
    try:
        outstr = subprocess.check_output(
            [os.path.dirname(__file__) + "/run.sh",
             "7",
             graph_fname,
             TMP_JOBS_FNAME,
             str(timeout),
             str(SPLIT_LEVEL)],
            cwd=os.path.dirname(__file__)
        )
    except subprocess.CalledProcessError as e:
        logging.warn("CalledProcessError")
        logging.warn(e.output)
        return [], 0
    t = time.time() - start_time
    try:
        os.remove(TMP_JOBS_FNAME)
    except OSError:
        pass
    paths_str = filter(
        lambda l: l.startswith("Agent"),
        outstr.split('\n'))
    try:
        os.remove(TMP_JOBS_FNAME)
    except OSError:
        pass

    paths = []
    for path_str in paths_str:
        path = list(map(
            lambda s: list(map(int, s.split(':'))),
            path_str.split(' ')[2:]))
        path = get_unique(path)
        paths.append(path)
    return paths, t


def make_undir_graph_file(graph_fname, graph_undir_fname):
    def update_graph_dict(d, a, b):
        for (start, end) in [(a, b), (b, a)]:
            if start not in d.keys():
                d[start] = tuple()
            d[start] = d[start] + (end,)
        return d
    with open(graph_fname, 'r') as grf:
        grreader = csv.reader(grf, delimiter=' ')
        edges = {}
        for node in grreader:
            if not node[0].startswith("#"):
                for target in node[1:]:
                    edges = update_graph_dict(
                        d=edges,
                        a=int(node[0]),
                        b=int(target)
                    )
    with open(graph_undir_fname, 'w') as gruf:
        grufwriter = csv.writer(gruf, delimiter=' ')
        nodes = list(edges.keys())
        nodes.sort()
        for node in nodes:
            grufwriter.writerow([node] + list(edges[node]))


def write_results(results):
    with open("results.csv", 'w') as f:
        reswriter = csv.writer(f, delimiter=' ')
        for res in results:
            reswriter.writerow(res)


def read_results():
    out = tuple()
    with open("results.csv", 'r') as res:
        resreader = csv.reader(res, delimiter=' ')
        for line in resreader:
            out = out + (list(map(float, line)),)
    return out


if __name__ == '__main__':
    if sys.argv[1] == "eval":
        N = max_vertex()
        # ns = [1, 2, 3, 5, 10, 20, 30, 50, 100]
        # ns = range(1, 20)
        ns = range(25, 150, 25)
        if not os.path.exists(GRAPH_UNDIR_FNAME):
            make_undir_graph_file(GRAPH_FNAME, GRAPH_UNDIR_FNAME)
        results = (ns,)
        for graph_fname in [GRAPH_UNDIR_FNAME, GRAPH_FNAME]:
            cs = []
            ts = []
            print("graph_fname: %s" % graph_fname)
            for n_jobs in ns:
                cost, t = plan_with_n_jobs(n_jobs, N, graph_fname)
                cs.append(cost)
                ts.append(t)
                print("n_jobs: %3d | c: % 7.2f | t: % 7.2fs" %
                      (n_jobs, cost, t))
            assert len(cs) == len(ns), "all ns should have a cost"
            results = results + (cs, ts)
        write_results(results)
    elif sys.argv[1] == "plot":
        (ns, cs_u, ts_u, cs_d, ts_d) = read_results()
        x = range(len(ns))
        plt.style.use('bmh')
        fig, (ax_cost, ax_time) = plt.subplots(2, 1)
        fig.tight_layout()
        ax_cost.plot(x, cs_u, label='undirected')
        ax_cost.plot(x, cs_d, label='directed')
        ax_time.plot(x, ts_u, label='undirected')
        ax_time.plot(x, ts_d, label='directed')
        plt.setp(ax_cost, xticks=x, xticklabels=map(str, map(int, ns)),
                 title="Cost")
        plt.setp(ax_time, xticks=x, xticklabels=map(str, map(int, ns)),
                 title="Computation Time")
        ax_cost.legend()
        ax_time.legend()
        plt.show()
    else:
        assert False, "choose either eval or plot"
