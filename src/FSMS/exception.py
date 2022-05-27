class MachineError(Exception):
    """ Used for issues related to state transitions and current states.
    For instance, it is raised for invalid transitions or machine configuration issues.
    """

    def __init__(self, value: str):
        super(MachineError, self).__init__(value)
        self.value = value

    def __str__(self):
        return repr(self.value)
