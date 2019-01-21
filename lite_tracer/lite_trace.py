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
import pdb

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
        raise exception.NoHistory()

    include_search_params = get_param_value(args.include) if args.include else dict()
    exclude_search_params = get_param_value(args.exclude) if args.exclude else dict()

    if include_search_params is None and exclude_search_params is None:
        raise exception.NoParameterError()

    search_results = list()
    param_default_checker = FindDefault()

    # Loop through all files and find include and exclude
    for file_path in setting_file_list:
        with open(file_path, 'r') as f:
            line = f.readline()

            parsed = Parsed(file_path, line)
            parsed_params = parsed.kwargs
            param_default_checker.add(parsed_params)

            include_search_result = include_search(parsed_params, include_search_params)
            exclude_search_result = exclude_search(parsed_params, exclude_search_params)

            if include_search_result and not exclude_search_result:
                search_results.append(parsed)

    if len(search_results) == 0:
        raise exception.NoMatchError()

    search_results.sort(key=lambda x: x.ctime)
    for r in search_results:
        print(format_output(r, param_default_checker.non_defaults))

def format_output(result, non_defaults):
    output_format = "{}\t{}\t{}"
    kv_format = '{}:{}'

    result_params = result.kwargs
    ctime = time.ctime(result.ctime)
    key_values = [kv_format.format(k, ','.join(result_params[k]))
                  for k in sorted(result_params.keys())
                  if k in non_defaults]
    key_value_str = ' '.join(key_values)

    return output_format.format(result.hash_str, ctime, key_value_str)

def include_search(stored_params, search_params):
    # True if include term is found

    stored_param_keys = set(stored_params.keys())
    search_param_keys = set(search_params.keys())

    if not search_param_keys.issubset(stored_param_keys):
        return False
    else:
        return all([match(stored_params, k, v)
                    for k, v in search_params.items()])

def exclude_search(stored_params, search_params):
    stored_param_keys = set(stored_params.keys())
    search_param_keys = set(search_params.keys())

    if search_param_keys.isdisjoint(stored_param_keys):
        return False
    else:
        return any([match(stored_params, k, v, True)
                    for k, v in search_params.items()])

def get_param_value(input_param_values):
    param_value = dict()
    for pv in input_param_values:
        p_v = pv.split(':')

        if len(p_v) > 1:
            value = [':'.join(p_v[1:])]
        else:
            value = [None]

        if param_value.get(p_v[0], None):
            param_value[p_v[0]].extend(value)
        else:
            param_value[p_v[0]] = value

    return param_value

def match(stored_params, search_key, search_values, partial_search=False):
    search_values = set(search_values)
    stored_values = set(stored_params.get(search_key, [None]))

    if search_key not in stored_params.keys():
        return False

    # key exists in params and look for partial or full match
    if partial_search:
        if None in search_values:
            return True

        return bool(search_values & stored_values)
    else:
        if None in search_values:
            search_values.remove(None)

        return search_values.issubset(stored_values)


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
