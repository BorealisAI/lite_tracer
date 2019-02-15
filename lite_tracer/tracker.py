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
import re

import lite_tracer.exceptions as exception


class LTParser(ArgumentParser):
    """Lite tracer parses arugments and saves them for future tracking

    Attributes:
    record_path(str): Directory in which the record will be saved
    args_file (str): File path for the record text path
    """
    _BASE_HASH_FIELD = 'base_hash_code'
    _HASH_FIELD = 'hash_code'
    _GIT_FIELD = 'git_label'
    _HASH_FORMAT = 'LT_delta-{}_base-{}_LT'

    def __init__(self, **kwargs):
        self._lt_record_dir = kwargs.pop('record_dir', 'lt_records')
        self._on_suspicion = kwargs.pop('on_suspicion', 'warn')
        self._short_hash = kwargs.pop('short_hash', True)

        self.record_path = ''
        self.args_file = ''

        self._flag_params = list()
        self._single_params = list()

        if not os.path.exists(self._lt_record_dir):
            os.makedirs(self._lt_record_dir)

        super(LTParser, self).__init__(**kwargs)

    def parse_args(self, args=None, namespace=None):
        args = super(LTParser, self).parse_args(args, namespace)

        try:
            git_label = self._shell_output(["git", "describe", "--always"])
        except RuntimeError:
            raise exception.GitError()

        hash_code = self._args_to_hash(args, short=self._short_hash)
        setattr(args, self._GIT_FIELD, git_label)
        setattr(args, self._BASE_HASH_FIELD, hash_code)

        args = self._handle_unclean(args)

        setting_fname = pjoin(self.record_path,
                              'settings_{}'.format(args.hash_code))
        self.args_file = setting_fname + '.txt'

        with open(self.args_file, 'w') as write_file:
            write_file.write(self._args_to_str(args))

        return args

    def add_argument(self, *args, **kwargs):
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

    def _handle_unclean(self, args):
        unclean_hash = hashlib.md5()
        base_hash = getattr(args, self._BASE_HASH_FIELD)

        # Update the hash
        git_diff = self._update_diff_hash(unclean_hash)
        untracked_files = self._update_untracked_hash(unclean_hash)

        unclean_hash_str = self._hash_to_str(unclean_hash)
        hash_text = self._HASH_FORMAT.format(unclean_hash_str, base_hash)
        setattr(args, self._HASH_FIELD, hash_text)

        # Check if Directories exist and error according to preference
        self.record_path = pjoin(self._lt_record_dir, hash_text)

        # TODO: Default is to create another directory with timestamp
        if os.path.exists(self.record_path):
            msg = "Experiment {} already exists.".format(hash_text)
            if self._on_suspicion == 'warn':
                import warnings
                warnings.warn(msg + " Overwriting previous record now.")
            elif self._on_suspicion == 'error':
                raise ValueError(msg)
            elif self._on_suspicion == 'ignore':
                pass
            else:
                raise ValueError('on_suspicion needs to be [warn/error/ignore]')
        else:
            os.makedirs(self.record_path)

        # Save the diff and the untracked_files in to a directory
        with open(pjoin(self.record_path, 'diff.patch'), 'w') as git_diff_file:
            git_diff_file.write(git_diff)

        self._save_untracked(untracked_files)

        return args

    def _args_to_str(self, args_parse_obj, filter_keys=None):
        if filter_keys is None:
            filter_keys = [self._HASH_FIELD, self._BASE_HASH_FIELD, 'record_path']

        cmd_items = [(k, v) for k, v in vars(args_parse_obj).items()
                     if k not in filter_keys]

        sorted_cmd_items = sorted(cmd_items, key=lambda x: x[0])

        return ' '.join(self._cmd_to_str(sorted_cmd_items))

    def _cmd_to_str(self, cmd_items):
        cmd_str = list()

        def format_cmd_str(key, values, str_format='--{} {}'):
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
                cmd_str.append(format_cmd_str(key, values, str_format='-{} {}'))
            else:
                cmd_str.append(format_cmd_str(key, values))

        return cmd_str

    def _update_diff_hash(self, md5_hash):
        try:
            git_diff = self._shell_output(['git', 'diff'])
        except RuntimeError:
            raise exception.GitError()

        md5_hash.update(git_diff.encode('utf-8'))

        return git_diff

    def _update_untracked_hash(self, md5_hash):
        untracked_files = self._find_untracked()
        files, folders = self._sort_files_folders(untracked_files)

        if folders:
            self._folder_error_msg(folders)

        untracked_content = self._read_untracked_files(files)
        md5_hash.update(''.join(untracked_content))

        return untracked_files

    def _find_untracked(self):
        try:
            git_untracked = self._shell_output(["git", "status", "-s"])
        except RuntimeError:
            raise exception.GitError()

        untracked_regex = re.compile(r'(?<=\?\? )(?!\.).*')
        untracked_files = re.findall(untracked_regex, git_untracked)

        return untracked_files

    @staticmethod
    def _sort_files_folders(paths):
        folders = {p for p in paths
                   if os.path.isdir(p)}
        files = set(paths) - folders

        return files, folders

    @staticmethod
    def _read_untracked_files(files):
        content = list()
        for path in files:
            with open(path, 'rb') as file_handler:
                content.append(file_handler.read().encode('utf-8'))

        return content

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

    def _save_untracked(self, untracked_files, save_folder='untracked'):
        untracked_save_path = pjoin(self.record_path, save_folder)

        if not os.path.exists(untracked_save_path):
            os.makedirs(untracked_save_path)

        for u_file in untracked_files:
            print(untracked_save_path, os.path.sep)
            if os.path.isdir(u_file):
                dst_path = pjoin(untracked_save_path,
                                 os.path.basename(u_file.rstrip(os.path.sep)))
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)

                shutil.copytree(u_file, dst_path)
            else:
                shutil.copy(u_file, untracked_save_path)

    def _args_to_hash(self, args_parse_obj, short=True):
        md5_hash = hashlib.md5()
        args_str = self._args_to_str(args_parse_obj)
        md5_hash.update(args_str.encode('utf-8'))

        return self._hash_to_str(md5_hash, short)

    @staticmethod
    def _hash_to_str(md5_hash, short=True):
        if not short:
            hash_code = md5_hash.hexdigest()
        else:
            from zlib import adler32
            hash_code = hex(adler32(md5_hash.digest()))

        return hash_code

    @staticmethod
    def _shell_output(cmd):
        try:
            newline_regex = re.compile("[\n\r]$")
            output = subprocess.check_output(cmd).decode('utf-8')
            return re.sub(newline_regex, '', output)

        except subprocess.CalledProcessError:
            raise RuntimeError("Error in the process that was called")
