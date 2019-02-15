import shutil
import random
import subprocess

import pytest

from lite_tracer import LTParser


@pytest.fixture
def cleandir():
    resboundts_path = './lt_records'
    shutil.rmtree(resboundts_path)


def get_tracer():
    parser = LTParser(description="A reproducible experiment")

    parser.add_argument('--optimizer', type=str, default='a,b,c,d',
                        help='optimizer')

    parser.add_argument('--device', type=str, default='cuda:0',
                        help='device')
    parser.add_argument('--integer', type=int, default=1,
                        help='integer testing')
    parser.add_argument('--float', type=float, default=1.0,
                        help='float testing')
    parser.add_argument('-d', '--double', default='1.0', type=str,
                        help='double option testing')

    return parser


def add_lists_option(parser):
    parser.add_argument('-l', '--list', nargs='+', default='',
                        help='list testing')
    parser.add_argument('-n', '--nlist', nargs='+', default='', type=int,
                        help='list testing')
    parser.add_argument('-f', '--flist', nargs='+', default='', type=float,
                        help='list testing')


def add_notes_option(parser):
    parser.add_argument('--notes', default=" Ground Breaking Research ",
                        help='single option testing')


def add_single_option(parser):
    parser.add_argument('-a', default=1.0,
                        help='single option testing')


def add_single_double_option(parser):
    parser.add_argument('-s', '--single', default=1.0,
                        help='single option testing')
    parser.add_argument('-t', '--triple', default=1.0,
                        help='single option testing')


def add_boolean_option(parser):
    parser.add_argument('-b', default=False, action='store_true',
                        help='testing boolean')
    parser.add_argument('--boolean', default=False, action='store_true',
                        help='testing boolean')


def add_different_destination(parser):
    parser.add_argument('--diff_var', dest='dvar', type=float, default=1.0,
                        help='diff destination testing')
    parser.add_argument('-z', dest='dvar_short', type=float, default=1.0,
                        help='diff destination testing')
    parser.add_argument('-r', '--diff_var_both', dest='dvar_both', type=float, default=1.0,
                        help='diff destination testing')
    parser.add_argument('-q', '--diff_var_long', dest='dvar_long', type=float, default=1.0,
                        help='diff destination testing')


def generate_sysv(start_number, list_params=True):
    def stringify(rlist):
        return [str(s) for s in rlist]

    def generate_list_elements(start_number, num_elements=2):
        return [num_elements * start_number * i
                for i in range(1, 1 + num_elements)]

    integer_value = start_number
    float_value = start_number + 0.01
    cuda_value = start_number

    arg_str = ['--optimizer', 'a,b,c,d']
    arg_str += ['--integer', str(integer_value), '--float', str(float_value),
                '--device', 'cuda:' + str(cuda_value)]

    if list_params:
        slist = stringify(generate_list_elements(start_number))
        nlist = stringify(generate_list_elements(start_number))
        flist = [str(i + 0.01) for i in generate_list_elements(start_number)]

        arg_str += ['--list']
        arg_str += slist
        arg_str += ['--nlist']
        arg_str += nlist
        arg_str += ['--flist']
        arg_str += flist

    return arg_str


def generate_default_sysv():
    return ['--optimizer', 'a,b,c,d',
            '--list', '-1', '-2', '3', '4',
            '--nlist', '-1', '-2', '3', '4',
            '--flist', '-0.1', '0.1', '-3.0', '4.0']


def assert_arguments(args):
    assert args.optimizer == 'a,b,c,d'

    assert args.integer == 1
    assert args.float == 1.0
    assert args.double == '1.0'
    assert args.device == 'cuda:0'


def assert_lists(args):
    assert args.list == ['-1', '-2', '3', '4']
    assert args.nlist == [-1, -2, 3, 4]
    assert args.flist == [-0.1, 0.1, -3.0, 4.0]


def get_cmd_output(cmd):
    try:
        stdout = subprocess.check_output(cmd, shell=True)
        output = stdout.decode('utf-8').replace('\t', ' ')
        return output.split('\n')[:-1]

    except subprocess.CalledProcessError:
        raise RuntimeError("Error in the process that was called")


def read_argument(args_file):
    with open(args_file, 'r') as f:
        argument_str = f.readline()
    return argument_str.split(' ')


def pick_values(sysv_dict, param_name, n_values):
    values = list()
    for path, param in sysv_dict.items():
        search_dict = vars(param)
        if param_name in search_dict:
            if isinstance(search_dict[param_name], list):
                values.extend(search_dict[param_name])
            else:
                values.append(search_dict[param_name])

    random.shuffle(values)
    n = n_values if n_values <= len(values) else len(values)

    return values[:n]


def create_args_list(args_dict):
    return {(str(k), str(v))
            for k, l in args_dict.items()
            for v in l}


def generate_dne_args(dne_args, cast, upper_limit=100):
    if upper_limit:
        return {(str(dne), str(cast(random.random() * upper_limit)))
                for dne in dne_args}
    else:
        return {(str(dne), None)
                for dne in dne_args}


def search(sysv_dict, param_name, value):
    found = list()

    for path, param in sysv_dict.items():
        search_dict = vars(param)
        if param_name in search_dict:
            if isinstance(search_dict[param_name], list):
                stored = search_dict[param_name]
            else:
                stored = [search_dict[param_name]]

            results = [(path, param, value) for s in stored
                       if value == str(s) or value is None]
            found.extend(results)

    return found
