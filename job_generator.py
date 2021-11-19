import os
import logging
import yaml

import numpy as np

import helper_functions
import rdkit_utils
import cluster_functions

logger = logging.getLogger(__name__)


class JobGenerator(object):
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
            self._generate_gaussian_job(self.tasks,
                                        conf_name,
                                        self.resource_block,
                                        coords_block,
                                        self.molecule.charge,
                                        self.molecule.spin)

            cluster_functions.generate_h2_job(conf_name=conf_name)

    def _generate_gaussian_job(self, tasks, name, resource_block, coords_block, charge, multiplicity) -> None:
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
