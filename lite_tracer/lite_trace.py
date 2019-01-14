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
import time
import re

import lite_tracer.exceptions as exception

class Parsed(object):
    def __init__(self, file_path, line):
        self.line = line

        self.file_name = file_path
        self.ctime = os.path.getctime(self.file_name)
        self.end_str = ".txt"
        self.start_str = "settings_"

        hash_str_regex = re.compile('(?<=settings_)LT.*LT(?=.txt)')
        self.hash_str = re.search(hash_str_regex, file_path).group(0)
        self.line = line

        tmp = [self._param_extraction(x)
               for x in self._param_split(self.line)]
        self.kwargs = dict([tuple(kv) for kv in tmp])

    def _param_extraction(self, split_param_str):
        split_param_str = self._clean_params(split_param_str)
        split = split_param_str.split(' ')
        key = split[0].replace('--', '')
        values = split[1:]

        return key, values

    # Needed for backward compatibility, fixed version does not need it
    # May cause problems with adding text notes
    def _clean_params(self, params):
        bad_chars = '[],\''
        for c in bad_chars:
            params = params.replace(c, '')

        return params

    def _param_split(self, raw_param_str):
        param_split = re.compile('[-]{1,2}[a-zA-Z].*?(?= [-]{1,2}[a-zA-Z]|$)')
        split_param_strs = re.findall(param_split, raw_param_str)
        return split_param_strs


class FindDefault(object):
    def __init__(self):
        self.non_defaults = set()
        self.values = dict()

    def add(self, params):
        changed = [k for k, v in params.items()
                   if self.values.setdefault(k, v) != v]

        if len(changed):
            self.non_defaults |= set(changed)


def main():
    parser = argparse.ArgumentParser(
        description="explore saved experiment results by matching hyperparameter flags")

    parser.add_argument('-d', '--lt_dir', type=str,
                        default='./lt_records', help="folder containing LT records")

    parser.add_argument('-i', '--include', type=str, nargs='+')
    parser.add_argument('-e', '--exclude', type=str, nargs='+')

    args = parser.parse_args()

    setting_file_list = [f for f in glob.glob(os.path.expanduser(
                         os.path.join(args.lt_dir, "LT*LT/settings*.txt")))
                         if 'searchable' not in f]

    if not setting_file_list:
        raise exception.NoHistory

    include_params = get_param_value(args.include) if args.include else dict()
    exclude_params = get_param_value(args.exclude) if args.exclude else dict()

    if include_params is None and exclude_params is None:
        raise exception.NoParameterError

    results = list()
    defaults = FindDefault()

    # Loop through all files and find include and exclude
    for file_path in setting_file_list:
        with open(file_path, 'r') as f:
            line = f.readline()

            parsed = Parsed(file_path, line)
            params = parsed.kwargs
            defaults.add(params)

            i_search_result = include_search(params, include_params)
            e_search_result = exclude_search(params, exclude_params)

            if i_search_result and not e_search_result:
                results.append(parsed)

    if len(results) == 0:
        raise exception.NoMatchError

    results = sorted(results, key=lambda x: x.ctime)

    for item in results:
        print(item.hash_str + "\t" + time.ctime(item.ctime) + "\t" +
              ' '.join([k + ':' + ','.join(item.kwargs[k])
                        for k in sorted(item.kwargs.keys())
                        if k in defaults.non_defaults]))


def include_search(params, include_params):
    # True if include term is found
    if include_params is None:
        return True

    params_keys = set(list(params.keys()))
    include_keys = set(include_params.keys())

    if not include_keys.issubset(params_keys):
        return False
    else:
        return all([match(params, k, v) for k, v in include_params.items()])

def exclude_search(params, exclude_params):
    # True if exclude term is found
    if exclude_params is None:
        return False

    params_keys = set(list(params.keys()))
    exclude_keys = set(exclude_params.keys())

    if exclude_keys.isdisjoint(params_keys):
        return False
    else:
        return any([match(params, k, v, True) for k, v in exclude_params.items()])


def get_param_value(tags):
    param_value = dict()
    for t in tags:
        t_v = t.split(':')
        if len(t_v) > 1:
            value = [':'.join(t_v[1:])]
            if param_value.get(t_v[0], None):
                param_value[t_v[0]].extend(value)
            else:
                param_value[t_v[0]] = value
        else:
            if param_value.setdefault(t_v[0], [None]):
                param_value[t_v[0]].append(None)

    return param_value


def match(params, key, values, partial=False):
    values_set = set(values)
    params_set = set(params.get(key, [None]))

    if key not in params.keys():
        return False

    if partial:
        if None in values_set:
            return True

        joint_set = values_set & params_set
        return not joint_set.isdisjoint(values_set)

    if None in values_set:
        values_set.remove(None)

    joint_set = values_set & params_set
    return joint_set == values_set


if __name__ == '__main__':
    try:
        main()
    except (exception.NoHistory, exception.NoMatchError, exception.NoParameterError) as e:
        if isinstance(e, exception.NoHistory):
            print("Error: There are no previous runs of this experiment")
        elif isinstance(e, exception.NoParameterError):
            print("Error: Parameters were not provided properly")
        elif isinstance(e, exception.NoMatchError):
            print("There were no match for the given Parameters")

        sys.exit(1)
