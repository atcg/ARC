#!/usr/bin/env python

# Copyright 2013, Institute for Bioninformatics and Evolutionary Studies
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import subprocess
import os
from ARC import exceptions
from ARC import logger


class MapperRunner:
    """
    This calss handles mapping jobs, as well as converting map results into a text version of a dict.
    """
    def __init__(self, params):
        self.params = params

    def to_dict(self):
        return {'runner': self, 'message': 'Starting mapper for sample %s' % self.params['sample'], 'params': self.params}

    def start(self):
        if not('mapper' in self.params):
            raise exceptions.FatalError("mapper not defined in params")
        if self.params['mapper'] == 'bowtie2':
            print "Running the bowtie2 for %s" % self.params['sample']
            self.run_bowtie2()
        if self.params['mapper'] == 'blat':
            print "Running the blat for %s" % self.params['sample']
            self.run_blat()

    def run_bowtie2(self):
        """
        Expects params:
            sample - required
            target - required
            PE1 and PE2 or SE
        """
        #Check for necessary params:
        if not ('sample' in self.params and 'reference' in self.params and 'working_dir' in self.params and (('PE1' in self.params and 'PE2' in self.params) or 'SE' in self.params)):
            raise exceptions.FatalError('Missing params in run_bowtie2.')
        #Check for necessary files:
        if os.path.exists(self.params['reference']) is False:
            raise exceptions.FatalError("Missing reference file for mapping")
        if 'PE1' in self.params and 'PE2' in self.params:
            if not (os.path.exists(self.params['PE1']) and os.path.exists(self.params['PE2'])):
                raise exceptions.FatalError("One or both PE files can not be found for mapping.")
        if 'SE' in self.params:
            if not os.path.exists(self.params['SE']):
                raise exceptions.FatalError("SE file cannot be found.")

        #Make temporary working directory and idx directory
        try:
            working_dir = self.params['working_dir']
            idx_dir = os.path.realpath(os.path.join(working_dir, 'idx'))
            os.mkdir(idx_dir)
            self.params['working_dir'] = working_dir
        except Exception as exc:
            txt = "Error creating working directory for Sample: %s" % (self.params['sample']) + '\n\t' + str(exc)
            raise exceptions.FatalError(txt)

        #Check whether to log to temporary file, or default to os.devnull
        if 'verbose' in self.params:
            out = open(os.path.join(working_dir, "mapping_log.txt"), 'w')
        else:
            out = open(os.devnull, 'w')

        #Build index
        base = os.path.join(idx_dir, 'idx')
        ret = subprocess.call(['bowtie2-build', '-f', self.params['reference'], base], stdout=out, stderr=out)
        if ret != 0:
            raise exceptions.FatalError("Error creating bowtie2 index for Sample: %s" % self.params['sample'])

        #Do bowtie2 mapping:
        args = ['bowtie2', '--local', '-x', base]
        if 'PE1' in self.params and 'PE2' in self.params:
            args += ['-1', self.params['PE1'], '-2', self.params['PE2']]
        if 'SE' in self.params:
            args += ['-U', self.params['SE']]
        args += ['-S', os.path.join(working_dir, 'mapping.sam')]
        ret = subprocess.call(args, stdout=out, stderr=out)
        out.close()
        if ret != 0:
            raise exceptions.FatalError("Error running bowtie2 mapping for Sample: %s" % self.params['sample'])

        #Extract the SAM to a dict
        read_map = self.SAM_to_dict(os.path.join(working_dir, 'mapping.sam'))
        self.write_dict(os.path.join(working_dir, 'mapping_dict.tsv'), read_map)
        #clean up intermediary files:
        os.remove(os.path.join(working_dir, 'mapping.sam'))
        os.system("rm -rf %s" % base)

        #return the self.params with the mapping_dict for the next step:
        self.params['mapping_dict'] = os.path.join(working_dir, 'mapping_dict.tsv')
        return self.params

    def run_blat(self):
        #Check for necessary params:
        if not ('sample' in self.params and 'reference' in self.params and 'working_dir' in self.params and (('PE1' in self.params and 'PE2' in self.params) or 'SE' in self.params)):
            raise exceptions.FatalError('Missing self.params in run_bowtie2.')
        #Check for necessary files:
        if os.path.exists(self.params['reference']) is False:
            raise exceptions.FatalError("Missing reference file for mapping")
        if 'PE1' in self.params and 'PE2' in self.params:
            if not (os.path.exists(self.params['PE1']) and os.path.exists(self.params['PE2'])):
                raise exceptions.FatalError("One or both PE files can not be found for mapping.")
        if 'SE' in self.params:
            if not os.path.exists(self.params['SE']):
                raise exceptions.FatalError("SE file cannot be found.")

        #Blat doesn't need an index
        working_dir = self.params['working_dir']

        #Check whether to log to temporary file, or default to os.devnull
        if 'verbose' in self.params:
            out = open(os.path.join(working_dir, "mapping_log.txt"), 'w')
        else:
            out = open(os.devnull, 'w')

        #Build a temporary txt file with all of the reads:
        allreads_outf = open(os.path.join(working_dir, 'reads.txt'), 'w')
        if 'PE1' in self.params and 'PE2' in self.params:
            allreads_outf.write(self.params['PE1'] + '\n')
            allreads_outf.write(self.params['PE2'] + '\n')
        if 'SE' in self.params:
            allreads_outf.write(self.params['SE'] + '\n')
        allreads_outf.close()

        #Do blat mapping
        args = ['blat', self.params['reference'], os.path.join(working_dir, 'reads.txt')]
        if 'format' in self.params and self.params['format'] == 'fastq':
            args.append('-fastq')
        if 'fastmap' in self.params:
            args.append('-fastMap')
        args.append(os.path.join(working_dir, 'mapping.psl'))

        ret = subprocess.call(args, stdout=out, stderr=out)
        out.close()
        if ret != 0:
            raise exceptions.FatalError('Error running blat mapping for sample: %s \n\t %s' % (self.params['sample'], " ".join(args)))

        #Extract the PSL to a dict
        read_map = self.PSL_to_dict(os.path.join(working_dir, 'mapping.psl'))
        self.write_dict(os.path.join(working_dir, 'mapping_dict.tsv'), read_map)
        os.remove(os.path.join(working_dir, 'mapping.psl'))

        #Return the self.params with the mapping_dict for the next step:
        self.params['mapping_dict'] = os.path.join(working_dir, 'mapping_dict.tsv')
        return self.params

    def SAM_to_dict(self, filename):
        """ Read a SAM file to a mapping dict and return it """
        #Check for necessary files:
        if os.path.exists(filename) is False:
            raise exceptions.FatalError("Missing SAM file")
        try:
            inf = open(filename, 'r')
        except Exception as exc:
            txt = "Failed to open SAM file %s" % filename
            txt += '\n\t' + str(exc)
            raise exceptions.FatalError(txt)
        read_map = {}  # target:{read} dictionary of dictionaries
        i = 0
        #startT = time.time()
        for l in inf:
            i += 1
            if l[0] != "@":
                l2 = l.strip().split()
                if l2[2] == "*":  # skip unmapped
                    continue
                readid = l2[0]
                target = l2[2]
                if target not in read_map:
                    read_map[target] = {}
                read_map[target][readid] = 1
        #Report total time:
        #logger.info("Processed %s lines in %s seconds." % (i, time.time() - startT))
        return read_map

    def PSL_to_dict(self, filename):
        try:
            inf = open(filename, 'r')
        except Exception as inst:
            if type(inst) == IOError:
                logger.error("Failed to open mapping dictionary %s." % filename)
            raise inst
        read_map = {}
        i = 0
        startT = time.time()

        psl_header = False

        for l in inf:
            i += 1
            #Check for PSL header and skip 5 lines if it exists
            if i == 1 and l.split()[0] == 'psLayout':
                psl_header = True
            if psl_header and i <= 5:
                continue
            l2 = l.strip().split("\t")
            readid = l2[9]
            target = l2[13]
            if target not in read_map:
                read_map[target] = {}
            read_map[target][readid] = 1
        logger.info("Processed %s lines in %s seconds." % (i, time.time() - startT))
        return read_map

    def write_dict(self, filename, read_map):
        """ Write a mapping dictionary to a file. """
        #startT = time.time()
        outf = open(filename, 'w')
        for k in read_map.keys():
            outf.write(k + '\t' + ",".join(read_map[k].keys()) + '\n')
        outf.close()
        #logger.info("Wrote all values to txt in %s seconds" % (time.time() - startT))

    def queue(self, ref_q):
        self.ref_q = ref_q
