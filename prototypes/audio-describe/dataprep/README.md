# how to prepare data on CREATE

The purpose of the contents of this dataprep folder are simply to enable KDL engineers to reproduce my steps on the CREATE cluster.
Instead of cloning the DANTE-AD repo in here, I paste the whole files where I changed something into the dantefiles folder.

There are also data and checkpoint files needed, and it is described in the step-by-step list below how to get them:  
DANTE-AD/data_preparation/ckpt/k400_vitb16_f8_82.5.pt  
DANTE-AD/data_preparation/CMD-AD/data/WAVES.mkv (only KDL has this)


1. go to the `scratch` first.
1. Clone the [DANTE-AD git repo from GitHub](https://github.com/AdrienneDeganutti/DANTE-AD/tree/main)
1. Get the files:
    - [vitb-16-f8](https://1drv.ms/u/c/fd682d23eb414404/IQCmi5jaupr8TLrHObCtSycYAdbdBLY1OHEPLCijgD2JIPI)
    - [the mkv video](https://emckclac-my.sharepoint.com/:v:/g/personal/k2366861_kcl_ac_uk/IQB5uyq2zP0KSab2KaI3czyfAb3MiCLe7jTl8-RmwB-EMys?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=ROFypI)
1. Run the following commands:

```bash
conda deactivate
uv sync
srun --exclude=erc-hpc-comp222 -p interruptible_gpu -c 6 --mem-per-gpu 32G --gpus-per-task 1 --constraint "l40s" -n 1 --time 5:00:00 --pty bash
cd DANTE-AD/data_preparation/
ml load python/3.10.13-gcc-11.4.0
ml load cuda/12.2.1-gcc-13.2.0
ml load py-setuptools/63.4.3-gcc-11.4.0-python-3.10.13
source .venv/bin/activate
python run_s4v.py     --config configs/k400_train_rgb_vitb-16-f8-side4video.yaml     --weights ckpt/k400_vitb16_f8_82.5.pt     --output_dir data_preparation/output/
```
