from gaussian_log_extractor import GaussianLogExtractor
import helper_classes
from molecule import pybel, GetSymbol
import numpy as np

conv = pybel.ob.OBConversion()


def input_to_OBMol(input, input_type, input_format) -> pybel.ob.OBMol:
    """Create OBMol object from input

    :param input: string or file path
    :param input_type: input_types.string or input_types.file
    :param input_format: any format supported by OpenBabel, e.g. 'smi', 'cdx', 'pdb', etc.

    :return: openbabel.OBMol
    """

    mol = pybel.ob.OBMol()
    conv.SetInFormat(input_format)

    if input_type == "file":
        conv.ReadFile(mol, input)
    elif input_type == "string":
        conv.ReadString(mol, input)

    return mol


def OBMol_to_string(mol, format) -> str:
    """Convert from OBMol object to a string.

    :param mol: OBMol object
    :param format: any format supported by OpenBabel, e.g. 'smi', 'cdx', 'pdb', etc.
    :return: string representation of the molecule
    """

    conv.SetOutFormat(format)
    return conv.WriteString(mol).strip()


def OBMol_to_file(mol, format, target_path) -> None:
    """Convert from OBMol object to a file.

    :param mol: OBMol object
    :param format: any format supported by OpenBabel, e.g. 'smi', 'cdx', 'pdb', etc.
    :param target_path: path of the output file
    """

    conv.SetOutFormat(format)
    return conv.WriteFile(mol, target_path)


def OBMol_from_done_slurm_job(slurm_job) -> pybel.ob.OBMol:
    """Create OBMol object from a finished slurm gaussian job.

    :param slurm_job: slurm_job data structure
    :return: openbabel.OBMol
    """

    assert slurm_job.status.value == helper_classes.slurm_status.done.value
    le = gaussian_log_extractor(f"{slurm_job.directory}/{slurm_job.base_name}.log")
    le.get_atom_labels()
    le.get_geometry()
    # create OBMol from can
    mol = input_to_OBMol(slurm_job.can, input_type="string", input_format="can")
    mol.AddHydrogens()

    # adjust geometry
    for atom in pybel.ob.OBMolAtomIter(mol):
        pos = le.geom.iloc[atom.GetIdx() - 1]
        atom.SetVector(pos.X, pos.Y, pos.Z)

    return mol


def deduplicate_list_of_OBMols(mols, RMSD_threshold, symmetry) -> list:
    """Filter conformers based on their mutual RMSD, until all molecules have RMSD > threshold.

    :param mols: list of OBMol objects
    :param RMSD_threshold: RMSD threshold
    :param symmetry: boolean, if True symmetry is taken into account when comparing molecules in OBAlign(symmetry=True)
    :return: list of indices in the mols list that are duplicates
    """

    # safety check, assert all mols convert to the same canonical smiles
    assert (len(set(OBMol_to_string(mol, "can") for mol in mols)) == 1)

    # trivial case
    if len(mols) < 2:
        return []

    alignment = pybel.ob.OBAlign(True, symmetry)  # alignment class from OB

    duplicate_indices = []
    for i in range(len(mols) - 1):
        alignment.SetRefMol(mols[i])
        for j in range(i + 1, len(mols)):
            alignment.SetTargetMol(mols[j])
            alignment.Align()
            if alignment.GetRMSD() < RMSD_threshold and i not in duplicate_indices:
                duplicate_indices.append(j)

    return duplicate_indices


def extract_from_obmol(mol, ) -> tuple([list, np.ndarray, np.ndarray, np.ndarray]):
    """Extract information from Openbabel OBMol object with conformers."""

    py_mol = pybel.Molecule(mol)
    elements = [GetSymbol(atom.atomicnum) for atom in py_mol.atoms]
    charges = np.array([atom.formalcharge for atom in py_mol.atoms])

    n_atoms = len(py_mol.atoms)
    connectivity_matrix = np.zeros((n_atoms, n_atoms))
    for bond in pybel.ob.OBMolBondIter(mol):
        i = bond.GetBeginAtomIdx() - 1
        j = bond.GetEndAtomIdx() - 1
        bo = bond.GetBondOrder()
        connectivity_matrix[i, j] = bo
        connectivity_matrix[j, i] = bo

    # Retrieve conformer coordinates
    conformer_coordinates = []
    for i in range(mol.NumConformers()):
        mol.SetConformer(i)
        coordinates = np.array([atom.coords for atom in py_mol.atoms])
        conformer_coordinates.append(coordinates)
    conformer_coordinates = np.array(conformer_coordinates)

    return elements, conformer_coordinates, connectivity_matrix, charges


def generate_conformations_from_openbabel(smiles, num_conf, ob_gen3D_option='best'):
    # initialize obmol
    obmol = pybel.readstring('smi', smiles).OBMol
    obmol.AddHydrogens()

    # initial geometry
    gen3D = pybel.ob.OBOp.FindType("gen3D")
    gen3D.Do(obmol, ob_gen3D_option)

    # conf search
    confSearch = pybel.ob.OBConformerSearch()
    confSearch.Setup(obmol, num_conf)
    confSearch.Search()
    confSearch.GetConformers(obmol)

    elements, conformer_coordinates, connectivity_matrix, charges = extract_from_obmol(obmol)

    return elements, conformer_coordinates, connectivity_matrix, charges
