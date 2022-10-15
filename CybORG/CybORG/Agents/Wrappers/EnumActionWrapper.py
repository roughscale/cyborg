import copy
import inspect, pprint
from typing import Union

from CybORG.Agents.SimpleAgents import BaseAgent
from CybORG.Agents.Wrappers import BaseWrapper
from CybORG.Shared import Results


class EnumActionWrapper(BaseWrapper):
    def __init__(self, env: Union[type, BaseWrapper] = None, agent: BaseAgent = None):
        super().__init__(env, agent)
        self.possible_actions = None
        self.action_signature = {}
        self.get_action_space('Red')

    def step(self, agent=None, action: int = None) -> Results:
        if action is not None:
            action = self.possible_actions[action]
        return super().step(agent, action)

    def action_space_change(self, action_space: dict) -> int:
        assert type(action_space) is dict, \
            f"Wrapper required a dictionary action space. " \
            f"Please check that the wrappers below the ReduceActionSpaceWrapper return the action space as a dict "
        possible_actions = []
        temp = {}
        params = ['action']
        # for action in action_space['action']:
        for i, action in enumerate(action_space['action']):
            if action not in self.action_signature:
                self.action_signature[action] = inspect.signature(action).parameters
            param_dict = {} # set for each action
            param_list = [{}] # set for each action
            #pprint.pprint(self.action_signature[action])
            #print("action: {0}".format(action))
            for p in self.action_signature[action]:
                # p is the key within the action (ie, parameter)
                temp[p] = [] # this doesn't seem to have any use
                # if p isn't 'action' add it the list of action params
                if p not in params:
                    params.append(p)  # params is the list of unique parameters for all actions. This is GLOBAL??
                    # not sure why this is required??
                # i think the following is attempting to retrieve the "known" parameters
                # from the agent's "internal state" (ip address, session, hostname, etc)
                # which resides in the "action space", so assuming we have no knowledge, 
                # any actions that depend upon these parameters will not be "possible actions"
                #print("action space of {0}".format(p))
                #pprint.pprint(action_space[p]) # this is the "internal state" of the parameters in the action space
                #print("initial params list p {0}: {1}".format(p,param_list))
                #print("param p: {0}".format(p))
                if len(action_space[p]) == 1:  # ie only has 1 entry?
                    # we need to update each current dict in the param_list with the new parameters
                    # the problem is how to add the initial p to an empty param list
                    if len(param_list) == 0: # ie empty list
                        param_list = [ { p: list(action_space[p].keys())[0] } ]
                    else:
                        for p_dict in param_list:
                          #print("p_dict: {0}".format(p_dict))
                          p_dict[p] = list(action_space[p].keys())[0]
                          #print("action_space[p] len = 1")
                          #print("param_dict: {0}".format(param_dict))
                else:
                    new_param_list = []
                    # TODO: for first p, need to add this to an empty list
                    for p_dict in param_list:
                        #print("p_dict: {0}".format(p_dict))
                        for key, val in action_space[p].items():
                            p_dict[p] = key
                            new_param_list.append({key: value for key, value in p_dict.items()})
                    #print("new_param_list: {0}".format(new_param_list))
                    param_list = new_param_list
            #print("final action param list: {0}".format(param_list))
            # param_list is a list of all combinations of parameters dicts for an Action class
            for p_dict in param_list:
                # so this create a list of Action Classes iterated with each combination of possible parameters
                possible_actions.append(action(**p_dict))  # action() is the Action Class

        self.possible_actions = possible_actions
        return len(possible_actions)
