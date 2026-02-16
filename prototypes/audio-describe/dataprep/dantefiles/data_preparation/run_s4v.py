"""
Code modified from:

Side4Video: Spatial-Temporal Side Network for Memory-Efficient Image-to-Video Transfer Learning 
https://github.com/HJYao00/Side4Video
Yao, Huanjin and Wu, Wenhao and Li, Zhiheng

"""

import os
import argparse

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.nn.parallel import DistributedDataParallel
import torch.distributed as dist
import torch.backends.cudnn as cudnn
import torchvision

from utils.utils import init_distributed_mode

import clip
import yaml
from dotmap import DotMap

from datasets.kinetics import Video_dataset
from datasets.transforms import GroupScale, GroupCenterCrop, Stack, ToTorchFormatTensor, GroupNormalize
from modules.video_clip import video_header

class VideoCLIP(nn.Module):
    def __init__(self, clip_model, fusion_model, config) :
        super(VideoCLIP, self).__init__()
        self.visual = clip_model.visual
        self.fusion_model = fusion_model
        self.n_seg = config.data.num_segments
        self.drop_out = nn.Dropout(p=config.network.drop_fc)
        self.fc = nn.Linear(config.network.n_emb, config.data.num_classes)

    def forward(self, image):
        bt = image.size(0)
        b = bt // self.n_seg
        print("----------- image: \n",type(image),"\n visual:", type(self.visual))
        image_emb = self.visual(image)
        if image_emb.size(0) != b: # no joint_st
            image_emb = image_emb.view(b, self.n_seg, -1)
            image_emb = self.fusion_model(image_emb)

        image_emb = self.drop_out(image_emb)
        logit = self.fc(image_emb)
        return logit
    
    def extract_features(self, image):
        """Extract visual features from the backbone."""
        bt = image.size(0)
        b = bt // self.n_seg
        image_emb = self.visual(image)  # Extract features from the visual backbone
        if image_emb.size(0) != b:  # no joint_st
            image_emb = image_emb.view(b, self.n_seg, -1)
            image_emb = self.fusion_model(image_emb)
        return image_emb  # Return features without classification
    

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default="configs/k400_train_rgb_vitb-16-f8-side4video.yaml", type=str, help='global config file')
    parser.add_argument('--weights', default="ckpt/k400_vitb16_f8_82.5.pt", type=str)
    parser.add_argument('--output_dir', default="output/", type=str)
    parser.add_argument('--dist_url', default='env://',
                        help='url used to set up distributed training')
    parser.add_argument('--world_size', default=1, type=int,
                        help='number of distributed processes')                        
    parser.add_argument("--local-rank", type=int, default=0,
                        help='local rank for DistributedDataParallel')
    parser.add_argument(
        "--precision",
        choices=["amp", "fp16", "fp32"],
        default="amp",
        help="Floating point precition."
    )                        
    parser.add_argument('--test_crops', default=1, type=int)   
    parser.add_argument('--test_clips', default=1, type=int) 
    parser.add_argument('--dense', default=False, action="store_true",
                    help='use multiple clips for test')                     
    args = parser.parse_args()                                       
    return args


def update_dict(dict):
    new_dict = {}
    for k, v in dict.items():
        new_dict[k.replace('module.', '')] = v
    return new_dict


def main(args):

    print("000MMM000---000MMM000",args)
    init_distributed_mode(args)

    with open(args.config, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    config = DotMap(config)

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
        cudnn.benchmark = True

    # get fp16 model and weight
    model_name = config.network.arch

    # get fp16 model and weight
    model, clip_state_dict = clip.load(
        config.network.arch,
        device='cpu',jit=False,
        internal_modeling=config.network.tm,
        T=config.data.num_segments,
        dropout=config.network.drop_out,
        emb_dropout=config.network.emb_dropout,
        pretrain=config.network.init,
        joint_st = config.network.joint_st,
        side_dim=config.network.side_dim,
        download_root='./clip_pretrain') # Must set jit=False for training  ViT-B/32

    video_head = video_header(
        config.network.sim_header,
        clip_state_dict)

    if args.precision == "amp" or args.precision == "fp32":
        model = model.float()


    input_mean = [0.48145466, 0.4578275, 0.40821073]
    input_std = [0.26862954, 0.26130258, 0.27577711]

    # rescale size
    if 'something' in config.data.dataset:
        scale_size = (256, 320) 
    else:
        scale_size = 256 if config.data.input_size == 224 else config.data.input_size

    # crop size
    input_size = config.data.input_size

    # control the spatial crop
    if args.test_crops == 1: # one crop
        cropping = torchvision.transforms.Compose([
            GroupScale(scale_size),
            GroupCenterCrop(input_size),
        ])
    else:
        raise ValueError("Only 1, 3, 5, 10 crops are supported while we got {}".format(args.test_crops))


    val_data = Video_dataset(       
        config.data.val_root, config.data.val_list, config.data.label_list,
        random_shift=False, num_segments=config.data.num_segments,
        modality=config.data.modality,
        image_tmpl=config.data.image_tmpl,
        test_mode=True,
        transform=torchvision.transforms.Compose([
            cropping,
            Stack(roll=False),
            ToTorchFormatTensor(div=True),
            GroupNormalize(input_mean,input_std),
        ]),
        dense_sample=args.dense,
        test_clips=args.test_clips)

    val_sampler = torch.utils.data.SequentialSampler(val_data)
    val_loader = DataLoader(val_data,
        batch_size=config.data.batch_size,num_workers=config.data.workers,
        sampler=val_sampler, pin_memory=True, drop_last=False)


    model_full = VideoCLIP(model, video_head, config)

    if os.path.isfile(args.weights):
        checkpoint = torch.load(args.weights, map_location='cpu')


        model_full.load_state_dict(update_dict(checkpoint['model_state_dict']))
        del checkpoint

    if args.distributed:
        model_full = DistributedDataParallel(model_full.cuda(), device_ids=[args.gpu], find_unused_parameters=True)

    validate(
        val_loader, device, 
        model_full, config, args.test_crops, args.test_clips,
        args.output_dir)
    
    return



def validate(val_loader, device, model, config, test_crops, test_clips, output_dir):

    model.eval()

    with torch.no_grad():
        for i, (image, class_id, directory) in enumerate(val_loader):
            batch_size = class_id.numel()
            num_crop = test_crops

            num_crop *= test_clips  # 4 clips for testing when using dense sample

            class_id = class_id.to(device)
            n_seg = config.data.num_segments
            image = image.view((-1, n_seg, 3) + image.size()[-2:])
            b, t, c, h, w = image.size()
            image_input = image.to(device).view(-1, c, h, w)

            print("---\n", type(model) ,"---\n")

            features = model.extract_features(image_input)  # Extract features
            
            save_features_as_pt(features, directory[0], output_dir)


    if dist.get_rank() == 0:
        print('-----Evaluation is finished------')


def save_features_as_pt(features, video_path, output_dir):
    year_folder = video_path.split('/')[-2]
    video_filename = video_path.split('/')[-1]
    video = video_filename.split('.')[0]
    output = os.path.join(output_dir, year_folder)
    os.makedirs(output, exist_ok=True)
    torch.save(features, os.path.join(output_dir, f"{video}.pt"))



if __name__ == '__main__':
    args = get_parser() 
    main(args)

