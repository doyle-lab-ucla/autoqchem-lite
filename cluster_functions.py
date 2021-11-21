# functions specific to computer clusters
# reason for this is to separate out functions that is cluster specific
# aka functions that need to be modified to be used on other computer clusters


def generate_h2_job(job_generator, mol_name, conf_name):
    """
    function to generate submission scripts for gaussian jobs on hoffman2 computer cluster at UCLA

    :param job_generator: JobGenerator object
    :type job_generator: gaussian_job_generator.JobGenerator
    :param mol_name: name of the molecule, or inchikey when name is not available
    :type mol_name: str
    :param conf_name: name of the conformer with index
    :type conf_name: str
    """

    file_name = str(conf_name + '.sh')
    file_path = job_generator.directory + '/' + file_name

    # write submission scripts
    to_write = '#!/bin/bash\n' \
               '#$ -cwd\n' \
               '#$ -o logs/$JOB_ID.$JOB_NAME.joblog\n' \
               '#$ -j y\n' \
               '#$ -M $USER@mail\n' \
               '#$ -m bea\n'
    to_write += '#$ -l h_data=' + str(job_generator.ram + 4) + 'G,' + 'h_rt=' + str(job_generator.wall_time) + ',arch=intel-[Eg][5o][l-]*\n'
    to_write += '#$ -pe shared ' + str(job_generator.n_processors) + '\n\n'
    to_write += '# echo job info on joblog:\n' \
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
                'echo "/usr/bin/time -v $g16root/16_avx/g16 < ' + mol_name + '/${JOB_NAME%.*}.gjf > ' + mol_name + '/${JOB_NAME%.*}.out"\n' \
                '/usr/bin/time -v $g16root/16_avx/g16 < ' + mol_name + '/${JOB_NAME%.*}.gjf > ' + mol_name + '/${JOB_NAME%.*}.out\n\n' \
                '# echo job info on joblog\n' \
                'echo "Job $JOB_ID ended on:   " `hostname -s`\n' \
                'echo "Job $JOB_ID ended on:   " `date `\n' \
                'echo " "\n' \
                'echo "Input file START:"\n' \
                'cat ' + mol_name + '/${JOB_NAME%.*}.gjf\n' \
                'echo "END of input file"\n' \
                'echo " "\n\n'

    with open(file_path, 'w') as f:
        f.write(to_write)


def write_submission_script(job_generator, mol_name, conf_name):
    """
    write a submit command into a submission script for each conformer
    example: qsub water_conf_1.sh

    :param job_generator
    :type job_generator
    :param mol_name
    :type mol_name
    :param conf_name
    :type conf_name
    """
    file_name = 'submit.sh'
    file_path = job_generator.directory + '/../' + file_name

    to_write = 'qsub ' + mol_name + '/' + conf_name + '.sh\n'

    with open(file_path, 'a') as f:
        f.write(to_write)
