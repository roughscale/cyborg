import random
import hashlib
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from gym import spaces
from CybORG.Shared import Results
from CybORG.Shared.State import State
import numpy as np

from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines.deepq.policies import MlpPolicy
from stable_baselines import DQN

from stable_baselines.common.callbacks import BaseCallback

class RedSB2DQNFCAgent(BaseAgent):

    """ a red agent that uses Double Q network with a fully connected layer """
    """ this uses the stable_baselines3 implementation """

    def __init__(self):

        self.dqn = None
        self.dqn_policy = None
        self.steps_done = 0

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

    def initialise(self, env, state_space, gamma, alpha, initial_eps, final_eps, total_steps, num_episodes, double_dqn = False, dueling_dqn = True):
        """ set up DQN """
        """ lr_schedule needs to be of Schedule type """
        self.env = env
        #print(type(state_space))
        #print(type(env.observation_space))
        #print(type(env.action_space))
        # following is for SB3
        #lr_schedule=get_linear_fn(initial_eps,final_eps,1.0)
        #print(lr_schedule())
        #print(type(lr_schedule))
        #net_arch=[1024,256]
        input_size=state_space.shape[0]
        #net_arch=[input_size]
        net_arch=[input_size,input_size]
        
        learning_rate = float(0.0001)
        buffer_size = int(total_steps/5)
        exploration_fraction=float(0.9)
        learning_starts = int(total_steps/1000)
        target_network_update_freq = int(total_steps/5000)

        prioritized_replay_alpha=float(0.9)
        prioritized_replay_beta0=float(0.4)
        prioritized_replay_beta_iters=int(total_steps/50)

        double_q = double_dqn
        dueling = dueling_dqn

        print("Hyperparameters:")
        print("Total Steps {}".format(total_steps))
        print("Input Size {}".format(input_size))
        print("Net Arch: {}".format(net_arch))
        print("Initial Epsilon: {}".format(initial_eps))
        print("Final Epsilon: {}".format(final_eps))
        print("Exploration Fraction: {}".format(exploration_fraction))
        print("Gamma: {}".format(gamma))
        print("Double Q: {}".format(double_q))
        print("Dueling: {}".format(dueling))
        print("Learning Rate: {}".format(learning_rate))
        print("PER Alpha: {}".format(prioritized_replay_alpha))
        print("PER Beta0: {}".format(prioritized_replay_beta0))
        print("PER Beta Iterations: {}".format(prioritized_replay_beta_iters))
        print("Learning Starts {}".format(learning_starts))
        print("Replay Buffer Size {}".format(buffer_size))
        print("Target network update freq: {}".format(target_network_update_freq))
        print()

        self.dqn = DQN(
                policy="MlpPolicy",
                env=env,
                learning_rate=learning_rate,
                buffer_size=buffer_size,
                learning_starts=learning_starts,
                batch_size=32, # default is 32
                #tau=1.0, # default. Doesn't scale the target network values when updating
                gamma=gamma,
                train_freq=1, #default is 4
                double_q = double_q,
                policy_kwargs={"layers": net_arch, "dueling": dueling },
                target_network_update_freq=target_network_update_freq,
                prioritized_replay=True,
                prioritized_replay_alpha=prioritized_replay_alpha,
                prioritized_replay_beta0=prioritized_replay_beta0,
                prioritized_replay_beta_iters=prioritized_replay_beta_iters,
                prioritized_replay_eps=float(0.000001),
                exploration_fraction=exploration_fraction,
                exploration_initial_eps=initial_eps,
                exploration_final_eps=final_eps,
                tensorboard_log=None, #default
                verbose=1,
                seed=None, #default
                _init_setup_model=True # default
        )

        # specific to policy
        self.num_actions = self.env.action_space.n
        #print(self.num_actions)
        obs_dim = state_space.shape
        #print(obs_dim)
        #hidden_sizes = [64,64] # schwartz default. why this?
        hidden_sizes = [256] # schwartz reported arch
        # should perhaps re-use schwartz' architecture of one 256 layer.
        # how many "features" does the state space contain??
        # 

        self.learn_callback = LearnCallback(self.dqn)

class LearnCallback(BaseCallback):

    def __init__(self, model):
        super().__init__(self)
        super().init_callback(model)
        env = None

    def _on_training_start(self):
        #print(self.globals)
        #print(self.training_env)
        #print(dir(self.training_env))
        #print(self.training_env.envs)
        # SB3 is multi-agent
        ##self.env=self.training_env.envs[0]
        # SB2 is single-agent
        self.env=self.training_env
        # Monitor class
        #print(dir(self.env))
        #print(self.locals)
        # OpenAIGymWrapper class
        #print(env.env)
        # FixedFlatObsWrapper class
        #print(env.env.env)
        #print(self.training_env.observation_space)
        return True

    def _on_step(self):
        #print(self.env.render)
        #self.env.render(self,mode=None,kwargs=None) 
        #print(self.locals)
        #print("Num Collected Episodes: {}".format(self.locals["num_collected_episodes"]))
        #print("Num Collected Steps: {}".format(self.locals["num_collected_steps"]))
        #print()
        # infos observation is unwrapped (ie python list not a numpy array)
        #print("Infos: {}".format(self.locals["infos"]))
        #print("Obs: {}".format(self.locals["infos"][0]["state"]))
        # SB3
        #print("Obs Hash: {}".format(State.get_state_hash(self.locals["infos"][0]["state"])))
        # SB2. 
        #with np.printoptions(threshold=6000,linewidth=300):
        #   print("State: {}".format(self.locals["info"]["state"]))
        #print("Obs Hash: {}".format(State.get_state_hash(self.locals["info"]["state"])))
        #print("New Obs: {}".format(self.locals["new_obs"][0]))
        #print("Comp Obs: {}".format(np.array_equal(self.locals["infos"][0]["state"],self.locals["new_obs"][0])))
        #diff = np.subtract(self.locals["infos"][0]["state"],self.locals["new_obs"][0])
        #print("Diff obs: {}".format(diff))
        #print("Diff shape: {}".format(diff.shape))
        #print("New Obs Hash: {}".format(State.get_state_hash(self.locals["new_obs"])))
        print("Action: {}".format(self.locals["action"]))
        print("Reward: {}".format(self.locals["rew"]))
        print("Done: {}".format(self.locals["done"]))
        print()
        return True
        #pass

