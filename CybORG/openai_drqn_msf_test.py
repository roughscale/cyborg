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
alpha = .5    # learning rate. NOT USED. Separate LR schedule is created
gamma = .99   # discount rate
initial_epsilon = 1.0 # high explore factor
final_epsilon = 0.02  # explore/exploit factor

#step_limit_reached=200
num_episodes=1000 # NOT USED. Total steps is used
#num_evals=100

# given larger action space.
total_steps=500000
# at the moment, DRQN doesn't use double or dueling.
#double=True
#dueling=False

n_envs = 1

env_config = {
   "fully_obs": False,
   "max_params": {
        "MAX_HOSTS": 5,
        "MAX_PROCESSES": 2,
        "MAX_CONNECTIONS": 2,
        "MAX_VULNERABILITIES": 1,
        "MAX_INTERFACES": 2,
        "MAX_SESSIONS": 3,
        "MAX_USERS": 5,
        "MAX_FILES": 0,
        "MAX_GROUPS": 0,
        "MAX_PATCHES": 0
   }
}
path = str(inspect.getfile(CybORG))
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionDRQNScenario.yaml"

cyborg = CybORG(path,'sim',env_config=env_config)

# print env controller network/environment state (ie not agent state!)
environment=cyborg.environment_controller.state

agent=cyborg.environment_controller.agent_interfaces["Red"]
#unwrapped_action_space=agent.action_space.get_action_space()
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg),max_params=env_config["max_params"])
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")

# print openaigym action and observation spaces
print(env.action_space) # Discrete
#print(env.observation_space) # Box

action_space=env.action_space

# initialise agent learning
#total_steps = num_episodes * step_limit_reached
agent.agent.initialise(env,gamma,initial_epsilon,final_epsilon,total_steps)
callback=agent.agent.learn_callback

done = False
terminal_states = set([])
total_states = set([])
start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
