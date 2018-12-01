# Copyright (c) 2018-present, Royal Bank of Canada.
# All rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.#
# Author: Yanshuai Cao

#!/usr/bin/python
from __future__ import print_function
import sys
import subprocess
import glob
import os
import sys
import argparse
from lite_tracer.tracker import u2b, b2u
import time


class Item(object):

    def __init__(self, line):
        self.line = line

        self.file_name = line.split(u2b(".txt:"))[0]+u2b(".txt")
        self.ctime = os.path.getctime(b2u(self.file_name))
        self.end_str = u2b("_searchable.txt:")
        self.start_str = u2b("settings_")

        self.hash_str = line.split(self.end_str)[0].split(self.start_str)[-1]
        self.param_str = line.split(self.end_str)[-1]

        tmp = [x.strip().split(u2b(':')) for x in self.param_str.split()]
        self.kwargs = dict([tuple(kv) for kv in tmp])


def main():
    parser = argparse.ArgumentParser(
        description="explore saved experiment results by matching hyperparameter flags")

    parser.add_argument('-d', '--lt_dir', type=str,
                        default='./lt_records', help="folder containing LT records")

    parser.add_argument('-i', '--include', type=str, nargs='+')
    parser.add_argument('-e', '--exclude', type=str, nargs='+')

    args = parser.parse_args()

    # search results
    setting_file_list = glob.glob(os.path.expanduser(
        os.path.join(args.lt_dir, "LT*LT/settings*searchable.txt")))

    if not len(setting_file_list):
        print('No match found')
        sys.exit()

    setting_files = ' '.join(setting_file_list)
    include_tags = args.include if args.include else []
    exclude_tags = args.exclude if args.exclude else []

    icommand = "grep -E '{}' {}".format('|'.join(include_tags), setting_files)

    # TODO: figure out why the non shell version fails so can avoid shell=True
    try:
        if exclude_tags:
            ecommand = "grep -v -E '{}'".format('|'.join(exclude_tags))

            # ips = subprocess.Popen(icommand, stdout=subprocess.PIPE)
            # lines = subprocess.check_output(ecommand, stdin=ips.stdout)
            # ips.wait()

            command = '{} | {}'.format(icommand, ecommand)
            lines = subprocess.check_output(command, shell=True)
        else:
            lines = subprocess.check_output(icommand, shell=True)

    except subprocess.CalledProcessError as e:
        print(e)
        print('Probably no match?')
        sys.exit()

    # process results
    lines = lines.split(u2b("\n"))

    if len(setting_file_list) == 1:
        lines[0] = u2b(setting_file_list[0]) + u2b(':') + lines[0]

    results = [Item(line) for line in lines if line]

    all_keys = set([])
    for item in results:
        all_keys.update(item.kwargs.keys())

    diff_dict = {key: False for key in all_keys}

    for key in diff_dict:
        for ind in range(1, len(results)):
            if results[ind].kwargs.setdefault(key, u2b('')) != \
                    results[ind - 1].kwargs.setdefault(key, u2b('')):
                diff_dict[key] = True
                break

    results = sorted(results, key=lambda x: x.ctime)

    for item in results:

        print(b2u(item.hash_str) + "\t" + time.ctime(item.ctime) + "\t" +
              ' '.join([b2u(k) + ':' + b2u(item.kwargs[k])
                        for k in sorted(item.kwargs.keys())
                        if diff_dict.setdefault(k, u2b(''))]))


if __name__ == '__main__':
    main()
