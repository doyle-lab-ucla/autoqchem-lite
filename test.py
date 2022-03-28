# test

from autobot import AutoBot
from molecule import Molecule
from gaussian_log_extractor import GaussianLogExtractor


def test():

    a = AutoBot()

    # build molecules

    smiles = ['COC1=CC=C(C(C2=CC=C(OC)C=C2)=O)C=C1',
              'C[N+](C)(C)C.[Br-]',
              '[Li]Br',
              'C12CCN(CC2)CC1',
              'CCCC[N+](CCCC)(CCCC)CCCC.[Br-]',
              'O=C(O[Na])O[Na]',
              'O=P(O[K])(O[K])O[K]',
              'O=C(O[Cs])O[Cs]',
              'O=C(O[Na])C(F)(F)F',]
    names = ['DMBP',
             'TMABr',
             'LiBr',
             'quin',
             'TBABr',
             'Na2CO3',
             'K3PO4',
             'Cs2CO3',
             'NaCO2CF3'
             ]

    for i in range(len(smiles)):
        mol = Molecule(smiles[i], name=names[i], num_conf=1)
        a.create_gaussian_jobs(mol)


def test_extract():
    gle = GaussianLogExtractor('tests/extract-test/CF3-mesitylene/CF3-mesitylene_conf_2.out')
    d = gle.get_descriptors()
    return d


if __name__ == '__main__':
    a = AutoBot(workdir='tests/extract-test')
    f = a.extract_features()
    print(f['water_conf_0'])
