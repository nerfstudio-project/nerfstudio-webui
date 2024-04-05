import multiprocessing
import os
from pathlib import Path

import gradio as gr
from utils.utils import (
    get_folder_path,
    browse_folder,
    browse_cfg,
    submit,
    generate_args,
)
from nerfstudio.scripts.exporter import (
    ExportCameraPoses,
    ExportGaussianSplat,
    ExportMarchingCubesMesh,
    ExportPointCloud,
    ExportPoissonMesh,
    ExportTSDFMesh,
)

current_path = Path(__file__).parent

exporter_configs = {
    "ExportCameraPoses": ExportCameraPoses(current_path, current_path),
    "ExportGaussianSplat": ExportGaussianSplat(current_path, current_path),
    "ExportMarchingCubesMesh": ExportMarchingCubesMesh(current_path, current_path),
    "ExportPointCloud": ExportPointCloud(current_path, current_path),
    "ExportPoissonMesh": ExportPoissonMesh(current_path, current_path),
    "ExportTSDFMesh": ExportTSDFMesh(current_path, current_path),
}


class ExporterTab:
    def __init__(self, **kwargs):
        super().__init__()
        self.root_dir = kwargs.get("root_dir", "./")  # root directory
        self.run_in_new_terminal = kwargs.get(
            "run_in_new_terminal", False
        )  # run in new terminal

        self.exporter_args = {}

        self.exporter_groups = []  # keep track of the exporter groups
        self.exporter_group_idx = {}  # keep track of the exporter group index
        self.exporter_arg_list = []  # gr components for the exporter args
        self.exporter_arg_names = []  # keep track of the exporter args names
        self.exporter_arg_idx = {}  # record the start and end index of the exporter args

        self.p = None

    def setup_ui(self):
        with gr.Tab(label="Export"):
            status = gr.Textbox(label="Status", lines=1, placeholder="Waiting")
            with gr.Row():
                exporter = gr.Radio(
                    choices=list(exporter_configs.keys()), label="Method", scale=5
                )
                run_button = gr.Button(value="Export", variant="primary", scale=1)
                stop_button = gr.Button(value="Stop", variant="stop", scale=1)
            if os.name == "nt":
                with gr.Row():
                    data_path = gr.Textbox(
                        label="Data Path",
                        lines=1,
                        placeholder="Path to the model config",
                        scale=4,
                    )
                    browse_button = gr.Button(value="Browse Config", scale=1)
                    browse_button.click(browse_cfg, None, outputs=data_path)
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
                        placeholder="Path to the model config",
                        scale=5,
                    )
                    input_button = gr.Button(value="Submit", scale=1)
                with gr.Row():
                    file_explorer = gr.FileExplorer(
                        label="Browse",
                        scale=1,
                        root_dir=self.root_dir,
                        file_count="single",
                        height=300,
                        glob="*.yml",
                    )
                    file_explorer.change(
                        lambda x: str(x), inputs=file_explorer, outputs=data_path
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
            with gr.Accordion("Exporter Config", open=False):
                for key, config in exporter_configs.items():
                    with gr.Group(visible=False) as group:
                        generated_args, labels = generate_args(config, visible=True)
                        self.exporter_arg_list += generated_args
                        self.exporter_arg_names += labels
                        self.exporter_arg_idx[key] = [
                            len(self.exporter_arg_list) - len(generated_args),
                            len(self.exporter_arg_list),
                        ]
                        self.exporter_groups.append(group)
                        self.exporter_group_idx[key] = len(self.exporter_groups) - 1
                exporter.change(
                    self.update_exporter_args_visibility,
                    inputs=exporter,
                    outputs=self.exporter_groups,
                )
            run_button.click(
                self.get_exporter_args,
                inputs=[exporter] + self.exporter_arg_list,
                outputs=None,
            ).then(
                self.run_exporter,
                inputs=[exporter, data_path, output_dir],
                outputs=status,
            )
            stop_button.click(self.stop, inputs=None, outputs=status)

    def update_exporter_args_visibility(self, exporter):
        idx = self.exporter_group_idx[exporter]
        update_info = [gr.update(visible=False)] * len(self.exporter_groups)
        update_info[idx] = gr.update(visible=True)
        return update_info

    def run_exporter(self, exporter, data_path, output_dir):
        if exporter == "":
            return "Please select a exporter"
        if data_path == "":
            return "Please select a data path"
        if output_dir == "":
            return "Please select a output directory"
        data_path = Path(data_path)
        output_dir = Path(output_dir)
        exporter = exporter_configs[exporter]
        exporter.load_config = data_path
        exporter.output_dir = output_dir

        for key, value in self.exporter_args.items():
            setattr(exporter, key, value)
        self.p = multiprocessing.Process(target=exporter.main)
        self.p.start()
        self.p.join()
        return "Exporting finished"

    def get_exporter_args(self, exporter, *args):
        temp_args = {}
        args = list(args)
        names = self.exporter_arg_names[
            self.exporter_arg_idx[exporter][0] : self.exporter_arg_idx[exporter][1]
        ]
        values = args[
            self.exporter_arg_idx[exporter][0] : self.exporter_arg_idx[exporter][1]
        ]
        for key, value in zip(names, values):
            temp_args[key] = value
        self.exporter_args = temp_args

    def stop(self):
        self.p.terminate()
        return "Export stopped"
