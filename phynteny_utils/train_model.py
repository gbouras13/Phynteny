""" 
Script to train model 

Use to parameter sweep to determine optimal batch size, epochs, dropout, memory cells

Think about using classes in this script -how to handle the features like max length etc
"""

# imports
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Bidirectional, TimeDistributed, Dense, LSTM
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import L1L2
from tensorflow import keras
from keras import optimizers

import pickle
from phynteny_utils import format_data
from sklearn.model_selection import StratifiedKFold, RandomizedSearchCV
from scikeras.wrappers import KerasClassifier
import numpy as np
from collections import ChainMap

def get_dict(dict_path): #TODO where to place this
    """
    Helper function to import dictionaries
    """

    with open(dict_path, "rb") as handle:
        dictionary = pickle.load(handle)
    handle.close()

    return dictionary

def feature_check(features_include):
    """
    Check the combination of features is possible

    :param features: string describing the list of features
    """

    if features_include not in ['all', 'strand', 'none','intergenic', 'gene_length', 'position', 'orientation_count' ]:
        raise Exception("Not an possible combination of features!\n"
                        "Must be one of: 'all', 'none', 'intergenic', 'gene_length', 'position', 'orientation_count', 'strand'")

    return features_include


class Model:

    def __init__(self,  phrog_categories_path, max_length = 120, features_include = 'all'):
        """
        :param phrog_categories_path: location of the dictionary describing the phrog_categories
        :param features: string describing a subset of features to use - one of ['all', 'strand', 'none', 'gene_start', 'intergenic', 'gene_length', 'position', 'orientation_count']
        """

        self.phrog_categories = get_dict(phrog_categories_path)
        self.features_include = feature_check(features_include)
        self.num_functions = len(set(self.phrog_categories.values())) # dimension describing the number of functions
        self.max_length = max_length

    def parse_data(self, data):
        """
        Function to take training data and process.
        Note - previous data will be removed from the model object if new data is parsed

        :param data: dictionary of training data to process
        """

        #generate dataset
        X, y, masked_cat = format_data.generate_dataset(data, self.features_include, self.num_functions, self.max_length)

        self.n_features = X.shape[1] #set this based on the size of the outputs
        self.X = X
        self.y = y #TODO these are not in init - figure out what to do
        self.masked_cat = masked_cat

    def train_crossValidation(self, k):
        """
        Perform stratified cross-validation
        :param k: number of k-folds to include. 1 is added to this to also generate a test set of equal size

        refer to this to make https://github.com/Fuhaoyi/ACEP/blob/master/ACME_codes/ACEP_model_CV.py
        """

        skf = StratifiedKFold(n_splits=self.n_features, shuffle=True, random_state=42) #Potentially this should be repeated stratifiedKFold


        #stratified KFold returns test and train set - how to distinguish the validation from the test set - do a test train split to get the test set

        #for the stratification should the masked value be what is parsed
        for train_index, val_index in skf.split(np.zeros(len(self.masked_cat)), self.masked_cat): #

            # generate stratified test and train sets
            X_train = X[train_index, :, :]
            y_train = y[train_index, :,:]

            X_val = X[val_index, :,:]
            y_val = y[val_index, :,:]


    def perform_search(self):
        """
        Perform search to identify the optimal set of parameters for the model

        parse parameters to use in a grid search

        # run this function several times to generate sufficient replication
        """

        # make model into an sklearn object
        model = KerasClassifier(model=self.create_model(), verbose = 0)

        # define the parameter search space
        batch_size = [10, 20, 30]
        param_grid = dict(batch_size=batch_size)
        search = RandomizedSearchCV(model,param_grid, n_jobs=-1)

        # run the results
        search_result = search.fit(self.X,self.y)

        # evaluate the results of the grid search
        print("Best: %f using %s" % (search_result.best_score_, search_result.best_params_))

        # save the best estimator

    def create_model(self, layers = 2, neurons = 2,  kernel_regularizer=L1L2(0,0), dropout = 0.1, activation = 'tanh', learning_rate = 0.0001):
        """
        Function for generating a LSTM model

        :param layers: number of hidden layers to use in the model
        :param neurons: number of memory cells in hidden layers
        :param kernel_regularizer: kernel regulzarizer
        :param dropout: dropout rate to implement
        :param optimizer: which optimization function to use
        :param activation: which activation function to use for the hidden layers
        :param learning_rate: learning rate for training the model
        :return: model ready to be trained
        """

        # define the model
        model = Sequential()
        
        
        #TODO does the activation function of the input layer need to be different to the hidden layers and output layer 
        # input layer 
        model.add(
                Bidirectional(
                    LSTM(
                        neurons, return_sequences = True, dropout = dropout, kernel_regularizer = kernel_regularizer, activation=activation), input_shape=(self.max_length, self.n_features)
                    )
                )
        

        # loop which controls the number of hidden layers
        for layer in range(layers):

            model.add(
                Bidirectional(
                    LSTM(
                        neurons, return_sequences = True, dropout = dropout, kernel_regularizer = kernel_regularizer, activation=activation)
                    ),
                )  

        # output layer
        model.add(TimeDistributed(Dense(self.num_functions, activation="softmax")))

        # optimizer
        #optimization_function = keras.optimizers.RMSprop(learning_rate=0.01)
        #print(optimization_function)
        #compile the model #in this compilation add the optimization function
        model.compile(
            loss="categorical_crossentropy", metrics=["accuracy"]
        )

        return model

    def train_LSTM(self, X, y, memory_cells = 100, batch_size = 128,  dropout = 0.1, recurrent_dropout = 0, learning_rate = 0.0001,  activation = 'tanh',  validation_dropout = 0, patience = 5, min_delta = 0.0001 ): #TODO - include activation function
        """
        Training procedure here

        :param X: X for training
        :param y: y for training
        :param memory_cells: number of memory cells in each hidden layer
        :param batch_size: batch size during training
        :param dropout: dropout of each hidden layer
        :param recurrent_dropout: recurrent dropout for each layer
        :param learning_rate: learning rate
        :param  activation: string describing activation function
        :param validation_dropout: validation dropout
        :param epochs: number of epochs to train the model for
        :param patience: number of epochs below min delta to cease training
        :param min_delta: minimum loss before giving up on training
        """
        #TODO how to control the different features here
        #TODO determine at what stage to parse all the different features

        #TODO when creating the model introduce a random seed for reproducibility

        model = Sequential()
        model.add(
            Bidirectional(
                LSTM(
                    memory_cells,
                    return_sequences=True,
                    dropout=dropout,
                    kernel_regularizer=L1L2(0, 0),
                ),
                input_shape=(max_length, n_features),
            )
        )
        model.add(
            Bidirectional(
                LSTM(
                    memory_cells,
                    return_sequences=True,
                    dropout=dropout,
                    kernel_regularizer=L1L2(0, 0),
                )
            )
        )
        model.add(
            Bidirectional(
                LSTM(
                    memory_cells,
                    return_sequences=True,
                    dropout=dropout,
                    kernel_regularizer=L1L2(0, 0),
                )
            )
        )
        model.add(TimeDistributed(Dense(num_functions, activation="softmax"))) #this is the output layer

        optimizer = Adam(learning_rate=lr)
        model.compile(
            loss="categorical_crossentropy", optimizer=optimizer, metrics=["accuracy"]
        )
        print(model.summary(), flush=True)

        es = EarlyStopping(
            monitor="loss", mode="min", verbose=2, patience=patience, min_delta=min_delta
        )  # use a set number of epoch when adjusting the memory cells and batch size
        mc = ModelCheckpoint(
            model_file_out[:-3] + "best_val_accuracy.h5",
            monitor="val_loss",
            mode="min",
            save_best_only=True,
            verbose=1,
            save_freq="epoch",
        )  # model with the best validation loss therefore minimise
        mc2 = ModelCheckpoint(
            model_file_out[:-3] + "best_val_loss.h5",
            monitor="val_accuracy",
            mode="max",
            save_best_only=True,
            verbose=1,
            save_freq="epoch",
        )  # model with the best validation set accuracy therefore maximise

        history = model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[es, mc, mc2],
            validation_data=(X_test, y_test),
        )

        # save the model
        model.save(model_file_out)

        # save the history dictionary as a pickle
        with open(history_file_out, "wb") as handle:
            pickle.dump(history.history, handle, protocol=pickle.HIGHEST_PROTOCOL)


