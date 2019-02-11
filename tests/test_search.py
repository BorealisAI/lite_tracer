import itertools
import pytest

import helper
from helper import cleandir

INCLUDE_CMD = "lite_trace.py -i {}"
EXCLUDE_CMD = "lite_trace.py -e {}"
IN_EX_CMD = "lite_trace.py -i {} -e {}"


@pytest.mark.usefixtures("cleandir")
# Save the arguments to the tracer settings file
# Search the files
def test_search_parameter():
    n_history = 20

    # Generate a set of results with half with list options
    for i in range(n_history):
        tracer = helper.get_tracer()
        if i % 2 == 0:
            helper.add_lists_option(tracer)
            sysv = helper.generate_sysv(i)
        else:
            sysv = helper.generate_sysv(i, False)
        tracer.parse_args(sysv)

    list_args = ['list', 'flist']
    single_args = ['integer', 'float', 'device']
    dne_args = ['lists']

    all_args = list_args + single_args + dne_args

    # Include single arguments
    for arg in all_args:
        cmd = INCLUDE_CMD.format(arg)
        if arg in list_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        elif arg in single_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_history
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)

    # Exclude single arguments
    for arg in all_args:
        cmd = EXCLUDE_CMD.format(arg)
        if arg in list_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        elif arg in single_args:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        else:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_history

    # Include multiple arguments
    for arg1, arg2 in itertools.product(all_args, repeat=2):
        arg_str = '{} {}'.format(arg1, arg2)
        cmd = INCLUDE_CMD.format(arg_str)

        if arg1 in dne_args or arg2 in dne_args:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif arg1 in list_args or arg2 in list_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        else:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_history

    # Exclude multiple arguments
    for arg1, arg2 in itertools.product(all_args, repeat=2):
        arg_str = '{} {}'.format(arg1, arg2)
        cmd = EXCLUDE_CMD.format(arg_str)

        if arg1 in single_args or arg2 in single_args:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif arg1 in list_args or arg2 in list_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        else:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_history

    # Include and Exclude tests
    for arg1, arg2 in itertools.product(all_args, repeat=2):
        cmd = IN_EX_CMD.format(arg1, arg2)

        if arg1 in dne_args:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif arg2 in single_args:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif arg1 in single_args and arg2 in list_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == (n_history / 2)
        elif arg1 in single_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_history
        elif arg1 in list_args and arg2 in dne_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == (n_history / 2)
        elif arg1 in list_args and arg2 in dne_args:
            output = helper.get_cmd_output(cmd)
            assert len(output) == int(n_history / 2)
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)


@pytest.mark.usefixtures("cleandir")
def test_search_parameter_value():
    n_history = 20

    sysv_dict = dict()
    for i in range(0, n_history * 2, 2):
        tracer = helper.get_tracer()

        # half the experiments have list options
        if i % 2 == 0:
            helper.add_lists_option(tracer)
            sysv = helper.generate_sysv(i)
        else:
            sysv = helper.generate_sysv(i, False)

        args = tracer.parse_args(sysv)
        args_file = tracer.args_file
        sysv_dict[args_file] = args

    list_args = ['list', 'flist']
    single_args = ['integer', 'float', 'device']
    dne_list_args = ['lists']

    include_cmd = "lite_trace.py -i {}"
    exclude_cmd = "lite_trace.py -e {}"
    in_ex_cmd = "lite_trace.py -i {} -e {}"

    num_test = 2
    args_dict = {arg: helper.pick_values(sysv_dict, arg, num_test)
                 for arg in list_args + single_args}
    exist_search = helper.create_args_list(args_dict)

    dne_search = helper.generate_dne_args(dne_list_args, cast=float)
    dne_search |= helper.generate_dne_args(list_args, cast=float)

    all_search = exist_search | dne_search

    # Include single arguments
    for param, value in all_search:
        cmd = include_cmd.format(param + ':' + value)
        n_results = len(helper.search(sysv_dict, param, value))

        if n_results > 0:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_results
        else:
            if (param, value) in exist_search:
                raise RuntimeError
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)

    # Exclude single arguments
    for param, value in all_search:
        cmd = exclude_cmd.format(param + ':' + value)
        n_results = len(helper.search(sysv_dict, param, value))

        if n_results < n_history:
            output = helper.get_cmd_output(cmd)
            assert n_history - len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)

    # Include multiple arguments

    dual_search = list(itertools.product(all_search, repeat=2))

    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(':'.join(arg1), ':'.join(arg2))
        cmd = include_cmd.format(arg_str)

        results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 & results_2)

        if arg1 in dne_search or arg2 in dne_search:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif n_results > 0:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)

    # Exclude multiple arguments
    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(':'.join(arg1), ':'.join(arg2))
        cmd = exclude_cmd.format(arg_str)

        results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 | results_2)

        if n_results < n_history:
            output = helper.get_cmd_output(cmd)
            assert n_history - len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)

    # Include and Exclude tests
    for arg1, arg2 in dual_search:
        cmd = in_ex_cmd.format(':'.join(arg1), ':'.join(arg2))

        full_files = set(sysv_dict.keys())
        results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

        include_result = results_1
        exclude_result = full_files - results_2

        full_result = include_result & exclude_result
        n_full_result = len(full_result)

        if arg1 in dne_search:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif n_full_result > 0:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_full_result
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)


