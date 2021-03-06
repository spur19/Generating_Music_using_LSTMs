
from __future__ import print_function
import sys
from music21 import *
import numpy as np

%tensorflow_version 1.x
!pip install keras==2.1.5
from grammar import *
from qa import *
from preprocess import * 
from music_utils import *
from data_utils import *
from keras.models import load_model, Model
from keras.layers import Dense, Activation, Dropout, Input, LSTM, Reshape, Lambda, RepeatVector
from keras.initializers import glorot_uniform
from keras.utils import to_categorical
from keras.optimizers import Adam
from keras import backend as K


X, Y, n_values, indices_values = load_music_utils()

n_a = 64 

n_values = 78 # number of music values
reshapor = Reshape((1, n_values))                    
LSTM_cell = LSTM(n_a, return_state = True)         
densor = Dense(n_values, activation='softmax')    

def djmodel(Tx, n_a, n_values):
    """
    Implement the model
    
    Arguments:
    Tx -- length of the sequence in a corpus
    n_a -- the number of activations used in our model
    n_values -- number of unique values in the music data 
    
    Returns:
    model -- a keras instance model with n_a activations
    """
    
    # Defining the input layer and specify the shape
    X = Input(shape=(Tx, n_values))
    
    # Defining the initial hidden state a0 and initial cell state c0
    # using `Input`
    a0 = Input(shape=(n_a,), name='a0')
    c0 = Input(shape=(n_a,), name='c0')
    a = a0
    c = c0
    
  
    # Creating empty list to append the outputs 
    outputs = list()
    
    
    for t in range(Tx):
        
        # Selecting the "t"th time step vector from X. 
        x = Lambda(lambda x: X[:,t,:])(X)
        # Using reshapor to reshape x to be (1, n_values) 
        x = reshapor(x)
        # Performing one step of the LSTM_cell
        a, _, c = LSTM_cell(inputs=x, initial_state=[a, c])
        # Applying densor to the hidden state output of LSTM_Cell
        out = densor(a)
        # Adding the output to "outputs"
        outputs.append(out)
        
    # Creating model instance
    model = Model(inputs=[X, a0, c0], outputs=outputs)
    
    
    return model

model = djmodel(Tx = 30 , n_a = 64, n_values = 78)

opt = Adam(lr=0.01, beta_1=0.9, beta_2=0.999, decay=0.01)

model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['accuracy'])

m = 60
a0 = np.zeros((m, n_a))
c0 = np.zeros((m, n_a))

model.fit([X, a0, c0], list(Y), epochs=100)



def music_inference_model(LSTM_cell, densor, n_values = 78, n_a = 64, Ty = 100):
    """
    Uses the trained "LSTM_cell" and "densor" from model() to generate a sequence of values.
    
    Arguments:
    LSTM_cell -- the trained "LSTM_cell" from model(), Keras layer object
    densor -- the trained "densor" from model(), Keras layer object
    n_values -- integer, number of unique values
    n_a -- number of units in the LSTM_cell
    Ty -- integer, number of time steps to generate
    
    Returns:
    inference_model -- Keras model instance
    """
    
  
    x0 = Input(shape=(1, n_values))
    
  
    a0 = Input(shape=(n_a,), name='a0')
    c0 = Input(shape=(n_a,), name='c0')
    a = a0
    c = c0
    x = x0

  
    # Creating an empty list of "outputs" to later store our predicted values
    outputs = list()
    
    # Looping over Ty and generate a value at every time step
    for t in range(Ty):
        
        # Performing one step of LSTM_cell
        a, _, c = LSTM_cell(inputs=x, initial_state=[a, c])
        
        # Applying Dense layer to the hidden state output of the LSTM_cell
        out = densor(a)

        # Appending the prediction "out" to "outputs". out.shape = (None, 78)
        outputs.append(out)
        
        x = Lambda(lambda x: one_hot(out))(x)
        
    
    inference_model = Model(inputs=[x0, a0, c0], outputs=outputs)
    
    
    return inference_model

inference_model = music_inference_model(LSTM_cell, densor, n_values = 78, n_a = 64, Ty = 50)

x_initializer = np.zeros((1, 1, 78))
a_initializer = np.zeros((1, n_a))
c_initializer = np.zeros((1, n_a))


def predict_and_sample(inference_model, x_initializer = x_initializer, a_initializer = a_initializer, 
                       c_initializer = c_initializer):
    """
    Predicts the next value of values using the inference model.
    
    Arguments:
    inference_model -- Keras model instance for inference time
    x_initializer -- numpy array of shape (1, 1, 78), one-hot vector initializing the values generation
    a_initializer -- numpy array of shape (1, n_a), initializing the hidden state of the LSTM_cell
    c_initializer -- numpy array of shape (1, n_a), initializing the cell state of the LSTM_cel
    
    Returns:
    results -- numpy-array of shape (Ty, 78), matrix of one-hot vectors representing the values generated
    indices -- numpy-array of shape (Ty, 1), matrix of indices representing the values generated
    """
    
    # Using our inference model to predict an output sequence given x_initializer, a_initializer and c_initializer.
    pred = inference_model.predict([x_initializer, a_initializer, c_initializer])
    # Converting "pred" into an np.array() of indices with the maximum probabilities
    indices = np.argmax(pred, axis=2)
    # Converting indices to one-hot vectors, the shape of the results should be (Ty, n_values)
    results = to_categorical(indices, num_classes=78)
  
    
    return results, indices


results, indices = predict_and_sample(inference_model, x_initializer, a_initializer, c_initializer)

out_stream = generate_music(inference_model)


