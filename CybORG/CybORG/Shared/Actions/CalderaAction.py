# Copyright DST Group. Licensed under the MIT license.
from .Action import Action


class CalderaAction(Action):
    """Class for an action to be executed by the Caldera C2 framework

    Parameters
    ----------
    operation : Operation
        the Caldera Operation object
    planning_svc: PlanningService
        the Caldera PlanningService object
    """

    def __init__(self, operation: Operation, planning_svc: PlanningService):
        """
        Parameters
        ----------
        session : int
            the id of the session to perform action in
        """
        super().__init__()
        self.operation = operation
        self.planning_svc = planning_svc
        self.ability_name = None
        self.executor_params= None

    def emu_execute(self, c2_agent: Agent):
        """Execute and action in the Caldera C2 framework

        Parameters
        ----------
        c2_agent : Agent
           the Agent object of the Caldera agent which will execute the Action

        Returns
        -------
        Observation
            Result of performing action
        """
        action_link = await self._get_links(agent=c2_agent, ability=ability)
        # if ability is supplied, can we just generate the link
        # rather than get all the abilities, generate all the links and then select the link?
        # need to filter this
        action_ability = await self.planning_svc.get_service('data_svc').locate('abilities')
        action_link=await self.planning_svc.generate_and_trim_links(c2_agent, self.operation, action_ability, trim=False)

        action_link_facts = self.executor_params
        #  ie: raw_action.facts=[Fact(trait='target.ip',value='192.168.121.8',score=1)]

        # use planning_svc.add_test_variants to populate the commands vars and generate link id

        actions = await self.planning_svc.add_test_variants([action_link], c2_agent, facts=action_link_facts,
            operation=self.operation, trim_unset_variables=True, trim_missing_requirements=True)
        action = actions[0]

        next_link=[]
        next_link.append(await self.operation.apply(action))

        await self.operation.wait_for_links_completion(next_link)

        # need to get the output of the link to then marshall an Observation object return


    def sim_execute(self, state):
        raise NotImplementedError

    def __str__(self):
        return (f"{self.__class__.__name__}: Operation={self.operation} Planning_Service={self.planning_svc}"\n)
