A Gradio Webui for Nerfstudio.
![Screenshot](screenshot.png)
# Installation
Gradio needs to be installed in the nerfstudio environment by running:
```bash
pip install gradio
```

To start the webui, run:
```bash
python webui.py
```

# Usage
The webui can be accessed by visiting `http://localhost:7860` in a web browser.
Currently, the webui supports the following features:
- Training
- Visualization with viser
- Process Data
- Model Export

To train, pick the path to the dataset from the browser and pick to corresponding data parser. Then, click the train button to start training. The training progress can be monitored in the terminal.

To start the viser, choose the visualize tab and pick the config to the trained model. Then, click the visualize button to start the viser.

To process training data, choose the process data tab and pick the path to the dataset from the browser and pick the output path. Click submit to create a new folder if the output path does not exist. Pick the method to process the data. Then, click the process button to start processing the data. 

To export the trained model, choose the export tab and pick the config to the trained model, and pick the output path. Then, click the export button to start exporting.
