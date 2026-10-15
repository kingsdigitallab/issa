# Data Processing

Follow these steps to process the batches of video files received 
from an archive in preparation for a workshop.

## Terms

* archive: the screen archive that supplied the video batches to ISSA; below NWFA
* workshop: each archive has its own workshop in the series; below it is 2
* video file: an .mp4 file
* batch: usually one folder with video files from a particular collection (e.g. H22, or Grampian channel)
* catalog: a file with a table holding information about every video tape or programme
* separator: a visual separator between two programmes (e.g. title card or color bars)
* programme: a continuous sequence of shots put together by the same author/editor/producer/camera crew; it can be rushes for a particular new report or a documentary, or an advert;
* RDS: the permanent storage space on KCL HPC CREATE, for input and final output data
* Scratch: the working storage area on KCL HPC CREATE, for intermediate processsing; unlike the RDS it can be accessed by compute nodes

## 1. Copy archive video batches to RDS

1. attach incoming drive with video batches to KDL ML computer
2. ssh into ML and copy the entire content to hpc:/rds/prj/dh_issa/data/input/NWFA/
3. ensure that all content has been copied properly (e.g. compare the source and target folders size; or checksums)

This must should remain read-only. At least until the end of the workshop.

## 2. Copy videos to Scratch

Create a new folder for the workshop 2, under hpc:/scratch/dh_issa/issa/workshops/ws2

Create a new sub-folder under that for the video batches, called `batches`

Copy all the *.mp4 anywhere under hpc:/rds/prj/dh_issa/data/input/NWFA/ 
**directly** under hpc:/scratch/dh_issa/issa/workshops/ws2/batches/.

`find /rds/prj/dh_issa/data/input/NWFA -type f -name "*.mp4" -exec cp -t . {} +`

Please ensure that all the files have a mp4 extension. 
If you have .MP4 instead: `rename 's/\.MP4$/.mp4/' *.MP4`

## 3. Collection.json and partitioning with filters

Copy a collections.js from the last workshop, e.g. workshops/ws1/collections.json
into workshops/ws2/.

Edit all parameters relevant to this workshop (mainly the data section at the end).

At the bottom of the data section, there is a `filters` dictionary. 
This is used by FrameSense and other scripts to filter the videos under the batches folder.
Each filter has a key or name and string value 
that consists of a pipe-separated list of keywords.
Any filename that contains at least one of the keywords will match the filter.

### Samples

The filters are used to define small samples of 20, 15, 10, 4, 2 and 1 videos.
The small samples allow us to experiment and test quickly before testing 
on larger one or the entire batches. Usually we do a deep analysis 
and pipeline work through over the sample10.

There are two ways to create a sample:
1. analyse the distribution of the video in the batches according to dimensions recorded in a catalog (e.g. duration, genre, source, year, color, etc). Then cherry pick 10 or more videos that represent that distribution and variety. See `ws1/notebooks/nls_metadata_analysis.ipynb`
2. create a random sample of 20 videos. Then iteratively sample from that to generate 15, 10, 4, 2 and 1. Trying to keep the original balance between batches. See `ws2/notebooks/sampling.ipynb`

### Partitions

Additional filters are also used to partition the batches 
into N distinct partitions. This enables parallel processing 
to save considerable amount of time on an HPC environment.

There's no single method to do that as it will depend on 
the format of the file names used by the archive.

See `ws2/collections.json` > `data.attributes.filters` for an example.

## 4. Reorganise and compress the videos on Scratch

```bash
cd batches
python vid-watcher.py
```

This script will move and compress any X.mp4 videos to X/X.mp4 
which is the structure FrameSense expects.

If you are short of space on Scratch, you can let the script run 
while copying new chunks of the batch into the batches folder. 
The script will detect new videos and compress them on the fly.
But keep in mind that copying is much faster than compressing
so you need to feed it chunks manually.

### On HPC

You'll need to run that on a cpu node:

```bash
cd batches
srun -p interruptible_cpu -c 12 -n 1 --mem=6G --time 4:00:00 python vid-watcher.py
```

Note that there is a time limit on compute node. 
By the end of it the script will be terminated and may leave .mp4 files 
unprocessed under the batches folder.

### Parallel processing

To speed up the processing, you can run multiple instances of vid-watcher.py on different partitions:

```bash
cd batches
ISSA_PART=half1 sbatch vid-watcher.sbatch
ISSA_PART=half2 sbatch vid-watcher.sbatch
```
For more parallelism an 8 part partitioning can drastically reduce the time needed to compress your 400 video batches.

### Checking 

This command returns the number of videos that still need to be compressed and moved.

```bash
cd batches
ls *.mp4 | wc -l
```

