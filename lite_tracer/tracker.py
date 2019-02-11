# Copyright (c) 2018-present, Royal Bank of Canada.
# All rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.#
# Author: Yanshuai Cao

from __future__ import print_function
import hashlib
from argparse import ArgumentParser
import subprocess
import shutil
import os
from os.path import join as pjoin
import sys
import re
import pdb

import lite_tracer.exceptions as exception

_BASE_HASH_FIELD = 'base_hash_code'
HASH_FIELD = 'hash_code'
GIT_FIELD = 'git_label'


class LTParser(ArgumentParser):
    """Lite tracer records arguments and saves the arguments for future tracking
    """

    def __init__(self, **kwargs):
        lt_record_dir = kwargs.pop('record_dir', 'lt_records')
        self._lt_record_dir = lt_record_dir

        self._on_suspicion = kwargs.pop('on_suspicion', 'warn')
        self._short_hash = kwargs.pop('short_hash', True)

        self._flag_params = list()
        self._single_params = list()

        if not os.path.exists(lt_record_dir):
            os.makedirs(lt_record_dir)

        super(LTParser, self).__init__(**kwargs)

    def parse_args(self, args=None, namespace=None):
        args = super(LTParser, self).parse_args(args, namespace)

        try:
            git_label = self._shell_output(["git", "describe", "--always"])
        except RuntimeError:
            raise exception.GitError()

        hash_code = self.args2hash(args, short=self._short_hash)
        setattr(args, GIT_FIELD, git_label)
        setattr(args, _BASE_HASH_FIELD, hash_code)

        args = self._handle_unclean(args)

        setting_fname = pjoin(args.record_path,
                              'settings_{}'.format(args.hash_code))
        self.args_file = setting_fname + '.txt'

        with open(self.args_file, 'w') as write_file:
            write_file.write(self.args2str(args))

        return args

    def add_argument(self, *args, **kwargs):
        # TODO Use Argument add to add new arguments and filter out dest
        if len(args) == 1 and args[0].count('-') == 1:
            arguments = [s.strip('-') for s in args]
            self._single_params.extend(arguments)
        if 'dest' in kwargs:
            raise exception.DestArgumentNotSuppported()
        if 'action' in kwargs:
            action = kwargs['action']
            if action == 'store_true' or action == 'store_false':
                arguments = [s.strip('-') for s in args]
                self._flag_params.extend(arguments)

        super(LTParser, self).add_argument(*args, **kwargs)

    def args2str(self, args_parse_obj, filter_keys=None):
        if filter_keys is None:
            filter_keys = [HASH_FIELD, _BASE_HASH_FIELD, 'record_path']

        cmd_items = [(k, v) for k, v in vars(args_parse_obj).items()
                     if k not in filter_keys]

        cmd_items = sorted(cmd_items, key=lambda x: x[0])
        cmd_str = self.process_cmd_str(cmd_items)

        return ' '.join(cmd_str)

    def process_cmd_str(self, cmd_items):
        cmd_str = list()

        def get_cmd_str(key, values, str_format='--{} {}'):
            if isinstance(values, list):
                arg_list = ' '.join([str(s) for s in values])
                return str_format.format(key, arg_list)
            else:
                return str_format.format(key, values)

        for key, values in cmd_items:
            is_flag_param = key in self._flag_params
            is_single_param = key in self._single_params

            if is_flag_param:
                prefix = '-' if is_single_param else '--'
                cmd_str.append(prefix + key)
            elif is_single_param:
                cmd_str.append(get_cmd_str(key, values, str_format='-{} {}'))
            else:
                cmd_str.append(get_cmd_str(key, values))

        return cmd_str

    @staticmethod
    def _sort_file_n_folders(paths):
        folders = {p for p in paths
                   if os.path.isdir(p)}
        files = set(paths) - folders

        return files, folders

    def _folder_error_msg(self, folders):
        folder_str = ', '.join(folders)
        msg = ("{} are folders not checked in. "
               "Consider adding it to .gitignore or git add".format(folder_str))

        if self._on_suspicion == 'warn':
            import warnings
            warnings.warn(msg + " Will backup the folder for now.")
        elif self._on_suspicion == 'error':
            raise ValueError(msg)
        elif self._on_suspicion == 'ignore':
            pass
        else:
            raise ValueError('on_suspicion needs to be [warn/error/ignore]')

    def _handle_unclean(self, args):
        try:
            git_diff = self._shell_output(['git', 'diff'])
            git_untracked = self._shell_output(["git", "status", "-s"])
        except RuntimeError:
            raise exception.GitError()

        untracked_regex = re.compile(r'(?<=\?\? )(?!\.).*')
        untracked_files = re.findall(untracked_regex, git_untracked)

        md5_hash = hashlib.md5()
        md5_hash.update(git_diff.encode('utf-8'))

        files, folders = self._sort_file_n_folders(untracked_files)

        if folders:
            self._folder_error_msg(folders)

        # update hash
        for path in files:
            with open(path, 'rb') as file_handler:
                content = file_handler.read()
                md5_hash.update(content)

        unclean_hash = self.hashm2str(md5_hash, self._short_hash)
        base_hash_code = getattr(args, _BASE_HASH_FIELD)
        setattr(args, HASH_FIELD, 'LT_delta-{}_base-{}_LT'.format(
            unclean_hash, base_hash_code))
        hash_code = getattr(args, HASH_FIELD)

        record_path = pjoin(self._lt_record_dir, getattr(args, HASH_FIELD))

        args.record_path = record_path

        if os.path.exists(record_path):
            msg = "Experiment {} already exists.".format(hash_code)
            if self._on_suspicion == 'warn':
                import warnings
                warnings.warn(msg + " Overwriting previous record now.")
            elif self._on_suspicion == 'error':
                raise ValueError(msg)
            elif self._on_suspicion == 'ignore':
                pass
            else:
                raise ValueError(
                    'on_suspicion needs to be [warn/error/ignore]')
        else:
            os.makedirs(record_path)

        # save unclean data in lt folder
        with open(pjoin(record_path, 'diff.patch'), 'w') as git_diff_file:
            git_diff_file.write(git_diff)

        untracked_record_dir = pjoin(record_path, 'untracked')

        if not os.path.exists(untracked_record_dir):
            os.makedirs(untracked_record_dir)

        for u_file in untracked_files:
            if os.path.isdir(u_file):
                dst_path = pjoin(untracked_record_dir,
                                 os.path.basename(u_file.rstrip(os.path.sep)))

                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)

                shutil.copytree(u_file, dst_path)
            else:
                shutil.copy(u_file, untracked_record_dir)

        return args

    @staticmethod
    def _shell_output(cmd):
        try:
            newline_regex = re.compile("[\n\r]$")
            output = subprocess.check_output(cmd).decode('utf-8')
            return re.sub(newline_regex, '', output)

        except subprocess.CalledProcessError:
            raise RuntimeError("Error in the process that was called")

    @staticmethod
    def hashm2str(md5_hash, short=True):
        hashcode = md5_hash.hexdigest()

        if short:
            from zlib import adler32
            hashcode = hex(adler32(md5_hash.digest()))

        return hashcode

    def hash_str(self, args_str, short=True):
        md5_hash = hashlib.md5()
        args_str = args_str.encode('utf-8')
        md5_hash.update(args_str)

        return self.hashm2str(md5_hash, short)

    def args2hash(self, args_parse_obj, short=True):
        return self.hash_str(self.args2str(args_parse_obj), short)
