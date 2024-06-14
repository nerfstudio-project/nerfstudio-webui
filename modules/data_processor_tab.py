import multiprocessing
import os
from pathlib import Path
import argparse
import gradio as gr
from utils.utils import (
    get_folder_path,
    browse_folder,
    browse_video,
    submit,
    generate_args,
)
from nerfstudio.scripts.process_data import (
    ImagesToNerfstudioDataset,
    # ProcessMetashape,
    ProcessODM,
    ProcessPolycam,
    # ProcessRealityCapture,
    ProcessRecord3D,
    VideoToNerfstudioDataset,
)
from utils.utils import run_cmd

current_path = Path(__file__).parent
dataprocessor_configs = {
    "ImagesToNerfstudioDataset": ImagesToNerfstudioDataset(current_path, current_path),
    "VideoToNerfstudioDataset": VideoToNerfstudioDataset(current_path, current_path),
    "ProcessPolycam": ProcessPolycam(current_path, current_path),
    # "ProcessMetashape": ProcessMetashape(current_path, current_path, current_path),
    # "ProcessRealityCapture": ProcessRealityCapture(current_path, current_path, current_path),
    "ProcessRecord3D": ProcessRecord3D(current_path, current_path),
    "ProcessODM": ProcessODM(current_path, current_path),
}


