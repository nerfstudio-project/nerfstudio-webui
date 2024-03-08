import gradio as gr

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
    app = WebUI(root_dir="./", run_in_new_terminal=False)
    app.launch(inbrowser=True, share=False)
