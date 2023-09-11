from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
#from CybORG.Agents.SimpleAgents.RedRandomAgent import RedRandomAgent
from CybORG.Shared.Results import Results
import inspect
import sys
import random
import time
import copy
import hashlib
import numpy as np
from pprint import pprint

path = str(inspect.getfile(CybORG))
path = path[:-10] + "/Shared/Scenarios/TestSessionSB3Scenario.yaml"

cyborg = CybORG(path,'sim')

# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
unwrapped_action_space=agent.action_space.get_action_space()
#print("unwrapped_action_space")
#print(unwrapped_action_space)
action_env = EnumActionWrapper(cyborg)
# the following returns the EnumActionWrapped space which is just
# integer length of the Discrete action space
#print(action_env.get_action_space("Red"))
#sys.exit(0)
#print("wrap env in FixedFlatWrapper wrapping in EnumActionWrapper")
#wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg))
wrapped_env = FixedFlatWrapper(action_env)
env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")

total_steps=200000
# initialise agent learning
agent.agent.initialise(env,
        gamma=0.99, # discount rate
        initial_eps=1.0, # high explore factor
        final_eps=0.02, # high exploit factor
        total_steps=total_steps,
        double=True,
        dueling=True
        )

callback=agent.agent.learn_callback

done = False
start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.dqn.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
