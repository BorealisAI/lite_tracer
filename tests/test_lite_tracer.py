import pytest

from lite_tracer import LTParser

import pdb
import helper
from helper import cleandir


@pytest.fixture
def tracer():
    parser = LTParser(description="A reproducible experiment")

    parser.add_argument('--data_name', type=str, default='penn',
                        help='data name')

    parser.add_argument('--optimizer', type=str, default='sgd',
                        help='optimizer')

    parser.add_argument('--bsz', type=int, default=512,
                        help='batch size')

    parser.add_argument('--note', type=str, default='',
                        help='additional_note_str')

    parser.add_argument('--result_folder', type=str, default='./results/',
                        help='additional_note_str')

    return parser


def test_simple_test(tracer):
    args, _ = tracer.parse_known_args(None)

    assert args.data_name == 'penn'
    assert args.optimizer == 'sgd'
    assert args.bsz == int(512)
    assert args.note == ''
    assert args.result_folder == './results/'


@pytest.mark.usefixtures("cleandir")
def test_arg_list():
    tracer = helper.get_tracer()
    args, left_over = tracer.parse_known_args()
    assert left_over

    helper.assert_arguments(args)


@pytest.mark.usefixtures("cleandir")
def test_arguments_file():
    # construct tracer and save results
    tracer = helper.get_tracer()
    helper.add_lists_option(tracer)

    sysv = helper.generate_default_sysv()
    tracer.parse_args(sysv)
    arguments = helper.read_argument(tracer.args_file)

    # Start a new tracer and read the arguments from file
    new_tracer = helper.get_tracer()
    helper.add_lists_option(new_tracer)
    args, unknown = new_tracer.parse_known_args(arguments)

    helper.assert_arguments(args)
    helper.assert_lists(args)
    assert len(unknown) == 2 and unknown[0] == '--git_label'
