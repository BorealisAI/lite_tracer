class NoHistory(RuntimeError):
    """There are no lite tracer run history"""


class ShellError(RuntimeError):
    """Shell output had errors"""


class GitError(RuntimeError):
    """Might not be a git repository or git is not installed"""
    def __init__(self, message=None, errors=None):
        self.message = "git may not be configured properly"
        super(GitError, self).__init__(message)
        self.errors = errors


class NoMatchError(RuntimeError):
    """There are no match for the given parameters"""


class NoParameterError(RuntimeError):
    """There are no match for the given parameters"""


class DestArgumentNotSuppported(RuntimeError):
    """There are no match for the given parameters"""
    def __init__(self, message=None, errors=None):
        self.message = "dest argument for argparser is not supported"
        super(DestArgumentNotSuppported, self).__init__(message)
        self.errors = errors


class ArgumentNotParsable(RuntimeError):
    """There are no match for the given parameters"""
