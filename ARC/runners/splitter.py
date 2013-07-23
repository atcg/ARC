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
from ARC import exceptions


class Splitter:
    """
    Deprecated in favor of doing the splitting of reads post mapping as
    part of MapperRunner. This class handles splitting reads into fastq files
    and launching assemblies. Once all assemblies are launched, add a job to
    check that the assemblies have finished.
    """
    def __init__(self, params):
        self.params = params

    def start(self, params):
        print "Running the splitter"

        if not('mapper' in params):
            raise exceptions.FatalException("mapper not defined in params")
        if params['mapper'] == 'bowtie2':
            self.run_bowtie2(params)
        if params['mapper'] == 'blat':
            self.run_blat(params)
