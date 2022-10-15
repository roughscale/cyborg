# The following code contains work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.
# Additionally, we waive copyright and related rights in the utilized code worldwide through the CC0 1.0 Universal public domain dedication.

"""
Handling of privilege escalation action selection and execution
"""
#pylint: disable=invalid-name
from random import choice
from abc import ABC, abstractmethod
from typing import Tuple, Optional, List

from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.ConcreteActions.EscalateAction import (
        ExploreHost, EscalateAction
        )
from CybORG.Shared.Actions.Caldera.ConcreteActions.JuicyPotato import JuicyPotato
from CybORG.Shared.Actions.Caldera.ConcreteActions.V4L2KernelExploit import V4L2KernelExploit
from CybORG.Shared.Enums import (
        OperatingSystemType, TrinaryEnum)
from CybORG.Simulator.State import State

# pylint: disable=too-few-public-methods
class EscalateActionSelector(ABC):
    """
    Examines the target host and returns a selected applicable escalate action
    if any, as well as processes that are required to be genuine
    """
    # pylint: disable=missing-function-docstring
    @abstractmethod
    def get_escalate_action(self, *, state: State, session: int, target_session: int,
            agent: str, hostname: str) -> \
                    Optional[EscalateAction]:
        pass

class DefaultEscalateActionSelector(EscalateActionSelector):
    """
    Attempts to use Juicy Potato if windows, otherwise V4l2 kernel
    """
    def get_escalate_action(self, *, state: State,
            agent: str, hostname: str) -> \
                    Optional[EscalateAction]:
        #if state.sessions[agent][session].operating_system[hostname] == OperatingSystemType.WINDOWS:
        if True:
            return JuicyPotato(agent=agent)

        return V4L2KernelExploit(agent=agent)
_default_escalate_action_selector = DefaultEscalateActionSelector()


class PrivilegeEscalate(Action):
    """Selects and executes a privilege escalation action on a host"""
    def __init__(self, agent: str, hostname: str):
        super().__init__()
        self.agent = agent
        self.hostname = hostname
        self.escalate_action_selector = _default_escalate_action_selector

    def emu_execute(self) -> Observation:
        raise NotImplementedError

    def __perform_escalate(self, state:State)  -> Tuple[Observation, int]:

        #print(f"""
        #Host {self.hostname} attempting escalate:
        #Session {target_session.__dict__}""")

        # test if session is in a sandbox
        sub_action = self.escalate_action_selector.get_escalate_action(
                state=state, agent=self.agent, hostname=self.hostname)

        if sub_action is None:
            return Observation(success=False), -1

        return sub_action.sim_execute(state)

    def sim_execute(self, state: State) -> Observation:
        sub_action = ExploreHost(agent=self.agent)
        obs2 = sub_action.sim_execute(state)
        for host in obs2.data.values():
            try:
                host_processes = host['Processes']
                for proc in host_processes:
                    if proc.get('Service Name') == 'OTService':
                        break
            except KeyError:
                pass
            except TypeError:
                pass

        obs.combine_obs(obs2)
        return obs

    def __str__(self):
        return f"{self.__class__.__name__} {self.hostname}"
