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
total_steps = 500000
n_steps=5 # 5 default
n_envs = 16
norm_adv = True # original impl did NOT normalise.
# what are the reasons for normalising advantage.
# Perhaps it is required in the synchronous implementation??
vf_coef=0.5 # 0.5 default
gae_lambda=1.0 # 0.95 default, 1 represents classic advantage calculation
ent_coef=0.0 # 0.0 default # regularisation 

#action_module = sys.modules['CybORG.Shared.Actions']
#print(dir(action_module))
path = str(inspect.getfile(CybORG))
#print(path)
#path = path[:-10] + "/Shared/Scenarios/Scenario1b.yaml"
# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionA2CScenario.yaml"
#print(path)

cyborg = CybORG(path,'sim',fully_obs=True)
# print env controller network/environment state (ie not agent state!)
environment=cyborg.environment_controller.state
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg))
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)
# EnumAction Object
#OpenAIGymWrapper reset only provides the Observation
# reset is now done in learn() method
#obs = env.reset(agent="Red")
#print("Initial Action Space follwing Environment Reset")
#print(action_obj.possible_actions) # produces a list of the Action class objects of the enumerated space

# print openaigym action and observation spaces
print("Total timesteps: {}".format(total_steps))
print("Action Space Size: {}".format(env.action_space)) # Discrete
#print(env.observation_space) # Box

#print("Initial Observation following Environment Reset")
#print(obs)
#print(type(obs))
#print()
#print(env.environment_controller)
#print(unwrapped_state)
# for openai operations, state needs to be ndarray not python list
#state=np.array(state_list, dtype=np.float32)
state_space=env.observation_space
action_space=env.action_space

# initialise agent learning
#total_steps = num_episodes * step_limit_reached
agent.agent.initialise(env,gamma=gamma,n_steps=n_steps,n_envs=n_envs,ent_coef=ent_coef,vf_coef=vf_coef,normalize_advantage=norm_adv,gae_lambda=gae_lambda)
callback=agent.agent.learn_callback

done = False

start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
