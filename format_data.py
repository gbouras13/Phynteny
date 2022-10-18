""" 
Functions to prepare data for training with the LSTM viral gene organisation model
""" 

#imports 
import numpy as np 
import random 
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle 
import glob 

def generate_data(data): 
    """
    
    :param data: directory containing dictionaries of phispy genomes
    :return dictionary 
    """
    
    #get the directorys containing the genomes 
    levelone = glob.glob(data)

    #counters to campare the sizes of the training datasets
    included = 0
    not_included = 0

    #dictionary to store the filtered data 
    data = {}

    #loop through each genome 
    for l1 in levelone:
        leveltwo = glob.glob(l1+'/*')

        for l2 in leveltwo:

            files = glob.glob(l2+'/*')

            for file in files: 
                with open(file, 'rb') as handle:
                    genomes = pickle.load(handle)

                for g in list(genomes.keys()):
                    this_genome = genomes.get(g)
                    categories = [phrog_encoding.get(i) for i in this_genome.get('phrogs')]

                    categories_present = set(categories)
                    if 0 in categories_present:
                        categories_present.remove(0)

                    #Take genomes which contain at least four different phrog categories 
                    if len(categories_present) >= 4:

                        #only consider genomes which contain a gene belonging to 'integration and excision' at either the start or end of the genome
                        if categories[0] == 1 or categories[-1] == 1: #look into whether to include this 
                            included += 1
                            data[g] = this_genome

                        else:
                            not_included += 1

    print('Number of genomes after filtering: ' + str(included) + ' sequences')
    print('Number of genomes removed during filtering: ' + str(not_included) + ' sequences')

    #dereplicate the filtered data such that genome has unique gene organisation and orientation 
    data_derep = derep_trainingdata(data, phrog_encoding) 
    
    return data_derep 

def test_train_data(data, test_portion): 
    """
    Separate data in testing and training data 
    
    :param data: directory containing dictionaries of phispy genomes
    :param test_portion: portion as a decimal of the data reserved as test data 
    :return dictionary of training data 
    :return dictionary of testing data 
    """
    
    #obtain data 
    genome_data = generate_data(data) 
    keys = list(genome_data.keys()) 
    
    #shuffle 
    random.shuffle(keys) 
    
    #separate into training and testing data 
    test_num = int(len(keys) * test_num)
    test_keys = keys[:test_num] 
    train_keys = keys[test_num:] 
 
    #get dictionaries 
    train_data = dict(zip(train_keys, [data.get(key) for key in train_keys])) 
    test_data = dict(zip(test_keys, [data.get(key) for key in test_keys]))

    return train_data, test_data

def encode_strand(strand): 
    """ 
    One hot encode sense
    
    :param strand: sense encoded as a vector of 1s and 2s 
    :return: one hot encoding as two separate numpy arrays
    """ 
    
    return np.array([1 if i==1 else 0 for i in strand]), np.array([1 if i==2 else 0 for i in strand])

def derep_trainingdata(training_data, phrog_encoding): 
    """ 
    Ensure there is only one copy of each phrog order and sense order 
    
    :param training_data: dictionary containing training data 
    :param phrog_encoding: dictionary which converts phrogs to category integer encoding 
    :return: dereplicated training dictionary 
    """
    
    
    #get the training keys and encodings 
    training_keys = list(training_data.keys()) 
    training_encodings = [[phrog_encoding.get(i) for i in training_data.get(key).get('phrogs')] for key in training_keys] 
    
    #write a function to remove duplicates in the training data 
    training_str = [''.join([str(j) for j in i]) for i in training_encodings]
    training_sense = [''.join(training_data.get(p).get('sense')) for p in training_keys]
    training_hash = [training_sense[i] + training_str[i] for i in range(len(training_keys))]

    #get the dereplicated keys 
    dedup_keys = list(dict(zip(training_hash, training_keys)).values())

    return dict(zip(dedup_keys, [training_data.get(d) for d in dedup_keys]))


