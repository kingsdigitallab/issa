# How to get started

## Create the environment

1. On Linux, install Conda following this tutorial: [https://carpentries.github.io/workshop-template/install_instructions/#python-1]( https://carpentries.github.io/workshop-template/install_instructions/#python-1)  
1. Initialise the environment so that it uses python 3.9: `conda create --name dante python=3.9`  
1. Install the requirements in the environment: `conda env create -f environment.yml`

## Clone the Repo

Clone the [DANTE-AD git repo from GitHub](https://github.com/AdrienneDeganutti/DANTE-AD/tree/main)

## Get the data

### Get the model method 1

1. Leave `llama_model: "meta-llama/Llama-2-7b-hf"` as the path in `model_config.yaml`:  
1. Make sure that the model is downloaded:
To be able to use the model that is set in the config already, make sure that in `~ ls .cache/huggingface/hub` there is the `models--meta-llama--Llama-2-7b-hf` model and the size around 13 GB. To get the model there, use the huggingface hub.

### Get the model method 2  

1. Adjust the path in `model_config.yaml` to something relative to the `main.py` file.:  
If the above does not work, get the model for example with git and git-lfs:

1. First, log in on hugging face and accept the terms in both places.  
        1. accept the general hugging face terms.
        1. accept the meta specific terms if you are on the llama model site.
1. Clone the model repository with git.
1. Install `git-lfs` on your computer `sudo apt install git-lfs`.
1. cd into the directory where the model repo is and load the big files with `git lfs pull`.
1. In `prototypes/audio-describe/DANTE-AD/src/configs/video_llama/model_config.yaml` change the `llama_model` to a path relative to the main.py. For example `llama_model: "./Llama-2-7b-hf"` if the model is in the DANTE-AD directory.

### Get the checkpoint

Download the checkpoint from OneDrive as described in the DANTE-AD README.md file.

## Configure as described in the DANTE-AD README.md file

1. Change the path for the checkpoint in `prototypes/audio-describe/DANTE-AD/src/configs/video_llama/model_config.yaml` to a path relative to the main.py. For example `ckpt: "./model-ckpt.pth.tar"`if the checkpoint is in the DANTE-AD directory.

1. Configure the model to evaluation in `prototypes/audio-describe/DANTE-AD/src/configs/training_config.json` by changeing `"do_train"` to `false` on the first line.
