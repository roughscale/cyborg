from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
#from CybORG.Agents.Wrappers.FixedFlatStateWrapper import FixedFlatStateWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
#from CybORG.Agents.SimpleAgents.RedRandomAgent import RedRandomAgent
from CybORG.Shared.Results import Results
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.evaluation import evaluate_policy
import inspect
import sys
import time
import copy
import os

# set vars
# initialise Q learning parameters
gamma = .99   # discount rate
initial_epsilon = 1.0 # high explore factor
final_epsilon = 0.02  # explore/exploit factor
batch_size=32
num_prev_seq=16

# given larger action space.
total_steps=1000000
double=False
dueling=True
tensorboard_log="./runs/drqn"
device = "auto"  # set to "cuda" or "mps" manually if desired

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
curr_dir = os.getcwd()

n_envs=1

scenario_path = path[:-10] + "/Shared/Scenarios/TestMSFSessionDRQNScenario.yaml"

cyborg = CybORG(scenario_path,'sim',env_config=env_config)

agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg),max_params=env_config["max_params"])
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

# initialise agent learning
agent.agent.initialise(env,
        gamma=gamma,
        initial_eps=initial_epsilon,
        final_eps=final_epsilon,
        total_steps=total_steps,
        batch_size=batch_size,
        num_prev_seq=num_prev_seq,
        dueling=dueling,
        tensorboard_log=tensorboard_log,
        device=device)

callback=agent.agent.learn_callback

start=time.time()
print("Training start: {}".format(time.ctime(start)))
print()
print(agent.agent)
print(dir(agent.agent))
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Training end: {}".format(time.ctime(end)))
print("Training duration: {}".format(end-start))
agent.agent.model.save(curr_dir+"/exports/drqn.zip")