def select_features(data, features):
    """
    Select a subset of features from a set of features

    :param data: total set of all features to consider
    :param features: string defining whether to include 'all' feautres, 'strand features' or no features
    :return: list of features
    """

    if features == "all":
        return data
    elif features == "strand":
        return [data[i][:2] for i in range(len(data))]
    else:
        return [[] for i in range(len(data))]


def PermaDropout(rate):
    """
    Function to apply dropout to the validation data as well as the training data. Useful for demonstrating why the validation loss is less than the training loss

    :param rate: Dropout rate
    :return: dropout layer applied to training data and validation data
    """

    return Lambda(lambda x: K.dropout(x, level=rate))


def train_kfold(
    base,
    phrog_encoding,
    k,
    num_functions,
    n_features,
    max_length,
    file_out,
    memory_cells,
    batch_size,
    epochs,
    dropout,
    recurrent,
    lr,
    patience,
    min_delta,
    features,
    model="LSTM",
    permadropout=False,
):
    """
    Separate training data into

    :param train_type: Whether to include dropout on validation data
    :param k: Number of folds to train over
    :param base: base string of location of the data chunks
    :param phrog_encoding: dictionary mapping proteins to phrog categories
    :param num functions: number of possible functions inlcuded in data
    :param n_features: number of possible features included in data
    :param max_length: maximum number of genes included in a single prophage
    :param file_out: destination to save model outputs
    :param memory cells: Number of memory cells to use for each LSTM layer
    :param batch_size: Batch size for training
    :param epochs: Number of epochs to use for training
    :param patience: Stopping condition - how many epochs without loss increasing to stop training
    :param min_delta: Stopping condition loss value
    :param model: Type of model to train - either LSTM or ANN
    :param permadropout: If true applies dropout to validation data
    """

    # REMOVE
    print("NUMBER OF FEATURES PARSED:" + str(n_features), flush=True)

    # loop through the training chunks
    kk = np.array(range(k))
    for i in range(k - 2, k):
        chunks = [base + str(f) + "_chunk.pkl" for f in kk[kk != i]]
        print("reading chunks", flush=True)
        training_chunks = [pickle.load(open(f, "rb")) for f in chunks]

        print("merging chunks", flush=True)
        train_data = ChainMap(*training_chunks)

        # generate the training data
        print("generating training features", flush=True)
        print("features used: " + features, flush=True)
        train_encodings, train_features = format_data.format_data(
            train_data, phrog_encoding
        )

        print("before select there are : " + str(len(train_features[0])))
        train_features = select_features(train_features, features)
        print("after select there are : " + str(len(train_features[0])))

        print("creating training dataset", flush=True)
        X_train, y_train, masked_idx = format_data.generate_dataset(
            train_encodings, train_features, num_functions, n_features, max_length
        )
        print("training X size: " + str(X_train.shape), flush=True)
        print("training y size: " + str(y_train.shape), flush=True)

        # generate the test data
        test_data = pickle.load(open(base + str(i) + "_chunk.pkl", "rb"))
        print("generating test features", flush=True)
        test_encodings, test_features = format_data.format_data(
            test_data, phrog_encoding
        )
        test_features = select_features(test_features, features)
        print("creating test dataset", flush=True)

        X_test, y_test, masked_idx = format_data.generate_dataset(
            test_encodings, test_features, num_functions, n_features, max_length
        )
        print("test size: " + str(y_test.shape), flush=True)

        # file names of the data
        model_file_out = file_out + str(i) + "_" + features + "_chunk_trained_LSTM.h5"
        history_file_out = file_out + str(i) + "_" + features + "_chunk_history.pkl"

        print("Training for chunk: " + str(i), flush=True)

        # train model
        if permadropout == False:
            print("Not including dropout on validation", flush=True)

            if model == "LSTM":
                train_LSTM(
                    X_train,
                    y_train,
                    X_test,
                    y_test,
                    max_length,
                    n_features,
                    num_functions,
                    model_file_out,
                    history_file_out,
                    memory_cells,
                    batch_size,
                    epochs,
                    dropout,
                    recurrent,
                    lr,
                    patience,
                    min_delta,
                )

            if model == "ANN":
                train_ANN(
                    X_train,
                    y_train,
                    X_test,
                    y_test,
                    max_length,
                    n_features,
                    num_functions,
                    model_file_out,
                    history_file_out,
                    memory_cells,
                    batch_size,
                    epochs,
                    dropout,
                    recurrent,
                    lr,
                    patience,
                    min_delta,
                )

                print("Training with ANN", flush=True)

        elif permadropout == True:
            print("Including dropout on validation", flush=True)

            train_LSTM_permadropout(
                X_train,
                y_train,
                X_test,
                y_test,
                max_length,
                n_features,
                num_functions,
                model_file_out,
                history_file_out,
                memory_cells,
                batch_size,
                epochs,
                dropout,
                recurrent,
                lr,
                patience,
                min_delta,
            )

        del X_train
        del y_train
        del train_encodings
        del train_features

        del X_test
        del y_test
        del test_encodings
        del test_features

