import gradio as gr
import argparse
from modules.data_processor_tab import DataProcessorTab
from modules.exporter_tab import ExporterTab
from modules.trainer_tab import TrainerTab
from modules.visualizer_tab import VisualizerTab


class WebUI:
    def __init__(self, **kwargs):
        super().__init__()
        self.root_dir = kwargs.get("root_dir", "./")  # root directory
        self.run_in_new_terminal = kwargs.get(
            "run_in_new_terminal", False
        )  # run in new terminal
        self.demo = gr.Blocks()
        self.trainer_tab = TrainerTab(**kwargs)
        self.visualizer_tab = VisualizerTab(**kwargs)
        self.data_processor_tab = DataProcessorTab(**kwargs)
        self.exporter_tab = ExporterTab(**kwargs)

        self.setup_ui()

    def setup_ui(self):
        with self.demo:
            self.trainer_tab.setup_ui()
            self.visualizer_tab.setup_ui()
            self.data_processor_tab.setup_ui()
            self.exporter_tab.setup_ui()

    def launch(self, *args, **kwargs):
        self.demo.launch(*args, **kwargs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--root_dir', type=str, default='./',
                        help='Root directory for data selection in web-ui')
    parser.add_argument('--run_in_new_terminal', type=bool,
                        default=False, help='Run commands in new terminal')
    parser.add_argument('--share', type=bool, default=False,
                        help='Create public gradio share link')
    parser.add_argument('--server_name', type=str, default='0.0.0.0',
                        help='IP address or hostname of the web-ui server')
    parser.add_argument('--server_port', type=int,
                        default=7860, help='Port of the web-ui server')

    args = parser.parse_args()

    app = WebUI(root_dir=args.root_dir,
                run_in_new_terminal=args.run_in_new_terminal)
    app.launch(inbrowser=True, share=args.share,
               server_name=args.server_name, server_port=args.server_port)
