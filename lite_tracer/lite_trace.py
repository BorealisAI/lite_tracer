#!/usr/bin/python
# Copyright (c) 2018-present, Royal Bank of Canada.
# All rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.#
# Author: Yanshuai Cao

from __future__ import print_function
import sys
import glob
import os
import argparse
import time
import re

from collections import defaultdict

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
        for char in bad_chars:
            params = params.replace(char, '')

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

        if changed:
            self.non_defaults |= set(changed)


def main():
    parser = argparse.ArgumentParser(
        description="explore saved experiment results by matching hyperparameter flags")

    parser.add_argument('-d', '--lt_dir', type=str,
                        default='./lt_records', help="folder containing LT records")

    parser.add_argument('-i', '--include', type=str, nargs='+')
    parser.add_argument('-e', '--exclude', type=str, nargs='+')

    args = parser.parse_args()

    setting_files_regex_path = os.path.expanduser(os.path.join(args.lt_dir, "LT*LT/settings*.txt"))
    setting_file_list = [f for f in glob.glob(setting_files_regex_path)
                         if 'searchable' not in f]

    if not setting_file_list:
        raise exception.NoHistory()

    include_params = get_param_operator_value(args.include) if args.include else defaultdict(list)
    exclude_params = get_param_operator_value(args.exclude) if args.exclude else defaultdict(list)

    if include_params is None and exclude_params is None:
        raise exception.NoParameterError()

    search_results = list()
    param_default_checker = FindDefault()

    for file_path in setting_file_list:
        with open(file_path, 'r') as setting_file:
            line = setting_file.readline()

            parsed = Parsed(file_path, line)
            parsed_params = parsed.kwargs
            param_default_checker.add(parsed_params)

            include_search_result = compare_match(parsed_params, include_params)
            include_found = all(include_search_result) and len(include_search_result) > 0

            exclude_search_result = compare_match(parsed_params, exclude_params, partial=True)
            exclude_found = any(exclude_search_result)

            # Include results when parameters are not part of the exclusion list AND
            # parameters in -i option is found OR -i option is not set
            if not exclude_found and (include_found or not include_params):
                search_results.append(parsed)

    if not search_results:
        raise exception.NoMatchError()

    search_results.sort(key=lambda x: x.ctime)
    for result in search_results:
        print(format_output(result, param_default_checker.non_defaults))


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


def get_param_operator_value(input_param_values):
    """Returns dictionary{param:[(operator, value), ...], ...}"""
    param_operator_value = defaultdict(list)
    split_regex = re.compile(r'(^[a-zA-Z]{1}[\w-]*)(<=|>=|==|<|>|:)?(.*)?')

    for p_v in input_param_values:
        p_v_matches = re.match(split_regex, p_v)
        if p_v_matches is None:
            raise exception.ArgumentNotParsable()

        par_op_val = [m for m in p_v_matches.groups() if m]

        param = par_op_val[0]
        if len(par_op_val) == 3:
            operator_value = (par_op_val[1], par_op_val[2])
        elif len(par_op_val) == 1:
            operator_value = ('', '')
        else:
            raise exception.ArgumentNotParsable()

        param_operator_value[param].append(operator_value)

    return param_operator_value


def compare_match(stored_params, search_params, partial=False):
    """Compares stored_param against search_params"""
    stored_keys = set(stored_params.keys())
    search_keys = set(search_params.keys())
    possible_search_keys = search_keys.intersection(stored_keys)
    results_list = list()

    if not partial and possible_search_keys != search_keys:
        return results_list

    for search_key in possible_search_keys:
        search_pattern = search_params[search_key]
        stored_values = stored_params[search_key]
        matches = (get_match_results(stored_values, pattern)
                   for pattern in search_pattern)
        if not partial:
            results_list.append(all(matches))
        else:
            results_list.append(any(matches))

    return results_list


def get_match_results(stored_values, pattern):
    """ Return if any of the the stored params is matching the key """
    operator = pattern[0]
    raw_value = pattern[1]
    numeric = is_numeric(raw_value)
    cast = float if numeric else str

    value = cast(raw_value)

    if raw_value and not numeric:
        if operator == ':' or operator == '==':
            return any(value == v for v in stored_values)
        else:
            return False

    casted_values = (cast(v) for v in stored_values
                     if is_numeric(v))

    if operator == ':' or operator == '==':
        return any(value == v for v in casted_values)
    elif operator == '<=':
        return any(value <= v for v in casted_values)
    elif operator == '>=':
        return any(value >= v for v in casted_values)
    elif operator == '<':
        return any(value < v for v in casted_values)
    elif operator == '>':
        return any(value > v for v in casted_values)
    else:
        return True


def is_numeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


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
