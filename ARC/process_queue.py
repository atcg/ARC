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
from multiprocessing import Manager


class ProcessQueue(object):
    def __init__(self, nprocs):
        """
            Initialize the queue management system.  Creates multiprocessing
            SyncManager queues for storing idle, executing and completed
            processes.  Adds locking mechanisms and a hash to store the
            running process information.
        """
        self.nprocs = nprocs
        self.mgr = Manager()
        #Setup thread-safe shared objects
        self.job_q = self.mgr.Queue()
        self.result_q = self.mgr.Queue()
        self.finished = self.mgr.Array('i', [0] * self.nprocs)
        # Add globals for things that need to be passed around everywhere
        self.universals = self.mgr.dict()

    def add_universals(self, universals):
        for key in universals.keys():
            self.universals[key] = universals[key]

    def submit(self):
        pass
