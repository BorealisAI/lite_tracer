import shutil
import argparse
import random
import subprocess
import itertools

import pytest

from lite_tracer import LTParser


@pytest.fixture
def cleandir():
    results_path = './lt_records'
    shutil.rmtree(results_path)


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
    parser.add_argument('-s', '--single',default=1.0,
                        help='single option testing')
    parser.add_argument('-t', '--triple',default=1.0,
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

def random_generate_sysv(list_params=True):
    ul = 200
    n_picks = 4

    def stringify(rlist):
        return [str(s) for s in rlist]

    integer_value = random.randint(-ul, ul)
    float_value = random.uniform(-ul, ul)
    cuda_value = random.randint(0, ul)
    slist = stringify(random.sample(range(-ul, ul), n_picks))
    nlist = stringify(random.sample(range(-ul, ul), n_picks))
    flist = stringify([random.uniform(-ul, ul) for i in range(n_picks)])

    arg_str = ['--optimizer', 'a,b,c,d']
    arg_str += ['--integer', str(integer_value), '--float', str(float_value),
                '--device', 'cuda:' + str(cuda_value)]

    if list_params:
        arg_str += ['--list']
        arg_str += slist
        arg_str += ['--nlist']
        arg_str += nlist
        arg_str += ['--flist']
        arg_str += flist

    return arg_str


def generate_sysv():
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


@pytest.mark.usefixtures("cleandir")
def test_arg_list():
    tracer = get_tracer()
    args, left_over = tracer.parse_known_args()

    assert_arguments(args)


@pytest.mark.usefixtures("cleandir")
# Save the arguments to the tracer_file
# Import the saved tracer_file and parse it again
def test_arguments_file():
    tracer = get_tracer()
    add_lists_option(tracer)

    sysv = generate_sysv()
    tracer.parse_args(sysv)
    args_file = tracer.args_file

    with open(args_file, 'r') as f:
        argument_str = f.readline()
    read_argument = argument_str.split(' ')

    new_tracer = get_tracer()
    add_lists_option(new_tracer)
    args, unknown = new_tracer.parse_known_args(read_argument)

    assert_arguments(args)
    assert_lists(args)
    assert len(unknown) == 2 and unknown[0] == '--git_label'

def get_cmd_output(cmd):
    try:
        stdout = subprocess.check_output(cmd, shell=True)
        output = stdout.decode('utf-8').replace('\t', ' ')
        return output.split('\n')[:-1]

    except subprocess.CalledProcessError as e:
        raise RuntimeError("Error in the process that was called")


@pytest.mark.usefixtures("cleandir")
# Save the arguments to the tracer settings file
# Search the files
def test_search_parameter():
    n_history = 20

    for i in range(n_history):
        tracer = get_tracer()

        # half the experiments have list options
        if i % 2 == 0:
            add_lists_option(tracer)
            sysv = random_generate_sysv()
        else:
            sysv = random_generate_sysv(False)
        tracer.parse_args(sysv)

    list_args = ['list', 'nlist', 'flist']
    single_args = ['integer', 'float', 'double', 'device']
    dne_args = ['lists', 'nlists', 'flists']

    all_args = list_args + single_args + dne_args
    include_cmd = "lite_trace.py -i {}"
    exclude_cmd = "lite_trace.py -e {}"
    in_ex_cmd = "lite_trace.py -i {} -e {}"

    # Include single arguments
    for arg in all_args:
        cmd = include_cmd.format(arg)
        if arg in list_args:
            output = get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        elif arg in single_args:
            output = get_cmd_output(cmd)
            assert len(output) == n_history
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)

    # Exclude single arguments
    for arg in all_args:
        cmd = exclude_cmd.format(arg)
        if arg in list_args:
            output = get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        elif arg in single_args:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        else:
            output = get_cmd_output(cmd)
            assert len(output) == n_history

    # Include multiple arguments
    for arg1, arg2 in itertools.product(all_args, repeat=2):
        arg_str = '{} {}'.format(arg1, arg2)
        cmd = include_cmd.format(arg_str)

        if arg1 in dne_args or arg2 in dne_args:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif arg1 in list_args or arg2 in list_args:
            output = get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        else:
            output = get_cmd_output(cmd)
            assert len(output) == n_history

    # Exclude multiple arguments
    for arg1, arg2 in itertools.product(all_args, repeat=2):
        arg_str = '{} {}'.format(arg1, arg2)
        cmd = exclude_cmd.format(arg_str)

        if arg1 in single_args or arg2 in single_args:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif arg1 in list_args or arg2 in list_args:
            output = get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        else:
            output = get_cmd_output(cmd)
            assert len(output) == n_history

    # Include and Exclude tests
    for arg1, arg2 in itertools.product(all_args, repeat=2):
        cmd = in_ex_cmd.format(arg1, arg2)

        if arg1 in dne_args:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif arg2 in single_args:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif arg1 in single_args and arg2 in list_args:
            output = get_cmd_output(cmd)
            assert len(output) == (n_history / 2)
        elif arg1 in single_args:
            output = get_cmd_output(cmd)
            assert len(output) == n_history
        elif arg1 in list_args and arg2 in dne_args:
            output = get_cmd_output(cmd)
            assert len(output) == (n_history / 2)
        elif arg1 in list_args and arg2 in dne_args:
            output = get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)


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