def flip_genomes(training_data, phrog_encoding): 
    """ 
    If an integrase has an integrase at the end of a sequence flip so that it is at the start of the sequence 
    
    :param training_data: dictionary which contains details for each genome 
    :param phrog_encoding: dictionary nwhich converts phrogs to category integer encoding 
    :return: dictionary containing genomes which are flipped if needed 
    """ 
    
    data = dict() 
    
    training_keys = list(training_data.keys()) 

    for key in training_keys: 
        
        genome = training_data.get(key) 
        encoding = [phrog_encoding.get(i) for i in genome.get('phrogs')]
        
        if encoding[-1] == 1: 
            
            #adjust the positions for the reverse order 
            length = genome.get('length')
            positions = [(np.abs(i[1] - length), np.abs(i[0] - length)) for i in genome.get('position')[::-1]]
            
            sense = ['-' if i == '+' else '+' for i in genome.get('sense')[::-1]]
            
            #add to the dictionary 
            data[key] = {'length': genome.get('length'), 
                         'phrogs': genome.get('phrogs')[::-1], 
                         'protein_id': genome.get('protein_id')[::-1], 
                         'sense': sense, 
                         'position': positions}
        else: 
           
            data[key] = genome 
        
    return data

def format_data(training_data, phrog_encoding): 
    """ 
    Intial function to generate training data.
    Currently only includes genomes which start or end with an integrase. This is hard coded and will likely need changing. 
    
    :param training_data: dictionary which contains details for each genome 
    :param phrog_encoding: dictionary which converts phrogs to cateogory integer encoding 
    :return: training encodings one-hot encoding each genome 
    :return: list of features 
    """
    
    training_encodings = []
    sense_encodings = []
    start_encodings = []
    length_encodings = []
    intergenic_encodings = [] 

    training_keys = list(training_data.keys()) 

    for key in training_keys: 

        encoding = [phrog_encoding.get(i) for i in training_data.get(key).get('phrogs')]
        length = np.array([i[1] - i[0] for i in training_data.get(key).get('position')])

        #encode the strand 
        sense = np.array([2 if i == '+' else 1 for i in training_data.get(key).get('sense')])

        #start position of each gene 
        start = np.array([i[0] - training_data.get(key).get('position')[0][0] + 1 for i in training_data.get(key).get('position')])

        #intergenic distances 
        intergenic = [training_data.get(key).get('position')[i+1][0] -  training_data.get(key).get('position')[i][1]  for i in range(len(training_data.get(key).get('position'))-1)]  
        intergenic.insert(0, 0)
            
        #update the features 
        training_encodings.append(encoding) 
        sense_encodings.append(sense) 
        start_encodings.append(start) 
        intergenic_encodings.append(intergenic) 
        length_encodings.append(length)

    #scale the lengths such that the maximum length is 1 
    max_length = np.max([np.max(l) for l in length_encodings])
    length_encodings = [l/max_length for l in length_encodings]

    #divide intergenic distance by the absolute maximum 
    max_intergenic = np.max([np.max(np.abs(i)) for i in intergenic_encodings]) 
    intergenic_encodings = [i/max_intergenic for i in intergenic_encodings]

    #scale the start positions according to the length of the genome 
    start_encodings = [s/np.max(s) for s in start_encodings] #simply divide starts by the length of the sequence 

    #split the sense into two separate features as it is categorical data 
    sense_encodings = [encode_strand(s) for s in sense_encodings]
    strand1s = [s[0] for s in sense_encodings]
    strand2s = [s[1] for s in sense_encodings] 

    #return a set of features to train the LSTM 
    features = [strand1s, strand2s, length_encodings, start_encodings, intergenic_encodings] 
    features = [[f[j] for f in features] for j in range(len(training_encodings))]

    return training_encodings, features 

