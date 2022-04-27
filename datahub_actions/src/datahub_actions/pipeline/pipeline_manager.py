import logging
import traceback
from dataclasses import dataclass
from threading import Thread
from typing import Dict

from datahub_actions.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)


@dataclass
class PipelineSpec:
    # The pipeline name
    name: str

    # The pipeline
    pipeline: Pipeline

    # The thread which is executing the pipeline.
    thread: Thread


# Start a pipeline
# TODO: Exit process on failure.
def run_pipeline(pipeline: Pipeline) -> None:
    try:
        pipeline.run()
    except Exception:
        logger.error(
            f"Caught exception while executing pipeline with name {pipeline.name}: {traceback.format_exc(limit=3)}"
        )
        pipeline.stop()
    logger.debug(f"Thread for pipeline with name {pipeline.name} has terminated.")


# A manager of multiple Action Pipelines.
# This class manages 1 thread per pipeline registered.
class PipelineManager:

    # A catalog of all the currently executing Action Pipelines.
    pipeline_registry: Dict[str, PipelineSpec] = {}

    # Initialize the Actions Manager.
    def init(self):
        pass

    # Start a new Action Pipeline.
    def start_pipeline(self, name: str, pipeline: Pipeline) -> None:
        logger.debug(f"Attempting to start pipeline with name {name}...")
        if name not in self.pipeline_registry:
            thread = Thread(target=run_pipeline, args=([pipeline]))
            thread.start()
            spec = PipelineSpec(name, pipeline, thread)
            self.pipeline_registry[pipeline.name] = spec
            logger.debug(f"Started pipeline with name {name}.")
        else:
            raise Exception(f"Pipeline with name {name} is already running.")

    # Terminate a running Action Pipeline.
    def terminate_pipeline(self, name: str) -> None:
        logger.debug(f"Attempting to terminate pipeline with name {name}...")
        if name in self.pipeline_registry:
            # First, stop the pipeline.
            try:
                pipeline_spec = self.pipeline_registry[name]
                pipeline_spec.pipeline.stop()
                pipeline_spec.thread.join()  # Wait for the pipeline thread to terminate.
                logger.info(f"Actions Pipeline with name '{name}' has been stopped.")
                pipeline_spec.pipeline.stats().pretty_print_summary(
                    name
                )  # Print the pipeline's statistics.
                del self.pipeline_registry[name]
            except Exception:
                # Failed to stop a pipeline - this is a critical issue, we should avoid starting another action of the same type
                # until this pipeline is confirmed killed.
                logger.error(
                    f"Caught exception while attempting to terminate pipeline with name {name}: {traceback.format_exc(limit=3)}"
                )
                raise Exception(
                    f"Caught exception while attempting to terminate pipeline with name {name}."
                )
        else:
            raise Exception(f"No pipeline with name {name} found.")

    # Terminate all running pipelines.
    def terminate_all(self) -> None:
        logger.debug("Attempting to terminate all running pipelines...")
        # Stop each running pipeline.
        names = list(self.pipeline_registry.keys()).copy()
        for name in names:
            self.terminate_pipeline(name)
        logger.debug("Successfully terminated all running pipelines.")