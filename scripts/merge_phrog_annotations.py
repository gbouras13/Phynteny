""" 
Add mmseqs annotations into phispy annotations 
"""

import gzip
import os
import re

# imports
import glob2
import handle_genbank
from Bio import SeqIO, bgzf

# read through each genome
directories = glob2.glob('/home/edwa0468/phage/Prophage/phispy/phispy/GCA/' + '/*', recursive=True)

for d in directories:

    e = glob2.glob(d + '/**',cd GI recursive=True)
    zipped_gdict = [i for i in e if i[-6:] == 'gbk.gz']

    for file in zipped_gdict:

        # convert genbank to a dictionary
        gb_dict = handle_genbank.get_genbank(file)
        gb_keys = list(gb_dict.keys())

        file_parts = re.split('/', file)
        genbank_parts = re.split('_', file_parts[11])
        mmseqs = '/home/edwa0468/phage/Prophage/phispy/phispy_phrogs/GCA/' + file_parts[8] + '/' + file_parts[9] + '/' + \
                 file_parts[10]
        mmseqs_fetch = glob2.glob(mmseqs + '/*')
 
        #check that there is an mmseqs file present (length is greate than 0) 
        if len(mmseqs_fetch) > 0:

            if os.stat(mmseqs_fetch[0]).st_size != 0:
                annotations = handle_genbank.get_mmseqs(mmseqs_fetch[0])

                if len(annotations) > 0:

                    phrogs = handle_genbank.filter_mmseqs(annotations)
                    genbank_name = '/home/grig0076/scratch/phispy_phrogs/GCA/' + file_parts[8] + '/' + file_parts[
                        9] + '/' + file_parts[10] + '/' + genbank_parts[0] + '_' + genbank_parts[1] + '_phrogs_' + \
                                   genbank_parts[3]

                    # write to the genbank file
                    print(genbank_name, flush=True)
                    with gzip.open(genbank_name, 'wt') as handle:

                        # loop through each prophage
                        for key in gb_keys:

                            # get a prophage
                            this_prophage = gb_dict.get(key)

                            # get the cds
                            cds = [i for i in this_prophage.features if i.type == 'CDS']

                            # loop through each protein
