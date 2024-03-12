import random

import numpy as np
import yaml
from torch import manual_seed

from nerfstudio.engine.trainer import TrainerConfig
from nerfstudio.scripts import train
from nerfstudio.utils.rich_utils import CONSOLE


class WebUITrainer:
    def __init__(self):
        self.trainer = None
        self.config = None

    def train_loop(
        self,
        local_rank: int,
        world_size: int,
        config: TrainerConfig,
        global_rank: int = 0,
    ):
        def _set_random_seed(seed) -> None:
            """Set randomness seed in torch and numpy"""
            random.seed(seed)
            np.random.seed(seed)
            manual_seed(seed)

        _set_random_seed(config.machine.seed + global_rank)
        self.trainer = config.setup(local_rank=local_rank, world_size=world_size)
        self.trainer.setup()
        self.trainer.train()

    def main(self):
        assert self.config is not None, "Config is not set"
        if self.config.data:
            CONSOLE.log("Using --data alias for --data.pipeline.datamanager.data")
            self.config.pipeline.datamanager.data = self.config.data

        if self.config.prompt:
            CONSOLE.log("Using --prompt alias for --data.pipeline.model.prompt")
            self.config.pipeline.model.prompt = self.config.prompt

        if self.config.load_config:
            CONSOLE.log(f"Loading pre-set config from: {self.config.load_config}")
            self.config = yaml.load(
                self.config.load_config.read_text(), Loader=yaml.Loader
            )

        # quit the viewer when training is done to avoid blocking
        self.config.viewer.quit_on_train_completion = True

        self.config.set_timestamp()

        # print and save config
        self.config.print_to_terminal()
        self.config.save_config()
        train.launch(
            main_func=self.train_loop,
            num_devices_per_machine=self.config.machine.num_devices,
            device_type=self.config.machine.device_type,
            num_machines=self.config.machine.num_machines,
            machine_rank=self.config.machine.machine_rank,
            dist_url=self.config.machine.dist_url,
            config=self.config,
        )
