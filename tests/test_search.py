import shutil
import argparse

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

    parser.add_argument('--integer', type=int, default=1,
                        help='integer testing')
    parser.add_argument('--float', type=float, default=1.0,
                        help='float testing')


    parser.add_argument('-l', '--list', nargs='+', default='',
                        help='list testing')
    parser.add_argument('-nl', '--nlist', nargs='+', default='', type=int,
                        help='list testing')
    parser.add_argument('-fl', '--flist', nargs='+', default='', type=float,
                        help='list testing')

    return parser


def generate_sysv():
    return ['--optimizer', 'a,b,c,d',
            '--list', '1', '2', '3', '4',
            '--nlist', '1', '2', '3', '4',
            '--flist', '1.0', '2.0', '3.0', '4.0']


@pytest.mark.usefixtures("cleandir")
def test_arg_list():
    tracer = get_tracer()
    sysv = generate_sysv()
    args = tracer.parse_args(sysv)

    assert args.optimizer == 'a,b,c,d'
    assert args.list == ['1', '2', '3', '4']
    assert args.nlist == [1, 2, 3, 4]
    assert args.flist == [1.0, 2.0, 3.0, 4.0]
    assert args.integer == 1
    assert args.float == 1.0


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

    assert args.optimizer == 'a,b,c,d'
    assert args.list == ['1', '2', '3', '4']
    assert args.nlist == [1, 2, 3, 4]
    assert args.flist == [1.0, 2.0, 3.0, 4.0]
    assert args.integer == 1
    assert args.float == 1.0

    assert len(unknown) == 2 and unknown[0] == '--git_label'