def format_data_flipped(training_data, phrog_encoding): 
    """ 
    Intial function to generate training data. Flips sequences with an integrase at one end so that the integrase is at the start of the sequence. 
    Currently only includes genomes which start or end with an integrase. This is hard coded and will likely need changing. 
    
    :param training_data: dictionary which contains details for each genome 
    :param phrog_encoding: dictionary which converts phrogs to cateogory integer encoding 
    :return: training encodings one-hot encoding each genome 
    :return: list of features 
    """
    
    training_encodings = []
    sense_encodings = []
    start_encodings = []
    length_encodings = []
    intergenic_encodings = [] 

    training_keys = list(training_data.keys()) 

    for key in training_keys: 

        encoding = [phrog_encoding.get(i) for i in training_data.get(key).get('phrogs')]
        length = np.array([i[1] - i[0] for i in training_data.get(key).get('position')])

        #if the integrase is at the end then reverse the sequence 
        if encoding[-1] == 1: 

            #flip the order and gene lengths 
            encoding = encoding[::-1]
            length = length[::-1] 

            #encode the strand  
            sense = np.array([1 if i == '+' else 2 for i in training_data.get(key).get('sense')])
            sense = sense[::-1]

            #get the start positions 
            start = np.array([training_data.get(key).get('length') - i[1] + 1for i in training_data.get(key).get('position')])
            start = start[::-1]

            #intergenic distances 
            intergenic = [training_data.get(key).get('position')[i+1][0] - training_data.get(key).get('position')[i][1]  for i in range(len(training_data.get(key).get('position')[::-1]) -1 )]
            intergenic.insert(0,0) 
        
        else: 
        
            #encode the strand 
            sense = np.array([2 if i == '+' else 1 for i in training_data.get(key).get('sense')])

            #start position of each gene 
            start = np.array([i[0] - training_data.get(key).get('position')[0][0] + 1 for i in training_data.get(key).get('position')])

            #intergenic distances 
            intergenic = [training_data.get(key).get('position')[i+1][0] -  training_data.get(key).get('position')[i][1]  for i in range(len(training_data.get(key).get('position'))-1)]  
            intergenic.insert(0, 0)
            

        #update the features 
        training_encodings.append(encoding) 
        sense_encodings.append(sense) 
        start_encodings.append(start) 
        intergenic_encodings.append(intergenic) 
        length_encodings.append(length)

    #scale the lengths such that the maximum length is 1 
    max_length = np.max([np.max(l) for l in length_encodings])
    length_encodings = [l/max_length for l in length_encodings]

    #divide intergenic distance by the absolute maximum 
    max_intergenic = np.max([np.max(np.abs(i)) for i in intergenic_encodings]) 
    intergenic_encodings = [i/max_intergenic for i in intergenic_encodings]

    #scale the start positions according to the length of the genome 
    start_encodings = [s/np.max(s) for s in start_encodings] #simply divide starts by the length of the sequence 

    #split the sense into two separate features as it is categorical data 
    sense_encodings = [encode_strand(s) for s in sense_encodings]
    strand1s = [s[0] for s in sense_encodings]
    strand2s = [s[1] for s in sense_encodings] 

    #return a set of features to train the LSTM 
    features = [strand1s, strand2s, length_encodings, start_encodings, intergenic_encodings] 
    features = [[f[j] for f in features] for j in range(len(training_encodings))]

    return training_encodings, features 


def one_hot_encode(sequence, n_features):
    """ 
    One hot encode PHROG categories as data is cateogrical. 
    
    :param sequence: numerical sequence of PHROG cateogories 
    :param n_features: total number of features in the model
    :return: numpy array containing one hot encoding 
    """ 
    
    encoding = list()
    for value in sequence:
        vector = [0 for _ in range(n_features)]
        vector[value] = 1
        encoding.append(vector)
        
    return np.array(encoding)
    
def encode_feature(encoding, feature, column): 
    """ 
    Add a feature to sequence feature matrix 
    
    :param encoding: matrix including features for some seuqnece
    :param feature: feature to append to matrix 
    :param column: column to add feature 
    :return: feature matrix including the new feature  
    """ 

    encoding = encoding.astype('float64')
    encoding[:len(feature), column] = feature

    return encoding 

def one_hot_decode(encoded_seq):
    """ 
    Return one-hot encoding of PHROG category to its original numeral value 
    
    :param encoded_seq: one_hot encoding of the sequence 
    :return: integer encoding of the PHROG cateogries present in a sequence 
    """ 
    return [np.argmax(vector) for vector in encoded_seq]

def shuffle_dict(dictionary): 
    """ 
    Shuffles a dictionary into random order. Use to generate randomised training datasets 
    
    :param dictionary: dictionary object to be shuffle 
    :return shuffled dictionary 
    """
    
    keys = dictionary.keys()
    random.shuffle(keys) 
    
    return dict(zip(keys, [dictionary.get(key) for key in keys]))

def generate_example(sequence, features, num_functions, n_features, max_length, idx): 
    """ 
    Convert a sequence of PHROG functions and associated features to a supervised learning problem 
    
    :param sequence: integer encoded list of PHROG categories in a sequence
    :param features: list of features to include in problem 
    :param num_functions: number of possible PHROG categories  
    :param max_length: maximum length of a sequence 
    :return: training or test example separated as X and y matrices 
    """

    seq_len = len(sequence) 
    padded_sequence = pad_sequences([sequence], padding = 'post', maxlen = max_length)[0]
    y = np.array(one_hot_encode(padded_sequence, num_functions))
    X =  np.array(one_hot_encode(padded_sequence, n_features ))

    for f in range(len(features)): #maybe this line has to change 
        X = encode_feature(X, features[f], num_functions + f) 

    #replace the function encoding for the masked sequence 
    X[idx, 0:num_functions] = np.zeros(num_functions) 
        
    #reshape the matrices 
    X = X.reshape((1, max_length, n_features))
    y = y.reshape((1, max_length, num_functions))
    
    return X, y
    
