import shutil
import argparse
import random

import pytest

from lite_tracer import LTParser


@pytest.fixture
def cleandir():
    results_path = './lt_records'
    shutil.rmtree(results_path)


def get_tracer():
    parser = LTParser(description="A reproducible experiment")

    parser.add_argument('--optimizer', type=str, default='sgd',
                        help='optimizer')

    parser.add_argument('--device', type=str, default='cuda:0',
                        help='device')
    parser.add_argument('--integer', type=int, default=1,
                        help='integer testing')
    parser.add_argument('--float', type=float, default=1.0,
                        help='float testing')
    parser.add_argument('-d', '--double', default='1.0', type=str,
                        help='double option testing')

    parser.add_argument('-l', '--list', nargs='+', default='',
                        help='list testing')
    parser.add_argument('-n', '--nlist', nargs='+', default='', type=int,
                        help='list testing')
    parser.add_argument('-f', '--flist', nargs='+', default='', type=float,
                        help='list testing')

    return parser


def add_single_option(parser):
    parser.add_argument('-a', default=1.0,
                        help='single option testing')


def add_boolean_arguments(parser):
    parser.add_argument('-b', default=False, action='store_true',
                        help='testing boolean')
    parser.add_argument('--boolean', default=False, action='store_true',
                        help='testing boolean')


def add_different_destination(parser):
    parser.add_argument('--diff_var', dest='dvar', type=float, default=1.0,
                        help='diff destination testing')


def random_generate_sysv():
    ul = 200
    n_picks = 4

    def stringify(rlist):
        return [str(s) for s in rlist]

    integer_value = random.randint(-ul, ul)
    float_value = random.uniform(-ul, ul)
    slist = stringify(random.sample(range(-ul, ul), n_picks))
    nlist = stringify(random.sample(range(-ul, ul), n_picks))
    flist = stringify([random.uniform(-ul, ul) for i in range(n_picks)])

    arg_str = ['--optimizer', 'a,b,c,d']
    arg_str += ['--list']
    arg_str += slist
    arg_str += ['--nlist']
    arg_str += nlist
    arg_str += ['--flist']
    arg_str += flist
    arg_str += ['--integer', str(integer_value), '--float', str(float_value)]

    return arg_str


def generate_sysv():
    return ['--optimizer', 'a,b,c,d',
            '--list', '-1', '-2', '3', '4',
            '--nlist', '-1', '-2', '3', '4',
            '--flist', '-0.1', '0.1', '-3.0', '4.0']


def assert_arguments(args):
    assert args.optimizer == 'a,b,c,d'
    assert args.list == ['-1', '-2', '3', '4']
    assert args.nlist == [-1, -2, 3, 4]
    assert args.flist == [-0.1, 0.1, -3.0, 4.0]
    assert args.integer == 1
    assert args.float == 1.0
    assert args.double == '1.0'
    assert args.device == 'cuda:0'


@pytest.mark.usefixtures("cleandir")
def test_arg_list():
    tracer = get_tracer()
    sysv = generate_sysv()
    args = tracer.parse_args(sysv)

    assert_arguments(args)


@pytest.mark.usefixtures("cleandir")
# Save the arguments to the tracer_file
# Import the saved tracer_file and parse it again
def test_arguments_file():
    tracer = get_tracer()
    sysv = generate_sysv()
    tracer.parse_args(sysv)
    args_file = tracer.args_file

    with open(args_file, 'r') as f:
        argument_str = f.readline()
    read_argument = argument_str.split(' ')

    new_tracer = get_tracer()
    args, unknown = new_tracer.parse_known_args(read_argument)

    assert_arguments(args)
    assert len(unknown) == 2 and unknown[0] == '--git_label'


#  @pytest.mark.usefixtures("cleandir")
#  # Save the arguments to the tracer settings file
#  # Search the files
#  def test_search():
#      n_history = 20

#      sysv_dict = dict()
#      for i in range(n_history):
#          tracer = get_tracer()
#          sysv = random_generate_sysv()
#          tracer.parse_args(sysv)
#          args_file = tracer.args_file
#          sysv_dict[args_file] = sysv

#      print(sysv_dict)