class DataProcessorTab:
    def __init__(self, args: argparse.Namespace):
        super().__init__()
        self.root_dir = args.root_dir  # root directory
        self.run_in_new_terminal = args.run_in_new_terminal  # run in new terminal

        self.dataprocessor_args = {}
        self.dataprocessor_args_cmd = ""

        self.dataprocessor_groups = []  # keep track of the dataprocessor groups
        self.dataprocessor_group_idx = {}  # keep track of the dataprocessor group index
        self.dataprocessor_arg_list = []  # gr components for the dataprocessor args
        self.dataprocessor_arg_names = []  # keep track of the dataprocessor args names
        self.dataprocessor_arg_idx = {}  # record the start and end index of the dataprocessor args

        self.p = None

    def setup_ui(self):
        with gr.Tab(label="Process Data"):
            status = gr.Textbox(label="Status", lines=1, placeholder="Waiting")
            with gr.Row():
                dataprocessor = gr.Radio(
                    choices=list(dataprocessor_configs.keys()), label="Method", scale=5
                )
                run_button = gr.Button(value="Process", variant="primary", scale=1)
                cmd_button = gr.Button(value="Show Command", scale=1)
                stop_button = gr.Button(value="Stop", variant="stop", scale=1)

            if os.name == "nt":
                with gr.Row():
                    data_path = gr.Textbox(
                        label="Data Path",
                        lines=1,
                        placeholder="Path to the data",
                        scale=4,
                    )
                    browse_button = gr.Button(value="Browse Image", scale=1)
                    browse_button.click(browse_folder, None, outputs=data_path)
                    browse_video_button = gr.Button(value="Browse Video", scale=1)
                    browse_video_button.click(browse_video, None, outputs=data_path)
                    gr.ClearButton(components=[data_path], scale=1)
                with gr.Row():
                    output_dir = gr.Textbox(
                        label="Output Path",
                        lines=1,
                        placeholder="Path to the output folder",
                        scale=4,
                    )
                    out_button = gr.Button(value="Browse", scale=1)
                    out_button.click(browse_folder, None, outputs=output_dir)
                    gr.ClearButton(components=[output_dir], scale=1)
            else:
                with gr.Row():
                    data_path = gr.Textbox(
                        label="Data Path",
                        lines=1,
                        placeholder="Path to the data",
                        scale=5,
                    )
                    input_button = gr.Button(value="Submit", scale=1)
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
                    input_button.click(submit, inputs=data_path, outputs=data_path)
                with gr.Row():
                    output_dir = gr.Textbox(
                        label="Output Path",
                        lines=1,
                        placeholder="Path to the output folder",
                        scale=5,
                    )
                    out_button = gr.Button(value="Submit", scale=1)
                with gr.Row():
                    file_explorer = gr.FileExplorer(
                        label="Browse",
                        scale=1,
                        root_dir=self.root_dir,
                        file_count="multiple",
                        height=300,
                    )
                    file_explorer.change(
                        get_folder_path, inputs=file_explorer, outputs=output_dir
                    )
                    out_button.click(submit, inputs=output_dir, outputs=output_dir)

            with gr.Accordion("Data Processor Config", open=False):
                for key, config in dataprocessor_configs.items():
                    with gr.Group(visible=False) as group:
                        generated_args, labels = generate_args(config, visible=True)
                        self.dataprocessor_arg_list += generated_args
                        self.dataprocessor_arg_names += labels
                        self.dataprocessor_arg_idx[key] = [
                            len(self.dataprocessor_arg_list) - len(generated_args),
                            len(self.dataprocessor_arg_list),
                        ]
                        self.dataprocessor_groups.append(group)
                        self.dataprocessor_group_idx[key] = (
                            len(self.dataprocessor_groups) - 1
                        )
                dataprocessor.change(
                    self.update_dataprocessor_args_visibility,
                    inputs=dataprocessor,
                    outputs=self.dataprocessor_groups,
                )

            run_button.click(
                self.get_dataprocessor_args,
                inputs=[dataprocessor] + self.dataprocessor_arg_list,
                outputs=None,
            ).then(
                self.run_dataprocessor,
                inputs=[dataprocessor, data_path, output_dir],
                outputs=status,
            )
            cmd_button.click(
                self.get_dataprocessor_args,
                inputs=[dataprocessor] + self.dataprocessor_arg_list,
                outputs=None,
            ).then(
                self.generate_cmd,
                inputs=[dataprocessor, data_path, output_dir],
                outputs=status,
            )

            stop_button.click(self.stop, inputs=None, outputs=status)

    def update_status(self, data_path, method, data_parser, visualizer):
        if self.trainer is not None and self.trainer.step != 0:
            return "Step: " + str(self.trainer.step)
        else:
            check = self.check(data_path, method, data_parser, visualizer)
            if check is not None:
                return check
            return "Initializing..."

    def run_dataprocessor(self, datapocessor, data_path, output_dir):
        if datapocessor == "":
            return "Please select a data processor"
        if data_path == "":
            return "Please select a data path"
        if output_dir == "":
            return "Please select a output directory"

        if self.run_in_new_terminal:
            cmd = self.generate_cmd(datapocessor, data_path, output_dir)
            run_cmd(cmd)
        else:
            data_path = Path(data_path)
            output_dir = Path(output_dir)
            processor = dataprocessor_configs[datapocessor]
            processor.data = data_path
            processor.output_dir = output_dir
            for key, value in self.dataprocessor_args.items():
                setattr(processor, key, value)
            # TODO: this will lead werid errors when running subprocesses in this subprocess
            self.p = multiprocessing.Process(target=processor.main)
            self.p.start()
            self.p.join()
            return "Processing finished"

    def get_dataprocessor_args(self, dataprocessor, *args):
        temp_args = {}
        args = list(args)
        cmd = ""
        names = self.dataprocessor_arg_names[
            self.dataprocessor_arg_idx[dataprocessor][0] : self.dataprocessor_arg_idx[
                dataprocessor
            ][1]
        ]
        values = args[
            self.dataprocessor_arg_idx[dataprocessor][0] : self.dataprocessor_arg_idx[
                dataprocessor
            ][1]
        ]
        for key, value in zip(names, values):
            if isinstance(value, bool):
                key = "no-" + key if not value else key
                cmd += f" --{key}"
            else:
                cmd += f" --{key} {value}"
            temp_args[key] = value
        self.dataprocessor_args = temp_args
        self.dataprocessor_args_cmd = cmd

    def update_dataprocessor_args_visibility(self, dataprocessor):
        idx = self.dataprocessor_group_idx[dataprocessor]
        update_info = [gr.update(visible=False)] * len(self.dataprocessor_groups)
        update_info[idx] = gr.update(visible=True)
        return update_info

    def stop(self):
        self.p.terminate()
        return "Process stopped"

    def generate_cmd(
        self,
        dataprocessor,
        data_path,
        output_dir,
    ):
        if dataprocessor == "":
            raise gr.Error("Please select a data processor")
        if data_path == "":
            raise gr.Error("Please select a data path")
        if output_dir == "":
            raise gr.Error("Please select a output directory")

        method = None
        if dataprocessor == "ImagesToNerfstudioDataset":
            method = "images"
        elif dataprocessor == "VideoToNerfstudioDataset":
            method = "video"
        elif dataprocessor == "ProcessPolycam":
            method = "polycam"
        elif dataprocessor == "ProcessRecord3D":
            method = "record3d"
        elif dataprocessor == "ProcessODM":
            method = "odm"
        else:
            raise gr.Error("Invalid method")

        cmd = f"ns-process-data {method} --data {data_path} --output_dir {output_dir} {self.dataprocessor_args_cmd}"

        return cmd
