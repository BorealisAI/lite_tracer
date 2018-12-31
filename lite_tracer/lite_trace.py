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
import re
import pdb


def u2bs(strs):
    return [u2b(s) for s in strs]


def b2us(strs):
    return [b2u(s) for s in strs]


class Item(object):

    def __init__(self, line):
        self.line = line

        self.file_name = line.split(u2b(".txt:"))[0] + u2b(".txt")
        self.ctime = os.path.getctime(b2u(self.file_name))
        self.end_str = u2b(".txt:")
        self.start_str = u2b("settings_")

        self.hash_str = line.split(self.end_str)[0].split(self.start_str)[-1]
        self.param_str = line.split(self.end_str)[-1]

        tmp = [self._param_extraction(x) for x in
               self._param_split(self.param_str)]
        self.kwargs = dict([tuple(kv) for kv in tmp])

    def _param_extraction(self, split_param_str):
        split_param_str = self._clean_params(b2u(split_param_str))
        split = split_param_str.split(' ')
        key = split[0].replace('--', '')
        values = split[1:]

        return u2b(key), u2bs(values)

    # Needed for backward compatibility, fixed version does not need it
    # May cause problems with adding text notes
    def _clean_params(self, params):
        bad_chars = '[],\''
        for c in bad_chars:
            params = params.replace(c, '')

        return params

    def _param_split(self, raw_param_str):
        param_split = re.compile('--[a-zA-Z].*?(?= --[a-zA-Z]|$)')
        split_param_strs = re.findall(param_split, b2u(raw_param_str))
        return u2bs(split_param_strs)


def main():
    parser = argparse.ArgumentParser(
        description="explore saved experiment results by matching hyperparameter flags")

    parser.add_argument('-d', '--lt_dir', type=str,
                        default='./lt_records', help="folder containing LT records")

    parser.add_argument('-i', '--include', type=str, nargs='+')
    parser.add_argument('-e', '--exclude', type=str, nargs='+')

    args = parser.parse_args()

    # search results
    setting_file_list = [f for f in glob.glob(os.path.expanduser(
                         os.path.join(args.lt_dir, "LT*LT/settings*.txt")))
                         if 'searchable' not in f]

    if not len(setting_file_list):
        print('No match found')
        sys.exit()

    def get_param_name(tags):
        return [t.split(':')[0] for t in tags]

    def get_param_values(tags):
        return [t.split(':')[1] for t in tags
                if ':' in t]

    setting_files = ' '.join(setting_file_list)
    include_tags = get_param_name(args.include) if args.include else []
    exclude_tags = get_param_name(args.exclude) if args.exclude else []

    include_values = get_param_values(args.include) if args.include else []
    exclude_values = get_param_values(args.exclude) if args.exclude else []

    icommand = "grep -E '{}' {}".format('|'.join(include_tags), setting_files)

    # TODO: figure out why the non shell version fails so can avoid shell=True
    try:
        if exclude_tags and len(exclude_values) == 0:
            ecommand = "grep -v -E '{}'".format('|'.join(exclude_tags))

            # ips = subprocess.Popen(icommand, stdout=subprocess.PIPE)
            # lines = subprocess.check_output(ecommand, stdin=ips.stdout)
            # ips.wait()

            command = '{} | {}'.format(icommand, ecommand)
            lines = subprocess.check_output(command, shell=True)
        else:
            lines = subprocess.check_output(icommand, shell=True)

    except subprocess.CalledProcessError as e:
        print('No match, Check the parameter name')
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

    # Find out if the parameter value has changed,
    # if it hasn't it's a constant and we don't care
    # TODO: Make this information more transparent on the docs
    #       possibley add a --full option
    for key in diff_dict:
        for ind in range(1, len(results)):
            if results[ind].kwargs.setdefault(key, u2b('')) != \
                    results[ind - 1].kwargs.setdefault(key, u2b('')):
                diff_dict[key] = True
                break

    if len(exclude_values):
        excluded_results = set()
        for key, value in zip(u2bs(exclude_tags), u2bs(exclude_values)):
            r = [r for r in results if value in r.kwargs.get(key, [])]
            excluded_results.update(r)
        results = list(set(results) - set(excluded_results))

    if len(include_values):
        included_results = set()
        for key, value in zip(u2bs(include_tags), u2bs(include_values)):
            r = [r for r in results if value in r.kwargs.get(key, [])]
            included_results.update(r)
        results = list(included_results)

    results = sorted(results, key=lambda x: x.ctime)

    for item in results:
        print(b2u(item.hash_str) + "\t" + time.ctime(item.ctime) + "\t" +
              ' '.join([b2u(k) + ':' + b2u(b','.join(item.kwargs[k]))
                        for k in sorted(item.kwargs.keys())
                        if diff_dict.setdefault(k, u2b(''))]))


if __name__ == '__main__':
    main()
