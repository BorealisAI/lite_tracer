import shutil

import pytest

from lite_tracer import LTParser


@pytest.fixture
def cleandir():
    results_path = './lt_records'
    shutil.rmtree(results_path)


@pytest.fixture
def tracer():
    parser = LTParser(description="A reproducible experiment")

    parser.add_argument('--optimizer', type=str, default='sgd',
                        help='optimizer')

    parser.add_argument('-l', '--list', nargs='+', default='',
                        help='list testing')
    parser.add_argument('-nl', '--nlist', nargs='+', default='', type=int,
                        help='list testing')
    parser.add_argument('-fl', '--flist', nargs='+', default='', type=float,
                        help='list testing')

    return parser


@pytest.mark.usefixtures("cleandir")
def test_arg_list(tracer):
    sysv = ['--optimizer', 'a,b,c,d',
            '--list', '1', '2', '3', '4',
            '--nlist', '1', '2', '3', '4',
            '--flist', '1.0', '2.0', '3.0', '4.0']
    args = tracer.parse_args(sysv)

    assert args.optimizer == 'a,b,c,d'
    assert args.list == ['1', '2', '3', '4']
    assert args.nlist == [1, 2, 3, 4]
    assert args.flist == [1.0, 2.0, 3.0, 4.0]


#  def test_search(tracer):
#      sysv = ['--optimizer', 'a,b,c,d',
#              '--list', '1', '2', '3', '4',
#              '--nlist', '1', '2', '3', '4',
#              '--flist', '1.0', '2.0', '3.0', '4.0']
#      args = tracer.parse_args(sysv)