@pytest.mark.usefixtures("cleandir")
def test_search_parameter_value():
    n_history = 20

    sysv_dict = dict()
    for i in range(n_history):
        tracer = get_tracer()

        # half the experiments have list options
        if i % 2 == 0:
            add_lists_option(tracer)
            sysv = random_generate_sysv()
        else:
            sysv = random_generate_sysv(False)

        args = tracer.parse_args(sysv)
        args_file = tracer.args_file
        sysv_dict[args_file] = args

    list_args = ['list', 'flist']
    single_args = ['integer', 'float', 'double', 'device']
    dne_list_args = ['lists']

    include_cmd = "lite_trace.py -i {}"
    exclude_cmd = "lite_trace.py -e {}"
    in_ex_cmd = "lite_trace.py -i {} -e {}"

    num_test = 2
    args_dict = {arg: pick_values(sysv_dict, arg, num_test)
                    for arg in list_args + single_args}
    exist_search = create_args_list(args_dict)

    dne_search = generate_dne_args(dne_list_args, cast=float)
    dne_search |= generate_dne_args(list_args, cast=float)

    all_search  = exist_search | dne_search

    # Include single arguments
    for param, value in all_search:
        cmd = include_cmd.format(param + ':' + value)
        n_results = len(search(sysv_dict, param, value))

        if n_results > 0:
            output = get_cmd_output(cmd)
            assert len(output) == n_results
        else:
            if (param, value) in exist_search:
                raise RuntimeError
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)

    # Exclude single arguments
    for param, value in all_search:
        cmd = exclude_cmd.format(param + ':' + value)
        n_results = len(search(sysv_dict, param, value))

        if n_results < n_history:
            output = get_cmd_output(cmd)
            assert n_history - len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)

    # Include multiple arguments

    dual_search = list(itertools.product(all_search, repeat=2))

    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(':'.join(arg1), ':'.join(arg2))
        cmd = include_cmd.format(arg_str)

        results_1 = {s[0] for s in search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 & results_2)

        if arg1 in dne_search or arg2 in dne_search:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif n_results > 0:
            output = get_cmd_output(cmd)
            assert len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)

    # Exclude multiple arguments
    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(':'.join(arg1), ':'.join(arg2))
        cmd = exclude_cmd.format(arg_str)

        results_1 = {s[0] for s in search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 | results_2)

        if n_results < n_history:
            output = get_cmd_output(cmd)
            assert n_history - len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)

    # Include and Exclude tests
    for arg1, arg2 in dual_search:
        cmd = in_ex_cmd.format(':'.join(arg1), ':'.join(arg2))

        full_files = set(sysv_dict.keys())
        results_1 = {s[0] for s in search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in search(sysv_dict, arg2[0], arg2[1])}

        include_result = results_1
        exclude_result = full_files - results_2

        full_result = include_result & exclude_result
        n_full_result = len(full_result)

        if arg1 in dne_search:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif n_full_result > 0:
            output = get_cmd_output(cmd)
            assert len(output) == n_full_result
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)


@pytest.mark.usefixtures("cleandir")
def test_search_parameter_and_parameter_value():
    n_history = 20

    sysv_dict = dict()
    for i in range(n_history):
        tracer = get_tracer()

        # half the experiments have list options
        if i % 2 == 0:
            add_lists_option(tracer)
            sysv = random_generate_sysv()
        else:
            sysv = random_generate_sysv(False)

        args = tracer.parse_args(sysv)
        args_file = tracer.args_file
        sysv_dict[args_file] = args

    list_args = ['list', 'flist']
    single_args = ['integer', 'float', 'double', 'device']
    dne_list_args = ['lists']
    arg_wo_value = ['list', 'integer']

    include_cmd = "lite_trace.py -i {}"
    exclude_cmd = "lite_trace.py -e {}"
    in_ex_cmd = "lite_trace.py -i {} -e {}"

    num_test = 1
    args_dict = {arg: pick_values(sysv_dict, arg, num_test)
                    for arg in list_args + single_args}
    exist_search = create_args_list(args_dict)

    dne_search = generate_dne_args(dne_list_args, cast=float)
    dne_search |= generate_dne_args(list_args, cast=float)

    arg_wo_search = generate_dne_args(arg_wo_value, int, upper_limit=None)

    all_search  = exist_search | dne_search | arg_wo_search

    dual_search = list(itertools.product(all_search, repeat=2))
    def process_arg(argument):
        if argument[1] != None:
            return ':'.join(argument)
        return argument[0]

    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(process_arg(arg1), process_arg(arg2))
        cmd = include_cmd.format(arg_str)

        results_1 = {s[0] for s in search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 & results_2)

        if arg1 in dne_search or arg2 in dne_search:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif n_results > 0:
            output = get_cmd_output(cmd)
            assert len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)

    # Exclude multiple arguments
    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(process_arg(arg1), process_arg(arg2))
        cmd = exclude_cmd.format(arg_str)

        results_1 = {s[0] for s in search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 | results_2)


        if n_results < n_history:
            output = get_cmd_output(cmd)
            assert n_history - len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)

    # Include and Exclude tests
    for arg1, arg2 in dual_search:
        cmd = in_ex_cmd.format(process_arg(arg1), process_arg(arg2))

        full_files = set(sysv_dict.keys())
        results_1 = {s[0] for s in search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in search(sysv_dict, arg2[0], arg2[1])}

        include_result = results_1
        exclude_result = full_files - results_2

        full_result = include_result & exclude_result
        n_full_result = len(full_result)

        if arg1 in dne_search:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)
        elif n_full_result > 0:
            output = get_cmd_output(cmd)
            assert len(output) == n_full_result
        else:
            with pytest.raises(RuntimeError):
                output = get_cmd_output(cmd)