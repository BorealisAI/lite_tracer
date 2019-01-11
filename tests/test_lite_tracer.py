import pytest
from lite_tracer import LTParser


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
    args, argv = tracer.parse_known_args(None)

    assert args.data_name == 'penn'
    assert args.optimizer == 'sgd'
    assert args.bsz == int(512)
    assert args.note == ''
    assert args.result_folder == './results/'

