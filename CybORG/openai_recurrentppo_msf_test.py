from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
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
gamma = .99   # discount rate
total_steps = 750000 
n_steps=1024 # 1024 default.
# rollout_steps = n_steps * n_envs
# batch_size must be a multiple of rollout_steps
# batch_size must be > 1 if norm_adv is True
batch_size=1024 # 128 default
n_epochs=10 # 10 default.
clip_range=0.1 # 0.2 default.
n_envs = 1 #
norm_adv = False # normalise adv across batch samples. Not in original paper 
vf_coef=1.0 # 0.5 default.
gae_lambda=1.0 # 0.95 default.
ent_coef=0.0 # 0.0 default.
target_kl=0.01 # 
# net_arch is expressed as proportions of the input vector size
net_arch = [1.0, 1.0] # matches TRPO
tensorboard_log = "./runs/recurrent_ppo"

# set max params for observation vector size
# other than MAX_HOSTS, they are max per host
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
curr_dir = os.getcwd()

path = path[:-10] + "/Shared/Scenarios/TestMSFSessionRecurrentPPOScenario.yaml"

cyborg = CybORG(path,'sim',env_config=env_config)

# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg),max_params=env_config["max_params"])
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

agent.agent.initialise(env,
        total_timesteps=total_steps,
        gamma=gamma,
        n_steps=n_steps,
        batch_size=int(batch_size*n_envs),
        n_epochs=n_epochs,
        clip_range=clip_range,
        n_envs=n_envs,
        ent_coef=ent_coef,
        vf_coef=vf_coef,
        normalize_advantage=norm_adv,
        gae_lambda=gae_lambda,
        target_kl=target_kl,
        net_arch=net_arch,
        tensorboard_log=tensorboard_log)

callback=agent.agent.learn_callback

start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
# save model to file
agent.agent.model.save(curr_dir+"/exports/recurrent_ppo.zip")