@pytest.mark.usefixtures("cleandir")
def test_search_parameter_and_value():
    n_history = 20

    sysv_dict = dict()
    for i in range(0, n_history * 2, 2):
        tracer = helper.get_tracer()

        # half the experiments have list options
        if i % 2 == 0:
            helper.add_lists_option(tracer)
            sysv = helper.generate_sysv(i)
        else:
            sysv = helper.generate_sysv(i, False)

        args = tracer.parse_args(sysv)
        args_file = tracer.args_file
        sysv_dict[args_file] = args

    list_args = ['list', 'flist']
    single_args = ['integer', 'float', 'device']
    dne_list_args = ['lists']
    arg_wo_value = ['list', 'integer']

    include_cmd = "lite_trace.py -i {}"
    exclude_cmd = "lite_trace.py -e {}"
    in_ex_cmd = "lite_trace.py -i {} -e {}"

    num_test = 1
    args_dict = {arg: helper.pick_values(sysv_dict, arg, num_test)
                 for arg in list_args + single_args}
    exist_search = helper.create_args_list(args_dict)

    dne_search = helper.generate_dne_args(dne_list_args, cast=float)
    dne_search |= helper.generate_dne_args(list_args, cast=float)

    arg_wo_search = helper.generate_dne_args(arg_wo_value, int, upper_limit=None)

    all_search = exist_search | dne_search | arg_wo_search

    dual_search = list(itertools.product(all_search, repeat=2))

    def process_arg(argument):
        if argument[1] is not None:
            return ':'.join(argument)
        return argument[0]

    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(process_arg(arg1), process_arg(arg2))
        cmd = include_cmd.format(arg_str)

        results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 & results_2)

        if arg1 in dne_search or arg2 in dne_search:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif n_results > 0:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)

    # Exclude multiple arguments
    for arg1, arg2 in dual_search:
        arg_str = '{} {}'.format(process_arg(arg1), process_arg(arg2))
        cmd = exclude_cmd.format(arg_str)

        results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

        n_results = len(results_1 | results_2)

        if n_results < n_history:
            output = helper.get_cmd_output(cmd)
            assert n_history - len(output) == n_results
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)

    # Include and Exclude tests
    for arg1, arg2 in dual_search:
        cmd = in_ex_cmd.format(process_arg(arg1), process_arg(arg2))

        full_files = set(sysv_dict.keys())
        results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
        results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

        include_result = results_1
        exclude_result = full_files - results_2

        full_result = include_result & exclude_result
        n_full_result = len(full_result)

        if arg1 in dne_search:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)
        elif n_full_result > 0:
            output = helper.get_cmd_output(cmd)
            assert len(output) == n_full_result
        else:
            with pytest.raises(RuntimeError):
                output = helper.get_cmd_output(cmd)


