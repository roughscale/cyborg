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
import os
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
n_steps=512 # 5 default
n_envs = 1
norm_adv = False # original impl did NOT normalise.
# what are the reasons for normalising advantage.
# Perhaps it is required in the synchronous implementation??
vf_coef=0.5 # 0.5 default
gae_lambda=1.0 # 0.95 default, 1 represents classic advantage calculation
ent_coef=0.0 # 0.0 default # regularisation 

# set max params for observation vector sizei
# other than MAX_HOSTS, they are max per host
env_config = {
   "fully_obs": True,
   "max_params": {
        "MAX_HOSTS": 5,
        "MAX_PROCESSES": 5,
        "MAX_CONNECTIONS": 2,
        "MAX_VULNERABILITIES": 1,
        "MAX_INTERFACES": 2,
        "MAX_SESSIONS": 5,
        "MAX_USERS": 5,
        "MAX_FILES": 0,
        "MAX_GROUPS": 0,
        "MAX_PATCHES": 0
   }
}

path = str(inspect.getfile(CybORG))
curr_dir = os.getcwd()

# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionA2CScenario.yaml"

#print(path)

cyborg = CybORG(path,'sim',env_config=env_config)
# print env controller network/environment state (ie not agent state!)
environment=cyborg.environment_controller.state
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg), max_params=env_config["max_params"])
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
# save model to file
agent.agent.model.save(curr_dir+"/exports/a2c.zip")

