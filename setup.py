# Copyright (c) 2018-present, Royal Bank of Canada.
# All rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.#
# Author: Yanshuai Cao

from setuptools import setup

setup(name='lite_tracer',
      version='0.1',
      description='A lightweight experiment reproducibility toolset',
      url='',
      author='Yanshuai Cao',
      author_email='yanshuai.cao@borealisai.com',
      license='GNU LGPL',
      packages=['lite_tracer'],
      scripts=['lite_tracer/lite_trace.py'],
      zip_safe=False)
