from CybORG.Shared.Observation import Observation
from pprint import pprint
import copy
import hashlib

import CybORG.Shared.Enums as CyEnums

class TrueState(Observation):

    """ 
        This is a subclass of the Observation class.  It is to isolate its usage as a "true state" in the 
        Simulated case.
    """
    def __init__(self, success: bool = None):
        super().__init__(success)

