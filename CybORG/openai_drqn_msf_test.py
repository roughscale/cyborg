from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
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
batch_size=32
num_prev_seq=16

# given larger action space.
total_steps=1000000
dueling=True
# at the moment, DRQN doesn't use double.
#double=True
#tensorboard_log = "./runs/drqn/"
tensorboard_log = None

n_envs = 1

env_config = {
   "fully_obs": False,
   "randomize_env": False,
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

agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg),max_params=env_config["max_params"])
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")

# initialise agent learning
agent.agent.initialise(
        env=env,
        gamma=gamma,
        initial_eps=initial_epsilon,
        final_eps=final_epsilon,
        total_steps=total_steps,
        batch_size=batch_size,
        num_prev_seq=num_prev_seq,
        dueling=dueling,
        tensorboard_log=tensorboard_log)

callback=agent.agent.learn_callback

start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
