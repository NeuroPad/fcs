"""
Copyright 2025, FCS Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


class AsyncWorker:
    """Worker for processing background tasks asynchronously with retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay_base: int = 5):
        """
        Initialize the AsyncWorker.
        
        Parameters
        ----------
        max_retries : int
            Maximum number of retries for a failed job.
        retry_delay_base : int
            Base delay in seconds for exponential backoff.
        """
        self.queue = asyncio.Queue()
        self.task = None
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self._running = False

    async def worker(self):
        """Main worker loop that processes jobs from the queue."""
        self._running = True
        
        while self._running:
            try:
                logger.debug(f'Waiting for job (queue size: {self.queue.qsize()})')
                print(f'Got a job: (size of remaining queue: {self.queue.qsize()})')
                job = await self.queue.get()
                
                if job is None:  # Shutdown signal
                    break
                
                logger.info(f'Processing job (remaining queue: {self.queue.qsize()})')
                
                # Wrap the job in retry logic
                await self._execute_job_with_retry(job)
                
                # Mark job as done regardless of outcome
                self.queue.task_done()
                await asyncio.sleep(1)  # Small delay to prevent overwhelming the system
                
            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Critical error in worker: {e.__class__.__name__}: {str(e)}")
                await asyncio.sleep(10)  # Brief pause before continuing

    async def _execute_job_with_retry(self, job: Callable):
        """Execute a job with retry logic for graphiti_core errors."""
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                await job()
                logger.debug("Job completed successfully")
                return  # Job succeeded, exit retry loop
                
            except Exception as e:
                error_module = e.__class__.__module__
                is_graphiti_error = error_module.startswith('graphiti_core')
                
                retry_count += 1
                
                if is_graphiti_error and retry_count <= self.max_retries:
                    delay = self.retry_delay_base * retry_count
                    logger.warning(
                        f"Graphiti core error: {e.__class__.__name__}: {str(e)}. "
                        f"Retrying job ({retry_count}/{self.max_retries}) in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    if is_graphiti_error:
                        logger.error(
                            f"Max retries reached for graphiti_core error: "
                            f"{e.__class__.__name__}: {str(e)}"
                        )
                    else:
                        logger.error(
                            f"Non-graphiti error in job: {e.__class__.__name__}: {str(e)}"
                        )
                    break

    async def add_job(self, job: Callable) -> int:
        """
        Add a job to the processing queue.
        
        Parameters
        ----------
        job : Callable
            The job function to execute.
            
        Returns
        -------
        int
            Current queue size after adding the job.
        """
        await self.queue.put(job)
        return self.queue.qsize()

    async def start(self):
        """Start the async worker."""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.worker())
            logger.info("AsyncWorker started")
        else:
            logger.warning("AsyncWorker is already running")

    async def stop(self):
        """Gracefully stop the worker and clear any pending jobs."""
        try:
            self._running = False
            
            # Add shutdown signal to queue
            await self.queue.put(None)
            
            if self.task:
                try:
                    await asyncio.wait_for(self.task, timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning("Worker didn't stop gracefully, cancelling...")
                    self.task.cancel()
                    try:
                        await self.task
                    except asyncio.CancelledError:
                        pass
                except Exception as e:
                    logger.error(f"Error during worker shutdown: {str(e)}")
            
            # Clear remaining jobs in queue
            cleared_jobs = 0
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                    cleared_jobs += 1
                except asyncio.QueueEmpty:
                    break
                except Exception:
                    pass
            
            if cleared_jobs > 0:
                logger.info(f"Cleared {cleared_jobs} pending jobs from queue")
            
            logger.info("AsyncWorker stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during AsyncWorker shutdown: {str(e)}")
            # Force cancel task if still running
            if self.task and not self.task.cancelled():
                try:
                    self.task.cancel()
                    logger.info("Forcefully cancelled AsyncWorker task")
                except Exception:
                    logger.error("Failed to forcefully cancel AsyncWorker task")

    @property
    def queue_size(self) -> int:
        """Get the current queue size."""
        return self.queue.qsize()

    @property
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._running and self.task is not None and not self.task.done()


# Global worker instance
async_worker = AsyncWorker() 