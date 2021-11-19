# autobot
#

import pandas as pd
import os
import pickle
from datetime import date, datetime

from job_generator import JobGenerator


class autobot(object):

    def __init__(self):
        
        self.workdir = os.path.join(os.getcwd(), 'tests', datetime.now().strftime("%m-%d-%Y-%H-%M-%S"))
        self.cachedir = os.path.join(self.workdir, 'cache')
        os.makedirs(self.workdir, exist_ok=True)
        os.makedirs(self.cachedir, exist_ok=True)

    def create_gaussian_jobs(self,
                             molecule,
                             workflow_type="equilibrium",
                             theory="APFD",
                             light_basis_set="6-31G*",
                             heavy_basis_set="LANL2DZ",
                             generic_basis_set="genecp",
                             max_light_atomic_number=36,
                             wall_time='23:59:00') -> None:

        mol_workdir = os.path.join(self.workdir, molecule.inchikey)

        generator = JobGenerator(molecule,
                                  workflow_type,
                                  mol_workdir,
                                  theory,
                                  light_basis_set,
                                  heavy_basis_set,
                                  generic_basis_set,
                                  max_light_atomic_number)

        gaussian_config = {'theory': theory,
                           'light_basis_set': light_basis_set,
                           'heavy_basis_set': heavy_basis_set,
                           'generic_basis_set': generic_basis_set,
                           'max_light_atomic_number': max_light_atomic_number}

        # TODO: possible db check

        generator.create_gaussian_files()



    def test_write(self):
        df = pd.DataFrame([[1,2,3],[4,5,6]])
        p1 = os.path.join(self.workdir, 'test.csv')
        p2 = os.path.join(self.cachedir, 'test.csv')
        df.to_csv(path_or_buf=p1)
        df.to_csv(path_or_buf=p2)

    def _cache(self) -> None:

        with open(self.cache_file, 'wb') as cf:
            pickle.dump(self.jobs, cf)

        cleanup_empty_dirs(self.workdir)
