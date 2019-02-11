import pytest
import stat
import shutil
import subprocess
import random
import pdb

from lite_tracer import LTParser
import helper
from helper import cleandir


@pytest.fixture
def script_setup(tmpdir):
    script = tmpdir.join('script.py')
    script.open('w').write(
        """#!/usr/bin/env python

from lite_tracer import LTParser

parser = LTParser(description="A reproducible experiment")

parser.add_argument('--device', type=str, default='cuda:0',
                    help='device')
parser.add_argument('--integer', type=int, default=1,
                    help='integer testing')
parser.add_argument('--float', type=float, default=1.0,
                    help='float testing')
parser.add_argument('-d', '--double', default='1.0', type=str,
                    help='double option testing')

parser.add_argument('-b', default=False, action='store_true',
                    help='testing boolean')
parser.add_argument('--boolean', default=False, action='store_true',
                    help='testing boolean')

parser.add_argument('-a', default=1.0,
                    help='single option testing')

args = parser.parse_args()
print(args)
""")
    script.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    return script


def generate_boolean():
    return ['-b', '--boolean']


def generate_single():
    return ['-a', '1.0']


def generate_single_double():
    return ['-s', '1.0', '-t', '1000']


def assert_boolean(args):
    assert args.b
    assert args.boolean


def tracer():
    tracer = helper.get_tracer()
    helper.add_lists_option(tracer)
    helper.add_boolean_option(tracer)

    return tracer


def generate_base_args():
    sysv = helper.generate_default_sysv()
    sysv += generate_boolean()

    return sysv


@pytest.mark.usefixtures("cleandir")
# Save the arguments to the tracer_file
# Import the saved tracer_file and parse it again
def test_boolean():
    parser = tracer()
    sysv = generate_base_args()
    parser.parse_args(sysv)
    read_args = helper.read_argument(parser.args_file)

    # create new tracer for read
    new_tracer = tracer()
    args, unknown = new_tracer.parse_known_args(read_args)

    assert len(unknown) == 2 and unknown[0] == '--git_label'

    helper.assert_arguments(args)
    helper.assert_lists(args)
    assert_boolean(args)


@pytest.mark.usefixtures("cleandir")
# Save the arguments to the tracer_file
# Import the saved tracer_file and parse it again
def test_single_argument():
    parser = tracer()
    helper.add_single_option(parser)
    sysv = generate_base_args()
    sysv += generate_single()
    parser.parse_args(sysv)
    read_args = helper.read_argument(parser.args_file)

    # create new tracer for read
    new_tracer = tracer()
    helper.add_single_option(new_tracer)

    args, unknown = new_tracer.parse_known_args(read_args)

    assert len(unknown) == 2 and unknown[0] == '--git_label'

    helper.assert_arguments(args)
    helper.assert_lists(args)
    assert_boolean(args)


@pytest.mark.usefixtures("cleandir")
def test_single_double_argument():
    parser = tracer()
    helper.add_single_double_option(parser)
    sysv = generate_base_args()
    sysv += generate_single_double()
    parser.parse_args(sysv)
    read_args = helper.read_argument(parser.args_file)

    # create new tracer for read
    new_tracer = tracer()
    helper.add_single_double_option(new_tracer)

    args, unknown = new_tracer.parse_known_args(read_args)

    assert len(unknown) == 2 and unknown[0] == '--git_label'

    helper.assert_arguments(args)
    helper.assert_lists(args)
    assert_boolean(args)
