import shutil
import argparse
import random
import subprocess
import itertools
import pdb

import pytest

from lite_tracer import LTParser
import test_search
import test_flags
from test_search import cleandir

def tracer():
    tracer = test_search.get_tracer()
    test_search.add_lists_option(tracer)
    test_search.add_boolean_option(tracer)

    return tracer

def generate_different_destination():
    return ['--diff_var', '1.0',
            '-z', '1.0',
            '-r', '1.0',
            '--diff_var_long', '1.0']

def assert_different_destination(args):
    assert args.dvar == 1.0
    assert args.dvar_short == 1.0
    assert args.dvar_both == 1.0
    assert args.dvar_long == 1.0

@pytest.mark.usefixtures("cleandir")
def test_dest():
    parser = tracer()
    with pytest.raises(RuntimeError):
        test_search.add_different_destination(parser)