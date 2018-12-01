![lite_tracer Logo](https://bitbucket.org/rbcmllab/lite_tracer/src/master/logos/Litetracer-Logo-Full-LB.png)

--------------------------------------------------------------------------------

# LiteTracer: a light weight experiment reproducibility toolset

LiteTracer acts as a drop-in replacement for argparse, and it can generate unique identifiers for experiments in addition to what argparse already does.
Along with a reverse lookup tool, LiteTracer can trace-back the state of a project that generated any result tagged by the identifier.
The identifiers are unique based on the combination of four factors:
1) code version;
2) un-committed code changes
3) untracked files in the project;
3) any command line arguments supplied at runtime.

As the name suggests, LiteTracer is desinged to be as lightweight as possible. It is a minimalistic toolset and convention to enable reproducible experimental research, rather than a framework that one has to learn about. 

## To track:

1) Instead of using argparse `from argparse import ArgumentParser`, use `LTParser`, e.g.:

```
from lite_tracer import LTParser
parser = LTParser("...")
parser.add_argument(...)
args = parser.parse_args()
```

2) Then in any result file you save (tensorboard results included), include as part of filename: `args.hash_code`, for example:
```
result_path = './results/{}/{}'.format(args.data_name, args.hash_code)
```

3) Never manually change output filenames (e.g. use generated filenames directly in your latex source code)

## Given hash code, to trace back to the exact configuration that produced a result:
By default, LTParser saves tracking information to ./lt_records/<args.hash_code>, which has three things:

`settings_<args.hash_code>.txt` which has all arguments used for the experiments (command line supplied merged with defaults),
 as well as some dynamically collected information such as git version information
 
`diff.patch` any source code change from last committed version

`untracked/` any untracked and not ingored files/folders in the project dir

## To find all results with certain param settings:
`lite_trace.py --include [[[PARAM1:VAL1] PARAM2:VAL2] ...] --exclude [[[PARAM1:VAL1] PARAM2:VAL2] ...]`

## See a complete example in example/lite_tracer_example.py
Example search:
`lite_trace.py --exclude bsz:12 git_label:f6afeb8 --include sgd`
