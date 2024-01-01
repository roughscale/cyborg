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
total_steps = 600000
n_steps=1024 # 1024 default. 128 used in Atari PPO
# rollout_steps = n_steps * n_envs
# batch_size must be a multiple of rollout_steps
# batch_size must be > 1 if norm_adv is True
batch_size=1024 # 128 default  32x8 spec in Atari. This is now per env
n_epochs=10 # 10 default. atari PPO spec is 3. didn't help
clip_range=0.1 # 0.2 default. atari PPO spec is 0.1 x annealed 1 to 0
n_envs = 2 # atari PPO is 8
norm_adv = False # normalise adv across batch samples. Not in original paper
vf_coef=1.0 # 0.5 default. atari spec is 1
gae_lambda=1.0 # 0.95 default. atari spec is 0.95
ent_coef=0.01 # 0.0 default. atari spec is 0.01
#target_kl=0.01 # float or None (default)
target_kl=None
# net_arch is expressed as proportions of the input vector size
#net_arch = [ 1.0, 0.5]
net_arch = [1.0]

#action_module = sys.modules['CybORG.Shared.Actions']
#print(dir(action_module))
path = str(inspect.getfile(CybORG))
#print(path)
#path = path[:-10] + "/Shared/Scenarios/Scenario1b.yaml"
# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionPPOScenario.yaml"
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
agent.agent.initialise(env,gamma=gamma,n_steps=n_steps,batch_size=int(batch_size*n_envs), n_epochs=n_epochs, clip_range=clip_range, n_envs=n_envs,ent_coef=ent_coef,vf_coef=vf_coef,normalize_advantage=norm_adv,gae_lambda=gae_lambda,target_kl=target_kl,net_arch=net_arch)
callback=agent.agent.learn_callback

done = False

start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
