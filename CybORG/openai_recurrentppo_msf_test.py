from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.FixedFlatStateWrapper import FixedFlatStateWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
#from CybORG.Agents.SimpleAgents.RedRandomAgent import RedRandomAgent
from CybORG.Shared.Results import Results
from CybORG.Shared.State import State
from stable_baselines3.common.env_util import make_vec_env
import inspect
import sys
import random
import time
import copy
import hashlib
import numpy as np
from pprint import pprint


# set vars
# initialise Q learning parameters
gamma = .99   # discount rate
total_steps = 1000000
n_steps=1024
batch_size=32
clip_range=0.2
n_envs = 4

#action_module = sys.modules['CybORG.Shared.Actions']
#print(dir(action_module))
path = str(inspect.getfile(CybORG))
#print(path)
#path = path[:-10] + "/Shared/Scenarios/Scenario1b.yaml"
# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionRecurrentPPOScenario.yaml"
#print(path)

cyborg = CybORG(path,'sim',fully_obs=False)
#cyborg = make_vec_env(lambda: CybORG(path,'sim',fully_obs=False))

# print env controller network/environment state (ie not agent state!)
environment=cyborg.environment_controller.state
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg))
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)
#OpenAIGymWrapper reset only provides the Observation
# reset is now done in learn() method
#obs = env.reset(agent="Red")
#print("Initial Action Space follwing Environment Reset")
#print(action_obj.possible_actions) # produces a list of the Action class objects of the enumerated space

# print openaigym action and observation spaces
print(env.action_space) # Discrete
#print(env.observation_space) # Box
#total_steps = num_episodes * step_limit_reached
agent.agent.initialise(env, gamma=gamma, n_steps=n_steps, batch_size=batch_size, clip_range=clip_range, n_envs=n_envs)
callback=agent.agent.learn_callback
done = False

start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
