import os
import subprocess
import webbrowser

import gradio as gr


from nerfstudio.viewer_legacy.server import viewer_utils
from utils.utils import (
    run_cmd,
    browse_cfg,
)


class VisualizerTab:
    def __init__(self, **kwargs):
        self.root_dir = kwargs.get("root_dir", "./")  # root directory
        self.run_in_new_terminal = kwargs.get(
            "run_in_new_terminal", False
        )  # run in new terminal

        self.p = None
        self.websocket_port = None

    def setup_ui(self):
        with gr.Tab(label="Visualize"):
            status = gr.Textbox(label="Status", lines=1, placeholder="Waiting")
            with gr.Row():
                vis_button = gr.Button(value="Run Viser", variant="primary")
                stop_button = gr.Button(value="Stop", variant="stop")
                vis_cmd_button = gr.Button(value="Show Command")
                viser_button = gr.Button(value="Open Viser", variant="secondary")
                viser_button.click(self.open_viser)

            if os.name == "nt":
                with gr.Row():
                    config_path = gr.Textbox(
                        label="Config Path",
                        lines=1,
                        placeholder="Path to the config",
                        scale=4,
                    )
                    cfg_browse_button = gr.Button(value="Browse", scale=1)
                    cfg_browse_button.click(browse_cfg, None, outputs=config_path)
                    gr.ClearButton(components=[config_path], scale=1)
            else:
                with gr.Row():
                    config_path = gr.Textbox(
                        label="Config Path",
                        lines=1,
                        placeholder="Path to the config",
                        scale=5,
                    )
                    cfg_choose_button = gr.Button(value="Submit", scale=1)
                with gr.Row():
                    cfg_file_explorer = gr.FileExplorer(
                        label="Browse",
                        scale=1,
                        root_dir=self.root_dir,
                        file_count="single",
                        height=300,
                        glob="*.yml",
                    )
                    cfg_file_explorer.change(
                        lambda x: str(x), inputs=cfg_file_explorer, outputs=config_path
                    )
                    cfg_choose_button.click(
                        lambda x: str(x), inputs=config_path, outputs=config_path
                    )

            vis_button.click(self.run_vis, inputs=[config_path], outputs=status)
            vis_cmd_button.click(
                self.generate_vis_cmd, inputs=[config_path], outputs=status
            )
            stop_button.click(self.stop, inputs=None, outputs=status)

    def run_vis(self, config_path):
        cmd = self.generate_vis_cmd(config_path)
        # run the command
        if self.run_in_new_terminal:
            run_cmd(cmd)
        else:
            self.websocket_port = viewer_utils.get_free_port()
            cmd = f"{cmd} --viewer.websocket-port {self.websocket_port}"
            self.p = subprocess.Popen(cmd, shell=True)
        return "Viewer is on url: http://localhost:{}/".format(self.websocket_port)

    def generate_vis_cmd(self, config_path):
        # generate the command
        if config_path == "":
            raise gr.Error("Please select a config path")
        # this only works on windows
        cmd = f"ns-viewer --load-config {config_path}"
        # run the command
        # result = run_ns_train_realtime(cmd)
        # print(cmd)
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

    def stop(self):
        self.p.terminate()
        return "Viewer stopped"

    def open_viser(self):
        # open url in a new tab, if a browser window is already open.
        if self.websocket_port is None:
            raise gr.Error("Please run the training first")
        host = "localhost"
        port = self.websocket_port
        webbrowser.open_new_tab("http://{}:{}".format(host, port))
