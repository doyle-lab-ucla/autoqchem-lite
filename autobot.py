# autobot
#

import pandas as pd
import json
import os
import pickle
from datetime import date, datetime

from gaussian_job_generator import JobGenerator


class AutoBot(object):

    def __init__(self):

        # TODO: name for workdir
        self.workdir = os.path.join(os.getcwd(), 'tests', datetime.now().strftime("%m-%d-%Y-%H-%M-%S"))
        #self.cachedir = os.path.join(self.workdir, 'cache')
        os.makedirs(self.workdir, exist_ok=True)
        #os.makedirs(self.cachedir, exist_ok=True)

        # create submission.sh with bash header
        file_path = os.path.join(self.workdir, 'submit.sh')
        with open(file_path, 'w') as f:
            f.write('#!/bin/bash\n')

    def create_gaussian_jobs(self,
                             molecule,
                             workflow_type="equilibrium",
                             theory="APFD",
                             light_basis_set="6-31G*",
                             heavy_basis_set="LANL2DZ",
                             generic_basis_set="genecp",
                             max_light_atomic_number=36,
                             wall_time='23:59:00') -> None:

        if not molecule.name:
            mol_workdir = os.path.join(self.workdir, molecule.inchikey)
        else:
            mol_workdir = os.path.join(self.workdir, molecule.name)

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

    def _cache(self) -> None:

        with open(self.cache_file, 'wb') as cf:
            pickle.dump(self.jobs, cf)

        cleanup_empty_dirs(self.workdir)
