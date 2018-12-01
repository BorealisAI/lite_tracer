# Copyright (c) 2018-present, Royal Bank of Canada.
# All rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.#
# Author: Yanshuai Cao

from lite_tracer import LTParser
import os
pjoin = os.path.join

if __name__ == '__main__':
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

    args = parser.parse_args()

    result_path = pjoin(args.result_folder,
                        '{}_{}'.format(args.data_name, args.hash_code))

    if not os.path.exists(args.result_folder):
        os.makedirs(args.result_folder)

    # simulate experiment and save results

    with open(result_path + '.txt', 'w') as wr:
        wr.write('Some amazing results!')
