import os
from pathlib import Path
import webbrowser

import gradio as gr

from nerfstudio.configs import dataparser_configs as dc, method_configs as mc
from utils.trainer import WebUITrainer
from utils.utils import run_cmd, get_folder_path, browse_folder, submit, generate_args
from nerfstudio.viewer_legacy.server import viewer_utils


class TrainerTab(WebUITrainer):
    def __init__(self, **kwargs):
        super().__init__()
        self.root_dir = kwargs.get("root_dir", "./")  # root directory
        self.run_in_new_terminal = kwargs.get(
            "run_in_new_terminal", False
        )  # run in new terminal

        self.model_args_cmd = ""
        self.dataparser_args_cmd = ""
        self.model_args = {}
        self.dataparser_args = {}

        self.dataparser_groups = []  # keep track of the dataparser groups
        self.dataparser_group_idx = {}  # keep track of the dataparser group index
        self.dataparser_arg_list = []  # gr components for the dataparser args
        self.dataparser_arg_names = []  # keep track of the dataparser args names
        self.dataparser_arg_idx = {}  # record the start and end index of the dataparser args

        self.model_groups = []  # keep track of the model groups
        self.model_group_idx = {}  # keep track of the model group index
        self.model_arg_list = []  # gr components for the model args
        self.model_arg_names = []  # keep track of the model args names
        self.model_arg_idx = {}  # record the start and end index of the model args

        self.num_devices = kwargs.get("num_devices", 1)
        self.device_type = kwargs.get("device_type", "cuda")
        self.num_machines = kwargs.get("num_machines", 1)
        self.machine_rank = kwargs.get("machine_rank", 0)
        self.dist_url = kwargs.get("dist_url", "auto")

        self.websocket_port = None

    def setup_ui(self):
        with gr.Tab(label="Train"):
            status = gr.Textbox(label="Status", lines=1, placeholder="Waiting")
            with gr.Row():
                run_button = gr.Button(value="Train", variant="primary")
                stop_button = gr.Button(value="Stop", variant="stop")
                pause_button = gr.Button(value="Pause", variant="secondary")
                cmd_button = gr.Button(value="Show Command")
                viser_button = gr.Button(value="Open Viser", variant="secondary")
                viser_button.click(self.open_viser, inputs=None, outputs=None)

            with gr.Row():
                max_num_iterations = gr.Slider(
                    minimum=0,
                    maximum=50000,
                    step=100,
                    label="Max Num Iterations",
                    value=30000,
                )
                steps_per_save = gr.Slider(
                    minimum=0,
                    maximum=10000,
                    step=100,
                    label="Steps Per Save",
                    value=2000,
                )

            if os.name == "nt":
                with gr.Row():
                    data_path = gr.Textbox(
                        label="Data Path",
                        lines=1,
                        placeholder="Path to the data folder",
                        scale=4,
                    )
                    browse_button = gr.Button(value="Browse", scale=1)
                    browse_button.click(browse_folder, None, outputs=data_path)
                    gr.ClearButton(components=[data_path], scale=1)
            else:
                with gr.Row():
                    data_path = gr.Textbox(
                        label="Data Path",
                        lines=1,
                        placeholder="Path to the data folder",
                        scale=5,
                    )
                    choose_button = gr.Button(value="Submit", scale=1)
                with gr.Row():
                    file_explorer = gr.FileExplorer(
                        label="Browse",
                        scale=1,
                        root_dir=self.root_dir,
                        file_count="multiple",
                        height=300,
                    )
                    file_explorer.change(
                        get_folder_path, inputs=file_explorer, outputs=data_path
                    )
                    choose_button.click(submit, inputs=data_path, outputs=data_path)

            with gr.Row():
                with gr.Column():
                    method = gr.Radio(
                        choices=list(mc.descriptions.keys()), label="Method"
                    )
                    description = gr.Textbox(label="Description", visible=True)
                    method.change(
                        self.get_model_description, inputs=method, outputs=description
                    )
                with gr.Column():
                    dataparser = gr.Radio(
                        choices=list(dc.dataparsers.keys()), label="Data Parser"
                    )
                    visualizer = gr.Radio(
                        choices=[
                            "viewer",
                            "wandb",
                            "tensorboard",
                            "comet",
                            "viewer+wandb",
                            "viewer+tensorboard",
                            "viewer+comet",
                            "viewer_legacy",
                        ],
                        label="Visualizer",
                        value="viewer",
                    )

            with gr.Accordion("Model Config", open=False):
                for key, value in mc.descriptions.items():
                    with gr.Group(visible=False) as group:
                        if key in mc.method_configs:
                            model_config = mc.method_configs[key].pipeline.model  # type: ignore
                            generated_args, labels = generate_args(
                                model_config, visible=True
                            )
                            self.model_arg_list += generated_args
                            self.model_arg_names += labels
                            self.model_arg_idx[key] = [
                                len(self.model_arg_list) - len(generated_args),
                                len(self.model_arg_list),
                            ]
                            self.model_groups.append(group)
                            self.model_group_idx[key] = len(self.model_groups) - 1
                method.change(
                    self.update_model_args_visibility,
                    inputs=method,
                    outputs=self.model_groups,
                )

            with gr.Accordion("Data Parser Config", open=False):
                for key, parser_config in dc.dataparsers.items():
                    with gr.Group(visible=False) as group:
                        generated_args, labels = generate_args(
                            parser_config, visible=True
                        )
                        self.dataparser_arg_list += generated_args
                        self.dataparser_arg_names += labels
                        self.dataparser_arg_idx[key] = [
                            len(self.dataparser_arg_list) - len(generated_args),
                            len(self.dataparser_arg_list),
                        ]
                        self.dataparser_groups.append(group)
                        self.dataparser_group_idx[key] = len(self.dataparser_groups) - 1
                dataparser.change(
                    self.update_dataparser_args_visibility,
                    inputs=dataparser,
                    outputs=self.dataparser_groups,
                )

            update_event = run_button.click(
                self.update_status,
                inputs=[data_path, method, dataparser, visualizer],
                outputs=status,
                every=1,
            )
            run_button.click(
                self.get_model_args,
                inputs=[method] + self.model_arg_list,
                outputs=None,
            ).then(
                self.get_data_parser_args,
                inputs=[dataparser] + self.dataparser_arg_list,  # type: ignore
                outputs=None,
            ).then(
                self.run_train,
                inputs=[
                    data_path,
                    method,
                    max_num_iterations,
                    steps_per_save,
                    dataparser,
                    visualizer,
                ],
                outputs=None,
            ).then(cancels=[update_event])

            pause_button.click(self.pause, inputs=None, outputs=pause_button)

            stop_button.click(
                self.stop, inputs=None, outputs=status, cancels=[update_event]
            )

            cmd_button.click(
                self.get_model_args,
                inputs=[method] + self.model_arg_list,
                outputs=None,
            ).then(
                self.get_data_parser_args,
                inputs=[dataparser] + self.dataparser_arg_list,  # type: ignore
                outputs=None,
            ).then(
                self.generate_cmd,
                inputs=[
                    data_path,
                    method,
                    max_num_iterations,
                    steps_per_save,
                    dataparser,
                    visualizer,
                ],
                outputs=status,
            )

    def update_status(self, data_path, method, data_parser, visualizer):
        if self.trainer is not None and self.trainer.step != 0:
            return "Step: " + str(self.trainer.step)
        else:
            check = self.check(data_path, method, data_parser, visualizer)
            if check is not None:
                return check
            return "Initializing..."

    def pause(self):
        if self.trainer is not None:
            if self.trainer.training_state == "paused":
                self.trainer.training_state = "training"
                return "Pause"
            else:
                self.trainer.training_state = "paused"
                return "Resume"
        else:
            raise gr.Error("Please run the training first")

    def stop(self):
        # stop the training
        # FIXME: this will not release the resources
        if self.trainer is not None:
            config_path = self.config.get_base_dir() / "config.yml"
            ckpt_path = self.trainer.checkpoint_dir
            self.trainer.early_stop = True
            print(
                "Early Stopped. Config and checkpoint saved at "
                + str(config_path)
                + " and "
                + str(ckpt_path)
            )
            return (
                "Early Stopped. Config and checkpoint saved at "
                + str(config_path)
                + " and "
                + str(ckpt_path)
            )
        else:
            raise gr.Error("Please run the training first")

    def run_train(
        self,
        data_path,
        method,
        max_num_iterations,
        steps_per_save,
        data_parser,
        visualizer,
    ):
        cmd = self.generate_cmd(
            data_path,
            method,
            max_num_iterations,
            steps_per_save,
            data_parser,
            visualizer,
        )
        print(cmd)
        # run the command
        if self.run_in_new_terminal:
            run_cmd(cmd)
        else:
            # set up the config
            config = mc.all_methods[method]
            config.data = Path(data_path)
            config.max_num_iterations = max_num_iterations
            config.steps_per_save = steps_per_save
            config.vis = visualizer
            config.pipeline.datamanager.dataparser = dc.all_dataparsers[data_parser]
            self.websocket_port = viewer_utils.get_free_port()
            config.viewer.websocket_port = self.websocket_port
            for key, value in self.dataparser_args.items():
                setattr(config.pipeline.datamanager.dataparser, key, value)
            for key, value in self.model_args.items():
                setattr(config.pipeline.model, key, value)
            # from nerfstudio.scripts import train
            self.config = config
            self.main()

    def generate_cmd(
        self,
        data_path,
        method,
        max_num_iterations,
        steps_per_save,
        data_parser,
        visualizer,
    ):
        # generate the command
        if data_parser == "":
            raise gr.Error("Please select a data parser")
        if method == "":
            raise gr.Error("Please select a method")
        if data_path == "":
            raise gr.Error("Please select a data path")
        if visualizer == "":
            raise gr.Error("Please select a visualizer")
        cmd = f"ns-train {method} {self.model_args_cmd} --vis {visualizer} --max-num-iterations {max_num_iterations} \
        --steps-per-save {steps_per_save} --data {data_path} {data_parser} {self.dataparser_args_cmd}"
        check = self.check(data_path, method, data_parser, visualizer)
        if check is not None:
            return check
        return cmd

    def check(self, data_path, method, data_parser, visualizer):
        if data_path == "":
            return "Please select a data path"
        elif method == "":
            return "Please select a method"
        elif data_parser == "":
            return "Please select a data parser"
        elif visualizer == "":
            return "Please select a visualizer"
        else:
            return None

    def get_model_args(self, method, *args):
        temp_args = {}
        args = list(args)
        cmd = ""
        values = args[self.model_arg_idx[method][0] : self.model_arg_idx[method][1]]
        names = self.model_arg_names[
            self.model_arg_idx[method][0] : self.model_arg_idx[method][1]
        ]
        for key, value in zip(names, values):
            cmd += f"--pipeline.model.{key} {value} "
            temp_args[key] = value
        # remove the last space
        self.model_args_cmd = cmd[:-1]
        self.model_args = temp_args

    def get_data_parser_args(self, dataparser, *args):
        temp_args = {}
        args = list(args)
        cmd = ""
        names = self.dataparser_arg_names[
            self.dataparser_arg_idx[dataparser][0] : self.dataparser_arg_idx[
                dataparser
            ][1]
        ]
        values = args[
            self.dataparser_arg_idx[dataparser][0] : self.dataparser_arg_idx[
                dataparser
            ][1]
        ]
        for key, value in zip(names, values):
            # change key to --{key}
            cmd += f"--{key} {value} "
            temp_args[key] = value
        # remove the last space
        self.dataparser_args_cmd = cmd[:-1]
        self.dataparser_args = temp_args

    def get_model_description(self, method):
        return mc.descriptions[method]

    def update_dataparser_args_visibility(self, dataparser):
        # print(group_keys)
        # print(dataparser_args)
        idx = self.dataparser_group_idx[dataparser]
        # if the dataparser is not the current one, then hide the dataparser args
        update_info = [gr.update(visible=False)] * len(self.dataparser_groups)
        update_info[idx] = gr.update(visible=True)
        return update_info

    def update_model_args_visibility(self, method):
        if method not in self.model_group_idx.keys():
            return [gr.update(visible=False)] * len(self.model_groups)

        idx = self.model_group_idx[method]
        # if the method is not the current one, then hide the model args
        update_info = [gr.update(visible=False)] * len(self.model_groups)
        update_info[idx] = gr.update(visible=True)
        return update_info

    def open_viser(self):
        # open url in a new tab, if a browser window is already open.
        if self.websocket_port is None:
            raise gr.Error("Please run the training first")
        host = "localhost"
        port = self.websocket_port
        webbrowser.open_new_tab("http://{}:{}".format(host, port))
