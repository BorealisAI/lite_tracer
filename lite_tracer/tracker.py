# Copyright (c) 2018-present, Royal Bank of Canada.
# All rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.#
# Author: Yanshuai Cao

from __future__ import print_function
import hashlib
from argparse import ArgumentParser
import six
import subprocess
import shutil
import os
import sys
import re

import lite_tracer.exceptions as exception


pjoin = os.path.join

_BASE_HASH_FIELD = 'base_hash_code'
HASH_FIELD = 'hash_code'
GIT_FIELD = 'git_label'


def args2str(args_parse_obj, filter_keys=None):
    def get_cmd_str(k, v, str_format=u'--{} {}'):
        if isinstance(v, list):
            arg_list = ' '.join([str(s) for s in v])
            return str_format.format(k, arg_list)
        else:
            return str_format.format(k, v)

    if filter_keys is None:
        filter_keys = [HASH_FIELD,
                       _BASE_HASH_FIELD,
                       'record_path']

    cmd_items = [(k, v) for k, v in vars(args_parse_obj).items()
                 if k not in filter_keys]

    cmd_items = sorted(cmd_items, key=lambda x: x[0])
    cmd_str = [get_cmd_str(k, v) for k, v in cmd_items]

    return u' '.join(cmd_str)


def hashm2str(m, short=True):
    hashcode = m.hexdigest()

    if short:
        from zlib import adler32
        hashcode = hex(adler32(m.digest()))

    return hashcode


def hash_str(args_str, short=True):
    m = hashlib.md5()
    args_str = args_str.encode('utf-8')
    m.update(args_str)

    return hashm2str(m, short)


def args2hash(args_parse_obj, short=True):
    return hash_str(args2str(args_parse_obj), short)


class LTParser(ArgumentParser):
    def __init__(self, **kwargs):
        lt_record_dir = kwargs.pop('record_dir', 'lt_records')
        self.lt_record_dir = lt_record_dir

        self.on_suspicion = kwargs.pop('on_suspicion', 'warn')
        self.short_hash = kwargs.pop('short_hash', True)

        if not os.path.exists(lt_record_dir):
            os.makedirs(lt_record_dir)

        super(LTParser, self).__init__(**kwargs)

    def parse_args(self, args=None, namespace=None):
        args = super(LTParser, self).parse_args(args, namespace)

        try:
            git_label = self._shell_output(["git", "describe", "--always"])
        except RuntimeError:
            raise exception.GitError

        hash_code = args2hash(args, short=self.short_hash)
        setattr(args, GIT_FIELD, git_label)
        setattr(args, _BASE_HASH_FIELD, hash_code)

        args = self._handle_unclean(args)

        setting_fname = pjoin(args.record_path,
                              'settings_{}'.format(args.hash_code))
        self.args_file = setting_fname + '.txt'

        with open(self.args_file, 'w') as wr:
            wr.write(args2str(args))

        return args

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

        if self.on_suspicion == 'warn':
            import warnings
            warnings.warn(msg + " Will backup the folder for now.")
        elif self.on_suspicion == 'error':
            raise ValueError(msg)
        elif self.on_suspicion == 'ignore':
            pass
        else:
            raise ValueError('on_suspicion needs to be [warn/error/ignore]')

    def _handle_unclean(self, args):
        try:
            git_diff = self._shell_output(['git', 'diff'])
            git_untracked = self._shell_output(["git", "status", "-s"])
        except RuntimeError:
            raise exception.GitError

        untracked_regex = re.compile('(?<=\?\? )(?!\.).*')
        untracked_files = re.findall(untracked_regex, git_untracked)

        m = hashlib.md5()
        m.update(git_diff.encode('utf-8'))

        files, folders = self._sort_file_n_folders(untracked_files)

        if folders:
            self._folder_error_msg(folders)

        for p in files:
            with open(p, 'rb') as fr:
                content = fr.read()
                m.update(content)

        unclean_hash = hashm2str(m, self.short_hash)
        base_hash_code = getattr(args, _BASE_HASH_FIELD)
        setattr(args, HASH_FIELD, 'LT_delta-{}_base-{}_LT'.format(
            unclean_hash, base_hash_code))
        hash_code = getattr(args, HASH_FIELD)

        # we have the unique identifier now in hash_code

        record_path = pjoin(
            self.lt_record_dir, getattr(args, HASH_FIELD))

        args.record_path = record_path

        if os.path.exists(record_path):
            msg = "Experiment {} already exists.".format(hash_code)
            if self.on_suspicion == 'warn':
                import warnings
                warnings.warn(msg + " Overwriting previous record now.")
            elif self.on_suspicion == 'error':
                raise ValueError(msg)
            elif self.on_suspicion == 'ignore':
                pass
            else:
                raise ValueError(
                    'on_suspicion needs to be [warn/error/ignore]')

        else:
            os.makedirs(record_path)

        # save unclearn data in lt folder
        with open(pjoin(record_path, 'diff.patch'), 'w') as wr:
            wr.write(git_diff)

        untracked_record_dir = pjoin(record_path, 'untracked')

        if not os.path.exists(untracked_record_dir):
            os.makedirs(untracked_record_dir)

        for uf in untracked_files:
            if os.path.isdir(uf):
                dst_path = pjoin(untracked_record_dir,
                                 os.path.basename(uf.rstrip(os.path.sep)))

                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)

                shutil.copytree(uf, dst_path)
            else:
                shutil.copy(uf, untracked_record_dir)

        return args

    @staticmethod
    def _shell_output(cmd):
        try:
            newline_regex = re.compile("[\n\r]$")
            output = subprocess.check_output(cmd).decode('utf-8')
            return re.sub(newline_regex, '', output)

        except subprocess.CalledProcessError as e:
            raise RuntimeError("Error in the process that was called")

