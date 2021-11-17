import os
import logging
import yaml

import numpy as np

import helper_functions
import rdkit_utils

logger = logging.getLogger(__name__)


class job_generator(object):
    """Generator of gaussian input files class"""

    def __init__(self, molecule, workflow_type, directory, theory, light_basis_set,
                 heavy_basis_set, generic_basis_set, max_light_atomic_number):
        """Initialize input generator for a given molecule.

        :param molecule: molecule object
        :type molecule: molecule
        :param workflow_type: Gaussian workflow type, allowed types are: 'equilibrium' or 'transition_state'
        :type workflow_type: str
        :param directory: local directory to store input files
        :type directory: str
        """

        self.directory = directory
        self.molecule = molecule
        # group elements into light and heavy
        light_elements, heavy_elements = rdkit_utils.get_light_and_heavy_elements(molecule.mol, max_light_atomic_number)
        self.heavy_block = ""

        if heavy_elements:
            basis_set = generic_basis_set
            self.heavy_block += f"{' '.join(light_elements + ['0'])}\n"
            self.heavy_block += f"{light_basis_set}\n****\n"
            self.heavy_block += f"{' '.join(heavy_elements + ['0'])}\n"
            self.heavy_block += f"{heavy_basis_set}\n****\n"
            self.heavy_block += f"\n"
            self.heavy_block += f"{' '.join(heavy_elements + ['0'])}\n"
            self.heavy_block += f"{heavy_basis_set}\n"
        else:
            basis_set = light_basis_set

        if workflow_type == "equilibrium":
            self.tasks = (
                f"opt=CalcFc {theory}/{basis_set} scf=xqc",
                f"freq {theory}/{basis_set} volume NMR pop=NPA density=current Geom=AllCheck Guess=Read",
                f"TD(NStates=10, Root=1) {theory}/{basis_set} volume pop=NPA density=current Geom=AllCheck Guess=Read"
            )
        elif workflow_type == "transition_state":
            self.tasks = (
                f"opt=(calcfc,ts,noeigentest) scf=xqc {theory}/{basis_set}",
                f"freq {theory}/{basis_set} volume NMR pop=NPA density=current Geom=AllCheck Guess=Read"
            )
        elif workflow_type == "test":
            self.tasks = (
                f"{theory}/{basis_set}",
            )
        else:
            raise ValueError(f"Not supported gaussian job type {workflow_type}. "
                             f"Allowed types are: equilibrium, transition_state.")

        # resource configuration
        with open('config.yml', 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
        self.n_processors = max(1, min(config['slurm']['max_processors'],
                                  self.molecule.mol.GetNumAtoms() // config['slurm']['atoms_per_processor']))
        self.ram = self.n_processors * config['slurm']['ram_per_processor']
        self.resource_block = f"%nprocshared={self.n_processors}\n%Mem={self.ram}GB\n"

    def create_gaussian_files(self) -> None:
        """Create the actual gaussian files for each conformer of the molecule."""

        # prepare directory for gaussian files
        helper_functions.cleanup_directory_files(self.directory, types=["gjf"])
        os.makedirs(self.directory, exist_ok=True)

        logger.info(f"Generating Gaussian input files for {self.molecule.mol.GetNumConformers()} conformations.")

        for conf_id, conf_coord in enumerate(self.molecule.conformer_coordinates):
            # set conformer
            conf_name = f"{self.molecule.inchikey}_conf_{conf_id}"

            # coordinates block
            geom_np_array = np.concatenate((np.array([self.molecule.elements]).T, conf_coord), axis=1)
            coords_block = "\n".join(map(" ".join, geom_np_array))

            # create the gaussian input file
            self._generate_file(self.tasks,
                                conf_name,
                                self.resource_block,
                                coords_block,
                                self.molecule.charge,
                                self.molecule.spin)

            self._create_h2_jobs(conf_name=conf_name)

    def _create_h2_jobs(self, conf_name):
        file_name = str(conf_name + '.sh')
        file_path = self.directory + '/' + file_name

        # start writing scripts
        to_write = '### ' + file_name + ' START ###\n'
        to_write += '#!/bin/bash\n' \
                    '#$ -cwd\n' \
                    '#$ -o logs/$JOB_ID.$JOB_NAME.joblog\n' \
                    '#$ -j y\n' \
                    '#$ -M $USER@mail\n' \
                    '#$ -m bea\n'
        to_write += '#$ -l h_data=' + str(self.ram+2) + 'G,' + 'h_rt=23:59:59,arch=intel-[Eg][5o][l-]*\n' #TODO: wall time
        to_write += '# #$ -pe shared ' + str(self.n_processors) +'\n' #TODO: fix memory logic
        to_write += '# #$ -l h_vmem=' + str(self.n_processors*(self.ram+2)) + 'G' + '\n\n'
        to_write += '# echo job info on joblog:' \
                    'echo "Job $JOB_ID started on:   " `hostname -s`\n' \
                    'echo "Job $JOB_ID started on:   " `date `\n' \
                    'echo " "\n\n' \
                    '# set job environment and GAUSS_SCRDIR variable\n' \
                    '. /u/local/Modules/default/init/modules.sh\n' \
                    'module load gaussian/g16_avx\n' \
                    'export GAUSS_SCRDIR=$TMPDIR\n' \
                    '# echo in joblog\n' \
                    'module li\n' \
                    'echo "GAUSS_SCRDIR=$GAUSS_SCRDIR"\n' \
                    'echo " "\n\n' \
                    'echo "/usr/bin/time -v $g16root/16_avx/g16 < ${JOB_NAME%.*}.gjf > out/${JOB_NAME%.*}.out"\n' \
                    '/usr/bin/time -v $g16root/16_avx/g16 < ${JOB_NAME%.*}.gjf > out/${JOB_NAME%.*}.out\n\n' \
                    '# echo job info on joblog\n' \
                    'echo "Job $JOB_ID ended on:   " `hostname -s`\n' \
                    'echo "Job $JOB_ID ended on:   " `date `\n' \
                    'echo " "\n' \
                    'echo "Input file START:"\n' \
                    'cat ${JOB_NAME%.*}.gjf\n' \
                    'echo "END of input file"\n' \
                    'echo " "\n' \
                    '### test.sh STOP ###\n\n'

        with open(file_path, 'w') as f:
            f.write(to_write)


    def _generate_file(self, tasks, name, resource_block, coords_block, charge, multiplicity) -> None:
        """

        :param tasks: tuple of Gaussian tasks
        :param name:  conformation name
        :param resource_block: resource block for the Gaussian input file
        :param coords_block: coordinates block for the Gaussian input file
        :param light_elements: list of light elements of the molecule
        :param heavy_elements: list of heavy elements of the molecule
        :param charge: molecule charge
        :param multiplicity: molecule multiplicity
        """

        output = ""

        # loop through the tasks in the workflow and create input file
        for i, task in enumerate(tasks):
            if i == 0:  # first task is special, coordinates follow
                output += resource_block
                output += f"%Chk={name}_{i}.chk\n"
                output += f"# {task}\n\n"
                output += f"{name}\n\n"
                output += f"{charge} {multiplicity}\n"
                output += f"{coords_block.strip()}\n"
                output += f"\n"
            else:
                output += "\n--Link1--\n"
                output += resource_block
                output += f"%Oldchk={name}_{i - 1}.chk\n"
                output += f"%Chk={name}_{i}.chk\n"
                output += f"# {task}\n"
                output += f"\n"

            output += self.heavy_block  # this is an empty string if no heavy elements are in the molecule

        output += f"\n\n"

        file_path = f"{self.directory}/{name}.gjf"
        with open(file_path, "w") as file:
            file.write(output)

        logger.debug(f"Generated a Gaussian input file in {file_path}")
