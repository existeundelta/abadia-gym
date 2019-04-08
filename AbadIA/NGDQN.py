import random
import numpy as np
import logging

from keras.models import Sequential, load_model
from keras.layers import Dense, Dropout
from keras.optimizers import Adam
from collections import deque

# TODO JT:
# 1) Need a method to fill the memory with actions
# 2) Need a method to training / validating out the agent
# 3) A method to get the history of the training/validating
# 4) a method to convert from the json format to the input vector

class NGDQN:
    def __init__(self, env=None):
        self.env     = env
        self.memory  = deque(maxlen=3000)
        # Exploring or playing

        self.gamma = 0.85
        self.epsilon = 1.0
        self.epsilon_min = 0.01 # previously 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.005
        self.tau = .125

        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%d-%m-%y %H:%M:%S',
                            level=logging.INFO)
        self.logging = logging

        # TODO JT: we need to implement this when goes to production
        # if env != None:
        #     if env.modelName == None:
        #         self.model        = self.create_model()
        #         self.target_model = self.create_model()
        #     else:
        #         if (env.gsBucket != None):
        #             self.logging.info("I will download from {} the file {}".format(env.gsBucket, env.modelName))
        #             env.download_blob(env.modelName, env.modelName)
        #
        #         self.model        = self.load_model(env.modelName)
        #         self.target_model = self.load_model(env.modelName)

    def create_model(self, input_dim=10, output_dim=9):
        self.logging.info("Creating a new model v5")
        model   = Sequential()
        # TODO JT we need to increment the input vector dim

        state_shape  = input_dim # self.env.observation_space.shape

        # TODO JT we need to redesign the internal lawyers

        model.add(Dense(24, input_dim=input_dim, activation="relu"))
        model.add(Dense(48, activation="relu"))
        model.add(Dense(24, activation="relu"))
        model.add(Dense(output_dim))
        model.compile(loss="mean_squared_error",
            optimizer=Adam(lr=self.learning_rate))
        return model

    def load_model(self, name):
        self.logging.info("Loading a model from: ({})".format(name))
        return load_model(name)

    def act(self, vector):
        self.epsilon *= self.epsilon_decay
        self.epsilon = max(self.epsilon_min, self.epsilon)
        if (self.env == None):
            return act_prediction(vector)
        else:
            return act_env(vector)

    def act_prediction(self, vector):

        # self.env.vector = vector

        predictions = self.model.predict(vector)[0]
        # self.env.predictions = predictions
        # TODO JT: how to get the action_space
        # final = np.zeros(self.env.action_space.n)

        action = np.argmax(final)
        self.logging.info("vector:      {}              ".format(vector))
        self.logging.info("predictions: {}              ".format(predictions))
        self.logging.info("final:       {}              ".format(final))
        self.logging.info("Action:      {} Prediction: {}    ".format(action, final[action]))

        return action

    def act_env(self, vector):

        vector = self.env.stateVector()
        self.env.vector = vector

        if (self.env.playing is False) and (np.random.random() < self.epsilon):
            action = self.env.action_space.sample()
            self.env.logging.info("e-greedy: {}  epsilon: {}<----               ".format(action, self.epsilon))
            actionType = "E"
            self.env.calculated_predictions = []
            self.env.final_predictions = []
        else:
            predictions = self.model.predict(vector)[0]
            self.env.predictions = predictions
            final = np.zeros(self.env.action_space.n)

            for ii in range(0,self.env.action_space.n):
                if (self.env.valMovs[ii] >= 1):
                    final[ii] = predictions[ii]
                else:
                    final[ii] = -99 # predictions[ii]*0.9

            action = np.argmax(final)
            self.env.logging.info("vector:      {}              ".format(vector))
            self.env.logging.info("predictions: {}              ".format(predictions))
            self.env.logging.info("final:       {}              ".format(final))
            self.env.logging.info("Action:      {} Prediction: {}    ".format(action, final[action]))
            actionType = "P"

            self.env.calculated_predictions = predictions.tolist()
            self.env.final_predictions = final.tolist()


        self.env.vector_predictions = vector.tolist()
        self.env.action_predictions = int(action)
        self.env.action_type = actionType

        return action

    def remember(self, state, action, reward, new_state, done):
        self.memory.append([state, action, reward, new_state, done, 0])

    def replay(self):
        batch_size = 32
        if len(self.memory) < batch_size:
            return

        temp = self.memory
        acu  = np.zeros(32)

        for index in range(len(temp)-1, 0, -1):
            acu[index % 32] = temp[index][2]
            temp[index][5]  = acu.sum()

        samples = random.sample(temp, batch_size)
        for sample in samples:
            state, action, reward, new_state, done, future_reward = sample
            target = self.target_model.predict(state)
            if done:
                target[0][action] = future_reward
            else:
                Q_future = max(self.target_model.predict(new_state)[0])
                target[0][action] = future_reward # Q_future # reward + Q_future * self.gamma
            history = self.model.fit(state, target, epochs=1, verbose=0)
            # print("loss:", history.history["loss"], "\n")

    def target_train(self):
        self.env.logging.info("training target ..")
        weights = self.model.get_weights()
        target_weights = self.target_model.get_weights()
        for i in range(len(target_weights)):
            target_weights[i] = weights[i] * self.tau + target_weights[i] * (1 - self.tau)
        self.target_model.set_weights(target_weights)

    def save_model(self, fn):
        self.model.save(fn)