def train_LSTM(
    X_train,
    y_train,
    X_test,
    y_test,
    max_length,
    n_features,
    num_functions,
    model_file_out,
    history_file_out,
    memory_cells,
    batch_size,
    epochs,
    dropout,
    recurrent,
    lr,
    patience,
    min_delta,
):
    """
    Train and save LSTM and training history

    :param X_train: Supervised learning problem features
    :param y_train: Supervised learning problem labels
    :param model_file_out: File name of saved model
    :param history_file_out: File name of history dictionary
    :param memory cells: Number of memory cells to use for each LSTM layer
    :param batch_size: Batch size for training
    :param epochs: Number of epochs to use for training
    :param patience: Stopping condition - how many epochs without loss increasing to stop training
    :param min_delta: Stopping condition loss value
    """

    model = Sequential()
    model.add(
        Bidirectional(
            LSTM(
                memory_cells,
                return_sequences=True,
                dropout=dropout,
                kernel_regularizer=L1L2(0, 0),
            ),
            input_shape=(max_length, n_features),
        )
    )
    model.add(
        Bidirectional(
            LSTM(
                memory_cells,
                return_sequences=True,
                dropout=dropout,
                kernel_regularizer=L1L2(0, 0),
            )
        )
    )
    model.add(
        Bidirectional(
            LSTM(
                memory_cells,
                return_sequences=True,
                dropout=dropout,
                kernel_regularizer=L1L2(0, 0),
            )
        )
    )
    model.add(TimeDistributed(Dense(num_functions, activation="softmax")))

    optimizer = Adam(learning_rate=lr)
    model.compile(
        loss="categorical_crossentropy", optimizer=optimizer, metrics=["accuracy"]
    )
    print(model.summary(), flush=True)

    es = EarlyStopping(
        monitor="loss", mode="min", verbose=2, patience=patience, min_delta=min_delta
    )  # use a set number of epoch when adjusting the memory cells and batch size
    mc = ModelCheckpoint(
        model_file_out[:-3] + "best_val_accuracy.h5",
        monitor="val_loss",
        mode="min",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation loss therefore minimise
    mc2 = ModelCheckpoint(
        model_file_out[:-3] + "best_val_loss.h5",
        monitor="val_accuracy",
        mode="max",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation set accuracy therefore maximise

    history = model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[es, mc, mc2],
        validation_data=(X_test, y_test),
    )

    # save the model
    model.save(model_file_out)

    # save the history dictionary as a pickle
    with open(history_file_out, "wb") as handle:
        pickle.dump(history.history, handle, protocol=pickle.HIGHEST_PROTOCOL)


def train_LSTM_permadropout(
    X_train,
    y_train,
    X_test,
    y_test,
    max_length,
    n_features,
    num_functions,
    model_file_out,
    history_file_out,
    memory_cells,
    batch_size,
    epochs,
    dropout,
    recurrent,
    lr,
    patience,
    min_delta,
):
    """
    Train LSTM with permadropout.
    Keras does not apply dropout to validation data. Use this function to explain gap between training loss and validation loss.

    :param X_train: Supervised learning problem features
    :param y_train: Supervised learning problem labels
    :param model_file_out: File name of saved model
    :param history_file_out: File name of history dictionary
    :param memory cells: Number of memory cells to use for each LSTM layer
    :param batch_size: Batch size for training
    :param epochs: Number of epochs to use for training
    :param patience: Stopping condition - how many epochs without loss increasing to stop training
    :param min_delta: Stopping condition loss value
    """

    model = Sequential()
    model.add(
        Bidirectional(
            LSTM(memory_cells, return_sequences=True, kernel_regularizer=L1L2(0, 0)),
            input_shape=(max_length, n_features),
        )
    )
    model.add(PermaDropout(dropout))
    model.add(
        Bidirectional(
            LSTM(memory_cells, return_sequences=True, kernel_regularizer=L1L2(0, 0))
        )
    )
    model.add(PermaDropout(dropout))
    model.add(
        Bidirectional(
            LSTM(memory_cells, return_sequences=True, kernel_regularizer=L1L2(0, 0))
        )
    )
    model.add(PermaDropout(dropout))
    model.add(TimeDistributed(Dense(num_functions, activation="softmax")))

    optimizer = Adam(learning_rate=lr)
    model.compile(
        loss="categorical_crossentropy", optimizer=optimizer, metrics=["accuracy"]
    )
    print(model.summary(), flush=True)

    es = EarlyStopping(
        monitor="loss", mode="min", verbose=2, patience=patience, min_delta=min_delta
    )  # use a set number of epoch when adjusting the memory cells and batch size
    mc = ModelCheckpoint(
        model_file_out[:-3] + "best_val_accuracy.h5",
        monitor="val_loss",
        mode="min",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation loss therefore minimise
    mc2 = ModelCheckpoint(
        model_file_out[:-3] + "best_val_loss.h5",
        monitor="val_accuracy",
        mode="max",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation set accuracy therefore maximise

    history = model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[es, mc, mc2],
        validation_data=(X_test, y_test),
    )

    # save the model
    model.save(model_file_out)

    # save the history dictionary as a pickle
    with open(history_file_out, "wb") as handle:
        pickle.dump(history.history, handle, protocol=pickle.HIGHEST_PROTOCOL)


def train_ANN(
    X_train,
    y_train,
    X_test,
    y_test,
    max_length,
    n_features,
    num_functions,
    model_file_out,
    history_file_out,
    memory_cells,
    batch_size,
    epochs,
    dropout,
    recurrent,
    lr,
    patience,
    min_delta,
):
    """
    Train Artificial Neural Network to compare with LSTM

    :param X_train: Supervised learning problem features
    :param y_train: Supervised learning problem labels
    :param model_file_out: File name of saved model
    :param history_file_out: File name of history dictionary
    :param memory cells: Number of memory cells to use for each LSTM layer
    :param batch_size: Batch size for training
    :param epochs: Number of epochs to use for training
    :param patience: Stopping condition - how many epochs without loss increasing to stop training
    :param min_delta: Stopping condition loss value
    """

    model = Sequential()
    model.add(Dense(memory_cells, input_shape=(max_length, n_features)))
    model.add(Dropout(dropout))
    model.add(Dense(memory_cells))
    model.add(Dropout(dropout))
    model.add(Dense(memory_cells))
    model.add(Dropout(dropout))
    model.add(Dense(num_functions, activation="softmax"))  # output layer
    optimizer = Adam(learning_rate=lr)
    model.compile(
        loss="categorical_crossentropy", optimizer=optimizer, metrics=["accuracy"]
    )

    es = EarlyStopping(
        monitor="loss", mode="min", verbose=2, patience=patience, min_delta=min_delta
    )  # use a set number of epoch when adjusting the memory cells and batch size
    mc = ModelCheckpoint(
        model_file_out[:-3] + "best_val_accuracy.h5",
        monitor="val_loss",
        mode="min",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation loss therefore minimise
    mc2 = ModelCheckpoint(
        model_file_out[:-3] + "best_val_loss.h5",
        monitor="val_accuracy",
        mode="max",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation set accuracy therefore maximise

    history = model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[es, mc, mc2],
        validation_data=(X_test, y_test),
    )


def train_ANN_permadropout(
    X_train,
    y_train,
    X_test,
    y_test,
    max_length,
    n_features,
    num_functions,
    model_file_out,
    history_file_out,
    memory_cells,
    batch_size,
    epochs,
    dropout,
    recurrent,
    lr,
    patience,
    min_delta,
):
    """
    Train LSTM with permadropout.
    Keras does not apply dropout to validation data. Use this function to explain gap between training loss and validation loss.

    :param X_train: Supervised learning problem features
    :param y_train: Supervised learning problem labels
    :param model_file_out: File name of saved model
    :param history_file_out: File name of history dictionary
    :param memory cells: Number of memory cells to use for each LSTM layer
    :param batch_size: Batch size for training
    :param epochs: Number of epochs to use for training
    :param patience: Stopping condition - how many epochs without loss increasing to stop training
    :param min_delta: Stopping condition loss value
    """

    model = Sequential()

    model.add(Dense(memory_cells, input_shape=(max_length, n_features)))
    model.add(PermaDropout(dropout))
    model.add(Dense(memory_cells))
    model.add(PermaDropout(dropout))
    model.add(Dense(memory_cells))
    model.add(PermaDropout(dropout))
    model.add(Dense(num_functions, activation="softmax"))  # output layer
    optimizer = Adam(learning_rate=lr)
    model.compile(
        loss="categorical_crossentropy", optimizer=optimizer, metrics=["accuracy"]
    )

    es = EarlyStopping(
        monitor="loss", mode="min", verbose=2, patience=patience, min_delta=min_delta
    )  # use a set number of epoch when adjusting the memory cells and batch size
    mc = ModelCheckpoint(
        model_file_out[:-3] + "best_val_accuracy.h5",
        monitor="val_loss",
        mode="min",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation loss therefore minimise
    mc2 = ModelCheckpoint(
        model_file_out[:-3] + "best_val_loss.h5",
        monitor="val_accuracy",
        mode="max",
        save_best_only=True,
        verbose=1,
        save_freq="epoch",
    )  # model with the best validation set accuracy therefore maximise

    history = model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[es, mc, mc2],
        validation_data=(X_test, y_test),
    )
