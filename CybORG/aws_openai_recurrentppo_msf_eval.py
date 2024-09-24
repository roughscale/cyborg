from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.evaluation import evaluate_policy
import inspect
import sys
import time
import copy
import json
import os
import psutil
import subprocess

# start msfrcpd
msfrcpd = subprocess.call(["/opt/metasploit-framework/bin/msfrpcd","-P","password"],close_fds=True)
# wait until service is available
time.sleep(5)

args = sys.argv
model_name = args[1]

# number of evaulation episodes
n_eval_eps=1

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

# get emulated config from file
emu_conf_file = open("aws_config.json","r")
emu_config = json.load(emu_conf_file)
env_config.update(emu_config)

path = str(inspect.getfile(CybORG))
n_envs=1
device = "auto"  # set to "cuda" or "mps" manually if desired

scenario_path = path[:-10] + "/Shared/Scenarios/TestMSFSessionRecurrentPPOScenario.yaml"
model_path=path[:-17] + "/exports/" + model_name

cyborg = CybORG(scenario_path,'aws',env_config=env_config)

agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg),max_params=env_config["max_params"])
# wraps env in DummyVecEnv VecEnv environment
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

# load agent from export file
model=agent.agent.load("RecurrentPPO",model_path,device=device)

start=time.time()
print("Evaluation start: {}".format(time.ctime(start)))
print()
mean_reward, std_reward = evaluate_policy(model.model.policy, env, n_eval_episodes=n_eval_eps, deterministic=True)
end=time.time()
print(mean_reward)
print(std_reward)
print("Evaluation end: {}".format(time.ctime(end)))
print("Evaluation duration: {}s".format(end-start))
