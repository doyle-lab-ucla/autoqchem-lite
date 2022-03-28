# autobot
#

import pandas as pd
import json
import os
import pickle
from datetime import date, datetime
from pathlib import Path

from gaussian_job_generator import JobGenerator
from gaussian_log_extractor import GaussianLogExtractor
from helper_functions import str_chop


class AutoBot(object):

    def __init__(self, workdir):
        if workdir is None:
            # TODO: name for workdir
            self.workdir = os.path.join(os.getcwd(), 'tests', datetime.now().strftime("%m-%d-%Y-%H-%M-%S"))
        else:
            self.workdir = workdir
        #self.cachedir = os.path.join(self.workdir, 'cache')
        os.makedirs(self.workdir, exist_ok=True)
        #os.makedirs(self.cachedir, exist_ok=True)

        # create submission.sh with bash header
        file_path = os.path.join(self.workdir, 'submit.sh')
        with open(file_path, 'w') as f:
            f.write('#!/bin/bash\n')

        # a list of molecule names processed by autobot
        self.mol_list = []

    def create_excited_gaussian_jobs(self,
                                     molecule,
                                     theory='B3LYP',
                                     light_basis_set='6-31G+(d,p)',
                                     heavy_basis_set="LANL2DZ",
                                     generic_basis_set="genecp",
                                     max_light_atomic_number=36,
                                     wall_time='23:59:00'):
        pass #TODO

    def create_gaussian_jobs(self,
                             molecule,
                             workflow_type="equilibrium",
                             theory="APFD",
                             light_basis_set="6-31G(d,p)",
                             heavy_basis_set="LANL2DZ",
                             generic_basis_set="genecp",
                             max_light_atomic_number=36,
                             wall_time='23:59:00') -> None:

        if not molecule.name:
            mol_workdir = os.path.join(self.workdir, molecule.inchikey)
            self.mol_list.append(molecule.inchikey)
        else:
            mol_workdir = os.path.join(self.workdir, molecule.name)
            self.mol_list.append(molecule.name)

        generator = JobGenerator(molecule, workflow_type, mol_workdir, theory,
                                 light_basis_set, heavy_basis_set, generic_basis_set,
                                 max_light_atomic_number, wall_time)

        # TODO: possible db check

        generator.create_gaussian_files()

        # save a copy of gaussian configs for this molecule
        gaussian_config = {'workflow_type': workflow_type,
                           'theory': theory,
                           'light_basis_set': light_basis_set,
                           'heavy_basis_set': heavy_basis_set,
                           'generic_basis_set': generic_basis_set,
                           'max_light_atomic_number': max_light_atomic_number,
                           'wall_time': wall_time}

        with open(str(mol_workdir + '/gaussian_config.json'), 'w') as f:
            json.dump(gaussian_config, f)

    def extract_features(self):

        features = {}
        for path in Path(self.workdir).rglob('*.out'):
            gle = GaussianLogExtractor(path)
            f = gle.get_descriptors()
            conf_name = str_chop(path.name, '.out')
            features[conf_name] = f

        # make pandas dataframe


        return features

    def save(self, name):
        # save autobot
        pass

    def _find_out_files(self):
        for path in Path(self.workdir).rglob('*.out'):
            print(path)


    def _cache(self) -> None:

        with open(self.cache_file, 'wb') as cf:
            pickle.dump(self.jobs, cf)

        cleanup_empty_dirs(self.workdir)