def generate_prediction(sequence, features, num_functions, n_features, max_length): 
    """ 
    Prepare data to predict the function of all hypothetical genes in a sequence 
    
    :param sequence: inteer enoded list of PHROG categories in a sequence 
    :param features: list of features to include 
    :param num_functions: number of possible PHROG categories 
    :param max_length: maximum length of a sequence 
    :return: encoded matrix which can be parsed to the model
    """ 
    
    #construct features 
    seq_len = len(sequence) 
    padded_sequence = pad_sequences([sequence], padding = 'post', maxlen = max_length)[0]
    
    X =  np.array(one_hot_encode(padded_sequence, n_features ))
    for f in range(len(features)): 
        X = encode_feature(X, features[f], num_functions + f)

    #mask each unknown in the sequence  
    unknown_idx = [i for i, x in enumerate(sequence) if x == 0]
    for unk in unknown_idx: 
        X[unk, 0:num_functions] = np.zeros(num_functions) 
 
    return X.reshape((1, max_length, n_features)) 

def generate_dataset_unbiased_category(sequences, all_features, num_functions, n_features, max_length): 
    """" 
    Generate a dataset to train LSTM model 
    
    :param sequences: set of sequences encoded as integers for each PHROG
    :param dataset_size: number of sequences in the dataset  
    :param all_features:  set of features to include in the encodings 
    :param num_functions: number of possible PHROG categories 
    :param n_features: total number of features 
    :param max_length: maximum length of a sequence 
    :return: Dataset of training or test data reprsented as X and y matrices 
    :return: list of which sequences are included and which are not included 
    :return: list stating which function is masked for each genome in the dataset 
    """
    
    #features is a list of list objects 
    X = [] 
    y = [] 
    masked_func = [] 
    genome_included = [] 

    #generate the function to mask in this genome 
    func = random.randint(1, num_functions-1)
        
    for i in range(len(sequences)): 
        
        if func in sequences[i]:
     
            occurence = [i for i, x in enumerate(sequences[i]) if x == func]
            idx = random.choice(occurence) 
   
            this_X, this_y = generate_example(sequences[i], all_features[i], num_functions, n_features, max_length, idx)  
           
            X.append(this_X) 
            y.append(this_y)
            masked_func.append(func) 
            
            #generate a new function for the next training example 
            func = random.randint(1, num_functions-1)
            
            #update inclusion list 
            genome_included.append(1)
            
        else: 
            genome_included.append(0) 
            
    X = np.array(X).reshape(len(masked_func),max_length,n_features)
    y = np.array(y).reshape(len(masked_func), max_length, num_functions)
    
    return X, y, genome_included, masked_func

def generate_dataset(sequences, all_features, num_functions, n_features, max_length): 
    """" 
    Generate a dataset to train LSTM model 
    
    :param sequences: set of sequences encoded as integers for each PHROG
    :param dataset_size: number of sequences in the dataset  
    :param all_features:  set of features to include in the encodings 
    :param num_functions: number of possible PHROG categories 
    :param n_features: total number of features 
    :param max_length: maximum length of a sequence 
    :return: Dataset of training or test data reprsented as X and y matrices 
    """
    
    #features is a list of list objects 
    X = [] 
    y = [] 
    masked_func = [] 
        
    for i in range(len(sequences)): 
        
        #take a function to mask 
        idx = random.randint(1, len(sequences[i]) -1) #don't include ends
        
        #make sure that the mask is not an uknown category 
        while sequences[i][idx] == 0: 
            idx = random.randint(1, len(sequences[i]) -1)
        
        this_X, this_y = generate_example(sequences[i], all_features[i], num_functions, n_features, max_length, idx) 
        
        #store the functon which was masked 
        X.append(this_X) 
        y.append(this_y)
        masked_func.append(sequences[i][idx]) 

    X = np.array(X).reshape(len(masked_func),max_length,n_features)
    y = np.array(y).reshape(len(masked_func), max_length, num_functions)
    
    return X, y, masked_func