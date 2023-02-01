"""
Generate training data for the model
""" 

#imports
import pickle
import argparse
import re
import handle_genbank


def check_positive(arg):
    """ Type function for argparse - a float within some predefined bounds """

    value = int(arg)
    if value <= 0:
        raise argparse.ArgumentTypeError("Negative input value 0" )
    return value

#argparser
parser = argparse.ArgumentParser(description='Generate training data for retraining the Phynteny model')
parser.add_argument('-i', '--input', help = 'Text file containing genbank files to build model', required=True)
parser.add_argument('-o', '--output', help='Name of output dictionary containing training data', required=True)
parser.add_argument('-max_genes', '--maximum_genes', type=check_positive, help='Specify the maximum number of genes in each genome', required=False, default=120)
parser.add_argument('-gene_cat', '--gene_categories', type=check_positive, help='Specify the minimum number of cateogries in each genome', required=False, default=4)
parser.add_argument('-c', '--chunks', type=check_positive, help='Number of chunks to divide data', required=False, default=0)
args = vars(parser.parse_args())

#read in annotations
with open('/home/grig0076/GitHubs/Phynteny/phrog_annotation_info/phrog_integer.pkl', 'rb') as handle:
    phrog_integer = pickle.load(handle) 
    phrog_integer = dict(zip([str(i) for i in list(phrog_integer.keys())], phrog_integer.values()))
handle.close()

training_data = {} #dictionary to store all of the training data

#takes a text file where each line is the file path to genbank files of phages to train a model
print('Extracting...', flush = True)
print(args['input'], flush = True) 
with open(args['input'], 'r') as file:
    
    genbank_files = file.readlines()
    #print(genbank_files) 
    for genbank in genbank_files:
        print(genbank) 
        #convert genbank to a dictionary
        gb_dict = handle_genbank.get_genbank(genbank)
        gb_keys = list(gb_dict.keys())

        for key in gb_keys:

                #extract the relevant features
                phage_dict = handle_genbank.extract_features(gb_dict.get(key))
                 
                #integer encoding of phrog categories 
                integer = handle_genbank.phrog_to_integer(phage_dict.get('phrogs'), phrog_integer)
                phage_dict['categories'] = integer

                #evaluate the number of categories present in the phage
                categories_present = set(integer)
                if 0 in categories_present:
                    categories_present.remove(0)

                #if above the minimum number of categories are included 
                if len(phage_dict.get('phrogs')) <= args['maximum_genes'] and len(categories_present) >= args['gene_categories']:

                    # update dictionary with this one
                    g = re.split(',|\.', re.split('/', genbank.strip())[-1])[0]
                    training_data[g + '_' + key] = phage_dict

#save the training data dictionary
print('Done Processing!')
print('Removing duplicate phrog category orders')

derep_data = handle_genbank.derep_trainingdata(training_data)
data_derep_shuffle = handle_genbank.shuffle_dict(derep_data)

with open(args['output'] + '_all_data.pkl', 'wb') as handle:
    pickle.dump(data_derep_shuffle, handle, protocol=pickle.HIGHEST_PROTOCOL)
handle.close()

print('\nTraining data save to ' + str(args['output'] + '_all_data.pkl'))

print('\nGenerating subsets for k-fold cross validation')
k = args['chunks']
n = int(len(data_derep_shuffle)/11)

if args['chunks'] > 0:
    suffix = [i for i in range(k - 1)]
    suffix.append('test')

    for i in range(k):
        fold = dict(list(data_derep_shuffle.items())[i * n: (i + 1) * n])

        filename = args['output'] + '_' + str(suffix[i]) + '_chunk.pkl'
        filehandler = open(filename, "wb")
        pickle.dump(fold, filehandler)

print('Complete!')
print(str(len(training_data)) + ' phages parsed. ' + str(len(data_derep_shuffle)) + ' phages used')