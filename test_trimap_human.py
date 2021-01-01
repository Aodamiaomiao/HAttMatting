from tqdm import tqdm
from time import time
import random

import torch
import torchvision
from torchsummary import summary
from torch.utils.data.dataloader import DataLoader
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from tensorboardX import SummaryWriter
from torch.cuda.amp import autocast, GradScaler

from utils import parse_args, save_checkpoint, AverageMeter, clip_gradient, get_logger, get_learning_rate
from config import device, im_size, grad_clip, print_freq
from model import Model
from data_human import HADataset
from loss import LossFunction

def val(val_loader, model):
    model.val()
    losses = AverageMeter()
    # loss_function = alpha_prediction_loss
    criterion = LossFunction(args.stage)()
    
    # Batches
    for i, (img, alpha_label, trimap_label) in enumerate(val_loader):
        # Move to GPU, if available
        img = img.type(torch.FloatTensor).to(device)  # [N, 4, 320, 320]
        alpha_label = alpha_label.type(
            torch.FloatTensor).to(device)  # [N, 320, 320]
        alpha_label = alpha_label.unsqueeze(1)
        trimap_label = trimap_label.to(device)
        # Forward prop.
        trimap_out, alpha_out = model(img)  # [N, 3, 320, 320]
        trimap_out.squeeze(0)
        # alpha_out = alpha_out.reshape((-1, 1, im_size * im_size))  # [N, 320*320]
        trimap_out = trimap_out.argmax(dim=1)
        trimap_out[trimap_out==1] = 128
        trimap_out[trimap_out==2] = 255
        trimap_out = np.array(trimap_out, dtype=np.uint8)
        cv.imwrite(os.path.join('image/test/out', args.output_folder, img_path.split('/')[-1]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, default='checkpoint.txt')
    parser.add_argument('--checkpoint', type=str, default='BEST_checkkpoint.tar')
    parser.add_argument('--output-folder', type=str)
    parser.add_argument('--device', type=str)
    args = parser.parse_args()
    ensure_folder('images' )
    ensure_folder('images/test' )
    ensure_folder('images/test/out' )
    ensure_folder('images/test/out/' + args.output_folder)
    f = open(args.file, "w")

    checkpoint = args.checkpoint
    if args.device == 'cpu':
        checkpoint = torch.load(checkpoint, map_location=lambda storage, loc: storage)
    else:
        checkpoint = torch.load(checkpoint)
    model_state_dict = checkpoint['model_state_dict']
    model = Model('train_trimap').to(args.device)
    model.load_state_dict(model_state_dict)
    val_loader  = DataLoader(HADataset('valid'), batch_size=1, shuffle=False, num_workers=2)
    val(val_loader, model)

        
