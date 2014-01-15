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
import multiprocessing
#import os
#from copy import deepcopy
from Queue import Empty
from ARC import ProcessRunner
from ARC import logger
from ARC import exceptions
from ARC.runners import Mapper


class Spawn:
    def __init__(self, config):
        self.nprocs = int(config['nprocs'])

        #Setup thread-safe shared objects
        self.job_q = multiprocessing.Queue()
        self.result_q = multiprocessing.Queue()
        self.finished = multiprocessing.Array('i', [0] * self.nprocs)

        # Get the number of samples from the configuration
        logger.info("Submitting initial mapping runs.")

        for sample in config['Samples']:
            s = config['Samples'][sample]
            params = {}
            for k in config:
                params[k] = config[k]
            params['working_dir'] = s['working_dir']
            params['finished_dir'] = s['finished_dir']
            params['sample'] = sample

            if 'PE1' in s and 'PE2' in s:
                params['PE1'] = s['PE1']
                params['PE2'] = s['PE2']
            if 'SE' in s:
                params['SE'] = s['SE']

            # mapper = Mapper(params)
            self.job_q.put(Mapper.to_job(params))

    def run(self):
        logger.info("Starting...")
        logger.debug("Setting up workers.")
        workers = []
        for i in range(self.nprocs):
            worker = ProcessRunner(
                self.job_q,
                self.result_q,
                self.finished,
                i)
            worker.daemon = False
            workers.append(worker)
            worker.start()

        status_ok = 0
        status_rerun = 0
        sleeptime = 0.1
        while True:
            try:
                time.sleep(sleeptime)
                result = self.result_q.get_nowait()
                #print "Spawner, setting sleeptime to %s" % sleeptime
                sleeptime = 0
                if result['status'] == 0:
                    logger.debug("Completed successfully %s" % (
                        result['process']))
                    status_ok += 1
                elif result['status'] == 1:
                    logger.debug("Rerunnable error returned from %s" % (
                        result['process']))
                    status_rerun += 1
                elif result['status'] == 2:
                    logger.error("Fatal error returned from %s" % (
                        result['process']))
                    logger.error("Terminating processes")
                    self.kill_workers(workers)
                    raise exceptions.FatalError("Unrecoverable error")
                elif result['status'] == 3:
                    logger.debug("Empty state returned from %s" % (
                        result['process']))
                elif result['status'] == 4:
                    logger.debug("%s worker needs to be retired" % (
                        result['process']))
                    self.retire_worker(
                        workers,
                        result['process'],
                        self.job_q,
                        self.result_q,
                        self.finished)
                else:
                    logger.error("Unknown state returned from %s" % (
                        result['process']))
                    self.kill_workers(workers)
            except (KeyboardInterrupt, SystemExit):
                logger.error("Terminating processes")
                self.kill_workers(workers)
                raise
            except Empty:
                sleeptime = 5
                #print "Spawn setting sleeptime to", sleeptime
                # In rare cases, the queue can be empty because a worker just
                # pulled a job, but hasn't yet gotten to update the finished
                # status. This will cause not_done() to return False, causing
                # the loop to break. Adding a short sleep here allows workers
                # to update their status.
                #time.sleep(5.5)
                if self.done():
                    logger.debug(
                        "Results queue is empty, Job queue is empty, "
                        "and there are no active processes. Exiting")
                    break
                else:
                    logger.debug(
                        "Results queue is empty but not all jobs are done. "
                        "Waiting...")

        logger.info("%d processes returned ok" % (status_ok))
        logger.info("%d processes had to be rerun" % (status_rerun))
        self.kill_workers(workers)

    def kill_workers(self, workers):
        for worker in workers:
            logger.debug("Shutting down %s" % (worker.name))
            worker.terminate()

    def retire_worker(self, workers, process, job_q, result_q, finished):
        for i in range(len(workers)):
            worker = workers[i]
            if worker.name == process:
                logger.info("Terminating working %s" % worker.name)
                worker.terminate()
                worker = ProcessRunner(job_q, result_q, finished, i)
                worker.daemon = False
                workers[i] = worker
                worker.start()
                logger.info("Started new worker %s" % worker.name)

    def done(self):
        # Check that all workers are done and all queues are empty
        logger.debug("Checking to see if everything is done.")

        #check workers
        if 0 in self.finished:
            logger.debug("Worker was not done.")
            return(False)

        # for i in self.finished:
        #     done += i
        #check queues
        if not self.job_q.empty():
            logger.debug("Job_q was not empty.")
            return(False)

        if not self.result_q.empty():
            logger.debug("Results_q was not empty.")
            return(False)

        # logger.debug("Active Workers: %d" % (
        #     len(self.finished) - done))
        #return done < len(self.finished)
        return(True)

    def not_empty(self, q):
        return not q.empty()
