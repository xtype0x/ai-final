from collections import deque
import random
import numpy as np
import tensorflow as tf


class flappydqn:
  # parameters
  ACTION = 2
  FRAME_PER_ACTION = 1
  GAMMA = 0.99 # decay rate of past observations
  OBSERVE = 200 # timesteps to observe before training
  EXPLORE = 100000 # frames over which to anneal epsilon
  FINAL_EPSILON = 0.0 # final value of epsilon
  INITIAL_EPSILON = 0.97 # starting value of epsilon
  REPLAY_MEMORY = 5000 # number of previous transitions to remember
  BATCH_SIZE = 32 # size of minibatch

  def __init__(self):
    self.timeStep = 0
    self.epsilon = self.INITIAL_EPSILON
    self.replayMemory = deque()
    # create q network
    self.createQN()


  def createQN(self):
    # weights and b
    W_conv1 = self.weight_variable([8,8,4,32])
    b_conv1 = self.bias_variable([32])

    W_conv2 = self.weight_variable([4,4,32,64])
    b_conv2 = self.bias_variable([64])

    W_conv3 = self.weight_variable([3,3,64,64])
    b_conv3 = self.bias_variable([64])

    W_fc1 = self.weight_variable([5*5*64,512])
    b_fc1 = self.bias_variable([512])

    W_fc2 = self.weight_variable([512,self.ACTION])
    b_fc2 = self.bias_variable([self.ACTION])

    # input layers
    self.stateInput = tf.placeholder("float",[None,80,80,4])

    # hidden layers
    h_conv1 = tf.nn.relu(self.conv2d(self.stateInput,W_conv1,4) + b_conv1)
    h_pool1 = self.max_pool_2x2(h_conv1)

    h_conv2 = tf.nn.relu(self.conv2d(h_pool1,W_conv2,2) + b_conv2)

    h_conv3 = tf.nn.relu(self.conv2d(h_conv2,W_conv3,1) + b_conv3)

    h_conv3_flat = tf.reshape(h_conv3,[-1,5*5*64])
    h_fc1 = tf.nn.relu(tf.matmul(h_conv3_flat,W_fc1) + b_fc1)

    # Q Value layer
    self.QValue = tf.matmul(h_fc1,W_fc2) + b_fc2

    self.actionInput = tf.placeholder("float",[None,self.ACTION])
    self.yInput = tf.placeholder("float", [None]) 
    Q_action = tf.reduce_sum(tf.mul(self.QValue, self.actionInput), reduction_indices = 1)
    self.cost = tf.reduce_mean(tf.square(self.yInput - Q_action))
    self.trainStep = tf.train.AdamOptimizer(1e-6).minimize(self.cost)

    # saving and loading networks
    self.saver = tf.train.Saver()
    self.session = tf.InteractiveSession()
    self.session.run(tf.initialize_all_variables())
    checkpoint = tf.train.get_checkpoint_state("models")
    if checkpoint and checkpoint.model_checkpoint_path:
            self.saver.restore(self.session, checkpoint.model_checkpoint_path)
            print "Successfully loaded:", checkpoint.model_checkpoint_path
    else:
            print "Could not find old network weights"

  def trainQN(self):
    # Step 1: obtain random minibatch from replay memory
    minibatch = random.sample(self.replayMemory,self.BATCH_SIZE)
    state_batch = [data[0] for data in minibatch]
    action_batch = [data[1] for data in minibatch]
    reward_batch = [data[2] for data in minibatch]
    nextState_batch = [data[3] for data in minibatch]

    # Step 2: calculate y 
    y_batch = []
    QValue_batch = self.QValue.eval(feed_dict={self.stateInput:nextState_batch})
    for i in range(0,self.BATCH_SIZE):
      terminal = minibatch[i][4]
      if terminal:
        y_batch.append(reward_batch[i])
      else:
        y_batch.append(reward_batch[i] + self.GAMMA * np.max(QValue_batch[i]))

    self.trainStep.run(feed_dict={
      self.yInput : y_batch,
      self.actionInput : action_batch,
      self.stateInput : state_batch
    })

    # save network every 10000 iteration
    if self.timeStep % 1000 == 0:
      self.saver.save(self.session, 'models/' + 'network' + '-dqn', global_step = self.timeStep)

  def setPerception(self,nextObservation,action,reward,terminal):
    newState = np.append(nextObservation,self.currentState[:,:,1:],axis = 2)
    self.replayMemory.append((self.currentState,action,reward,newState,terminal))
    if len(self.replayMemory) > self.REPLAY_MEMORY:
      self.replayMemory.popleft()
    if self.timeStep > self.OBSERVE:
      # Train the network
      self.trainQN()

    self.currentState = newState
    self.timeStep += 1

  def getAction(self):
    QValue = self.QValue.eval(feed_dict= {self.stateInput:[self.currentState]})[0]
    action = np.zeros(self.ACTION)
    action_index = 0
    if self.timeStep % self.FRAME_PER_ACTION == 0:
      r = random.random()
      if r <= self.epsilon:
        action_index = random.random() > 0.97
        action[action_index] = 1
      else:
        print QValue
        action_index = np.argmax(QValue)
        action[action_index] = 1
    else:
      action[0] = 1 # do nothing

    # change episilon
    if self.timeStep % 200 == 0:
      print "epsilon:", self.epsilon
    if self.epsilon > self.FINAL_EPSILON and self.timeStep > self.OBSERVE:
      self.epsilon -= (self.INITIAL_EPSILON - self.FINAL_EPSILON)/self.EXPLORE

    return action

  def setInitState(self,observation):
    self.currentState = np.stack((observation, observation, observation, observation), axis = 2)

  def weight_variable(self,shape):
    initial = tf.truncated_normal(shape, stddev = 0.01)
    return tf.Variable(initial)

  def bias_variable(self,shape):
    initial = tf.constant(0.01, shape = shape)
    return tf.Variable(initial)

  def conv2d(self,x, W, stride):
    return tf.nn.conv2d(x, W, strides = [1, stride, stride, 1], padding = "SAME")

  def max_pool_2x2(self,x):
    return tf.nn.max_pool(x, ksize = [1, 2, 2, 1], strides = [1, 2, 2, 1], padding = "SAME")

