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


pjoin = os.path.join

_BASE_HASH_FIELD = 'base_hash_code'
HASH_FIELD = 'hash_code'
GIT_FIELD = 'git_label'

if six.PY3:
    def u2b(u):
        return u.encode('utf-8')

    def b2u(b):
        return b.decode('utf-8')

else:
    def u2b(x): return x

    def b2u(x): return x


def args2str(args_parse_obj, filter_keys=None, searchable=True):

    if filter_keys is None:
        filter_keys = [HASH_FIELD,
                       _BASE_HASH_FIELD,
                       'record_path']

    cmd_items = [(k, v) for k, v in vars(args_parse_obj).items()
                 if k not in filter_keys]

    cmd_items = sorted(cmd_items,  key=lambda x: x[0])

    if searchable:
        cmd_items = [u'{}:{}'.format(k, v) for k, v in cmd_items]
    else:
        cmd_items = [u'--{} {}'.format(k, v) for k, v in cmd_items]

    return u' '.join(cmd_items)


def hashm2str(m, short=True):
    hashcode = m.hexdigest()

    if short:
        from zlib import adler32
        hashcode = hex(adler32(m.digest()))

    return hashcode


def hash_str(args_str, short=True):
    m = hashlib.md5()
    m.update(u2b(args_str))
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
        git_label = subprocess.check_output(
            ["git", "describe", "--always"]).strip()

        git_label = b2u(git_label)

        hash_code = args2hash(args, short=self.short_hash)
        setattr(args, GIT_FIELD, git_label)
        setattr(args, _BASE_HASH_FIELD, hash_code)

        args = self._handle_unclean(args)

        setting_fname = pjoin(args.record_path,
                              'settings_{}'.format(args.hash_code))

        with open(setting_fname+'.txt', 'w') as wr:
            wr.write(args2str(args, searchable=False))

        with open(setting_fname+'_searchable.txt', 'w') as wr:
            wr.write(args2str(args, searchable=True))

        return args

    def _handle_unclean(self, args):
        git_diff = subprocess.check_output(["git", "diff"])
        git_untracked = subprocess.check_output(["git", "status", "-s"])

        mark = u2b("??")
        linesep = u2b(os.linesep)

        git_untracked = [uf for uf in git_untracked.strip().split(linesep)
                         if (mark in uf and u2b(self.lt_record_dir) not in uf)]

        untracked_files = [x.split(mark)[1].strip() for x in git_untracked]
        untracked_files = [
            x for x in untracked_files if not x.startswith(u2b('.'))]

        m = hashlib.md5()
        m.update(git_diff)

        for uf in untracked_files:
            if os.path.isdir(uf):
                msg = ("untracked {} is a folder. "
                       "Consider .gitignore it or commit".format(
                           b2u(uf)))
                if self.on_suspicion == 'warn':
                    import warnings
                    warnings.warn(msg + " Will backup the folder for now.")
                elif self.on_suspicion == 'error':
                    raise ValueError(msg)
                elif self.on_suspicion == 'ignore':
                    pass
                else:
                    raise ValueError(
                        'on_suspicion needs to be [warn/error/ignore]')
            else:
                with open(uf, 'rb') as fr:
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
            wr.write(b2u(git_diff))

        untracked_record_dir = pjoin(record_path, 'untracked')

        if not os.path.exists(untracked_record_dir):
            os.makedirs(untracked_record_dir)

        for uf in untracked_files:
            uf = b2u(uf)

            if os.path.isdir(uf):

                dst_path = pjoin(untracked_record_dir,
                                 os.path.basename(uf.rstrip(os.path.sep)))

                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)

                shutil.copytree(uf,  dst_path)
            else:
                shutil.copy(uf, untracked_record_dir)

        return args
