class NoHistory(RuntimeError):
    """There are no lite tracer run history"""

class ShellError(RuntimeError):
    """Shell output had errors"""

class GitError(RuntimeError):
    """Might not be a git repository or git is not installed"""
    def __init__(self, message, errors):
        self.message = "git may not be configured properly"
        super(RuntimeError, self).__init__(message)
        self.errors = errors

class NoMatchError(RuntimeError):
    """There are no match for the given parameters"""

class NoParameterError(RuntimeError):
    """There are no match for the given parameters"""