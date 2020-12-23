from tqdm import tqdm
from time import time

import torch
import torchvision
from torchsummary import summary
from torch.utils.data.dataloader import DataLoader
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from tensorboardX import SummaryWriter

from utils import parse_args, save_checkpoint, AverageMeter, clip_gradient, get_logger, get_learning_rate, \
    alpha_prediction_loss, adjust_learning_rate
from config import device, im_size, grad_clip, print_freq

from model import Model
from data_tfrecord import HADataset

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print('Using device {}'.format(device))


def train(train_loader, model, optimizer, epoch, logger):
    model.train()  # train mode (dropout and batchnorm is used)

    losses = AverageMeter()

    # Batches
    for i, (img, alpha_label) in enumerate(train_loader):
        # Move to GPU, if available
        img = img.type(torch.FloatTensor).to(device)  # [N, 4, 320, 320]
        alpha_label = alpha_label.type(
            torch.FloatTensor).to(device)  # [N, 320, 320]
        alpha_label = alpha_label.unsqueeze(1)
        # alpha_label = alpha_label.reshape((-1, 2, im_size * im_size))  # [N, 320*320]

        # Forward prop.
        alpha_out = model(img)  # [N, 3, 320, 320]
        # alpha_out = alpha_out.reshape((-1, 1, im_size * im_size))  # [N, 320*320]

        # Calculate loss
        # loss = criterion(alpha_out, alpha_label)
        loss = alpha_prediction_loss(alpha_out, alpha_label)

        # Back prop.
        optimizer.zero_grad()
        loss.backward()

        # Clip gradients
        clip_gradient(optimizer, grad_clip)

        # Update weights
        optimizer.step()

        # Keep track of metrics
        losses.update(loss.item())

        # Print status

        if i % print_freq == 0:
            status = 'Epoch: [{0}][{1}/{2}]\t' \
                     'Loss {loss.val:.4f} ({loss.avg:.4f})\t'.format(
                         epoch, i, len(train_loader), loss=losses)
            logger.info(status)
    writer.add_scalar('Train_Loss', losses.avg, epoch)
    writer.add_scalar('Learning_Rate', get_learning_rate(optimizer), epoch)
    save_checkpoint(epoch, 0, model, optimizer, losses.avg, False)
    return losses.avg

# def train(epoch, total_epoch, loader, model, optimizer, log_interval=1):
#     train_losses = []
#     train_counter = []
#     model.to(device).train()
#     print('Train Epoch {} of {}'.format(epoch, total_epoch))
#     t = tqdm(loader)
#     for batch_idx, (image, target) in enumerate(t):
#         image = image.to(device)
#         target = target.to(device)
#         optimizer.zero_grad()
#         output = model(image)
#         loss = F.nll_loss(output, target)
#         loss.backward()
#         optimizer.step()
#         if batch_idx % log_interval == 0:
#             train_losses.append(loss.item())
#             t.set_postfix({'Loss': sum(train_losses)/len(train_losses)})
#             train_counter.append(batch_idx*64 + (epoch + 1)
#                                  * len(train_loader.dataset))
#     torch.save(model.state_dict(), 'result/model.pth')
#     torch.save(optimizer.state_dict(), 'result/optimizer.pth')

# def test(loader, model):
#     model.to(device).eval()
#     test_loss = 0
#     test_losses = []
#     correct = 0
#     t = tqdm(loader)
#     with torch.no_grad():
#         for image, target in t:
#             image = image.to(device)
#             target = target.to(device)
#             output = model(image)
#             test_loss += F.nll_loss(output, target, reduction='sum').item()
#             pred = output.data.max(1, keepdim=True)[1]
#             correct += pred.eq(target.data.view_as(pred)).sum()
#         test_loss /= len(test_loader.dataset)
#         test_losses.append(test_loss)
#         print('\nTest set: Avg. loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
#             test_loss, correct, len(test_loader.dataset),
#             100. * correct / len(test_loader.dataset)))


if __name__ == '__main__':
    global args
    args = parse_args()
    checkpoint = args.checkpoint
    global writer
    writer = SummaryWriter(logdir=args.logdir)
    global start_epoch
    start_epoch = args.start_epoch
    if checkpoint is None:
        torch.random.manual_seed(7)
        torch.cuda.manual_seed(7)
        np.random.seed(7)
        model = Model()
        optimizer = torch.optim.Adam(model.parameters())
    else:
        checkpoint = torch.load(checkpoint)
        
        epochs_since_improvement = checkpoint['epochs_since_improvement']
        optimizer = checkpoint['optimizer_state_dict']
        model_state_dict = checkpoint['model_state_dict']
        model = Model()
        model.load_state_dict(model_state_dict)
        if 'epoch' in checkpoint:
            start_epoch = checkpoint['epoch'] + 1
        else:
            start_epoch = 1
        if 'torch_seed' in checkpoint:
            torch.random.set_rng_state(checkpoint['torch_seed'])
        else:
            torch.random.manual_seed(7)
        if 'torch_cuda_seed' in checkpoint:
            torch.cuda.set_rng_state(checkpoint['torch_cuda_seed'])
        else:
            torch.cuda.manual_seed(7)
        if 'np_seed' in checkpoint:
            np.random.set_state(checkpoint['np_seed'])
        else:
            np.random.seed(7)
    model = model.to(device)
    summary(model, (3, 320, 320), depth=6)
    train_loader = DataLoader(HADataset('train'), batch_size=8, shuffle=True)
    # optimizer = optim.Adam(model.parameters())
    total_training_time = 0
    n_epochs = args.end_epoch
    logger = get_logger()
    for epoch in range(start_epoch, n_epochs + 1):
        start = time()
        train(train_loader, model, optimizer, epoch, logger)
        end = time()
        print('\nTraning process takes {} seconds'.format(end - start))
        total_training_time += end - start
        # test(test_loader, model)
    # print('Total traning process takes {} seconds'.format(total_training_time))

# if __name__ == '__main__':
#     model = Model()
#     summary(model, (3, 320, 320), depth=4)