# @pytest.mark.usefixtures("cleandir")
# def test_comparison_search():
#     n_history = 20

#     sysv_dict = dict()

#     end = n_history // 2
#     start = -1 * end

#     for i in range(start, end):
#         tracer = helper.get_tracer()

#         # half the experiments have list options
#         if i % 2 == 0:
#             helper.add_lists_option(tracer)
#             sysv = helper.generate_sysv(i)
#         else:
#             sysv = helper.generate_sysv(i, False)

#         args = tracer.parse_args(sysv)
#         args_file = tracer.args_file
#         sysv_dict[args_file] = args

#     list_args = ['list', 'flist']
#     single_args = ['integer', 'float', 'device']
#     arg_wo_value = ['integer', 'list']
#     dne_args = ['lists']
#     operator = ['<', '>', '<=', '>=', '==', ':']

#     include_cmd = "lite_trace.py -i {}"
#     exclude_cmd = "lite_trace.py -e {}"
#     in_ex_cmd = "lite_trace.py -i {} -e {}"

#     num_test = 1
#     args_dict = {arg: helper.pick_values(sysv_dict, arg, num_test)
#                  for arg in list_args + single_args}
#     exist_search = helper.create_args_list(args_dict)

#     dne_search = helper.generate_dne_args(dne_args, cast=float)
#     dne_search |= helper.generate_dne_args(list_args, cast=float)

#     arg_wo_search = helper.generate_dne_args(arg_wo_value, int, upper_limit=None)

#     all_search = exist_search | dne_search | arg_wo_search

#     dual_search = list(itertools.product(all_search, repeat=2))

#     def process_arg(argument):
#         if argument[1] is not None:
#             return ':'.join(argument)
#         return argument[0]

#     for arg1, arg2 in dual_search:
#         arg_str = '{} {}'.format(process_arg(arg1), process_arg(arg2))
#         cmd = include_cmd.format(arg_str)

#         results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
#         results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

#         n_results = len(results_1 & results_2)

#         if arg1 in dne_search or arg2 in dne_search:
#             with pytest.raises(RuntimeError):
#                 output = helper.get_cmd_output(cmd)
#         elif n_results > 0:
#             output = helper.get_cmd_output(cmd)
#             assert len(output) == n_results
#         else:
#             with pytest.raises(RuntimeError):
#                 output = helper.get_cmd_output(cmd)

#     # Exclude multiple arguments
#     for arg1, arg2 in dual_search:
#         arg_str = '{} {}'.format(process_arg(arg1), process_arg(arg2))
#         cmd = exclude_cmd.format(arg_str)

#         results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
#         results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

#         n_results = len(results_1 | results_2)

#         if n_results < n_history:
#             output = helper.get_cmd_output(cmd)
#             assert n_history - len(output) == n_results
#         else:
#             with pytest.raises(RuntimeError):
#                 output = helper.get_cmd_output(cmd)

#     # Include and Exclude tests
#     for arg1, arg2 in dual_search:
#         cmd = in_ex_cmd.format(process_arg(arg1), process_arg(arg2))

#         full_files = set(sysv_dict.keys())
#         results_1 = {s[0] for s in helper.search(sysv_dict, arg1[0], arg1[1])}
#         results_2 = {s[0] for s in helper.search(sysv_dict, arg2[0], arg2[1])}

#         include_result = results_1
#         exclude_result = full_files - results_2

#         full_result = include_result & exclude_result
#         n_full_result = len(full_result)

#         if arg1 in dne_search:
#             with pytest.raises(RuntimeError):
#                 output = helper.get_cmd_output(cmd)
#         elif n_full_result > 0:
#             output = helper.get_cmd_output(cmd)
#             assert len(output) == n_full_result
#         else:
#             with pytest.raises(RuntimeError):
#                 output = helper.get_cmd_output(cmd)
