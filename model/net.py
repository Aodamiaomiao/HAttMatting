import torch
import torch.nn as nn
import math
import cv2
import torch.nn.functional as F
from torchvision import transforms

data_transforms = {
    'train': transforms.Compose([
        transforms.ToPILImage(),
        transforms.ColorJitter(
            brightness=0.125, contrast=0.125, saturation=0.125),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]),
    'valid': transforms.Compose([
        # transforms.ToPILImage(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
}

class VGG16(nn.Module):
    def __init__(self):
        super(VGG16, self).__init__()
        
        self.conv1_1 = nn.Conv2d(4, 64, kernel_size=3,stride = 1, padding=1,bias=True)
        self.conv1_2 = nn.Conv2d(64, 64, kernel_size=3,stride = 1, padding=1,bias=True)
        self.conv2_1 = nn.Conv2d(64, 128, kernel_size=3, padding=1,bias=True)
        self.conv2_2 = nn.Conv2d(128, 128, kernel_size=3, padding=1,bias=True)
        self.conv3_1 = nn.Conv2d(128, 256, kernel_size=3, padding=1,bias=True)
        self.conv3_2 = nn.Conv2d(256, 256, kernel_size=3, padding=1,bias=True)
        self.conv3_3 = nn.Conv2d(256, 256, kernel_size=3, padding=1,bias=True)
        self.conv4_1 = nn.Conv2d(256, 512, kernel_size=3, padding=1,bias=True)
        self.conv4_2 = nn.Conv2d(512, 512, kernel_size=3, padding=1,bias=True)
        self.conv4_3 = nn.Conv2d(512, 512, kernel_size=3, padding=1,bias=True)
        self.conv5_1 = nn.Conv2d(512, 512, kernel_size=3, padding=1,bias=True)
        self.conv5_2 = nn.Conv2d(512, 512, kernel_size=3, padding=1,bias=True)
        self.conv5_3 = nn.Conv2d(512, 512, kernel_size=3, padding=1,bias=True)

        
        self.conv6_1 = nn.Conv2d(512, 512, kernel_size=3, padding=1,bias=True)
        
        self.deconv6_1 = nn.Conv2d(512, 512, kernel_size=1,bias=True)
        self.deconv5_1 = nn.Conv2d(512, 512, kernel_size=5, padding=2,bias=True)
        self.deconv4_1 = nn.Conv2d(512, 256, kernel_size=5, padding=2,bias=True)
        self.deconv3_1 = nn.Conv2d(256, 128, kernel_size=5, padding=2,bias=True)
        self.deconv2_1 = nn.Conv2d(128, 64, kernel_size=5, padding=2,bias=True)
        self.deconv1_1 = nn.Conv2d(64, 64, kernel_size=5, padding=2,bias=True)
        
        self.deconv1 = nn.Conv2d(64, 1, kernel_size=5, padding=2,bias=True)
        
        self.refine_conv1 = nn.Conv2d(4, 64, kernel_size=3, padding=1, bias=True)
        self.refine_conv2 = nn.Conv2d(64, 64, kernel_size=3, padding=1, bias=True)
        self.refine_conv3 = nn.Conv2d(64, 64, kernel_size=3, padding=1, bias=True)
        self.refine_pred = nn.Conv2d(64, 1, kernel_size=3, padding=1, bias=True)
        
    def forward(self, x, trimap):
        trimap = trimap.argmax(dim=1, keepdim=True)
        trimap[trimap == 0] = 0
        trimap[trimap == 1] = 128
        trimap[trimap == 2] = 255
        trimap = trimap / 255.0

        x = torch.cat((x, trimap), dim=1)

        # Stage 1
        x11 = F.relu(self.conv1_1(x))
        x12 = F.relu(self.conv1_2(x11))
        x1p, id1 = F.max_pool2d(x12,kernel_size=(2,2), stride=(2,2),return_indices=True)

        # Stage 2
        x21 = F.relu(self.conv2_1(x1p))
        x22 = F.relu(self.conv2_2(x21))
        x2p, id2 = F.max_pool2d(x22,kernel_size=(2,2), stride=(2,2),return_indices=True)

        # Stage 3
        x31 = F.relu(self.conv3_1(x2p))
        x32 = F.relu(self.conv3_2(x31))
        x33 = F.relu(self.conv3_3(x32))
        x3p, id3 = F.max_pool2d(x33,kernel_size=(2,2), stride=(2,2),return_indices=True)

        # Stage 4
        x41 = F.relu(self.conv4_1(x3p))
        x42 = F.relu(self.conv4_2(x41))
        x43 = F.relu(self.conv4_3(x42))
        x4p, id4 = F.max_pool2d(x43,kernel_size=(2,2), stride=(2,2),return_indices=True)

        # Stage 5
        x51 = F.relu(self.conv5_1(x4p))
        x52 = F.relu(self.conv5_2(x51))
        x53 = F.relu(self.conv5_3(x52))
        x5p, id5 = F.max_pool2d(x53,kernel_size=(2,2), stride=(2,2),return_indices=True)

        # Stage 6
        x61 = F.relu(self.conv6_1(x5p))

        # Stage 6d
        x61d = F.relu(self.deconv6_1(x61))

        # Stage 5d
        x5d = F.max_unpool2d(x61d,id5, kernel_size=2, stride=2)
        x5d = x5d + x53
        x51d = F.relu(self.deconv5_1(x5d))

        # Stage 4d
        x4d = F.max_unpool2d(x51d, id4, kernel_size=2, stride=2)
        x4d = x4d + x43
        x41d = F.relu(self.deconv4_1(x4d))

        # Stage 3d
        x3d = F.max_unpool2d(x41d, id3, kernel_size=2, stride=2)
        x3d = x3d + x33
        x31d = F.relu(self.deconv3_1(x3d))

        # Stage 2d
        x2d = F.max_unpool2d(x31d, id2, kernel_size=2, stride=2)
        x2d = x2d + x22
        x21d = F.relu(self.deconv2_1(x2d))

        # Stage 1d
        x1d = F.max_unpool2d(x21d, id1, kernel_size=2, stride=2)
        x1d = x1d + x12
        x12d = F.relu(self.deconv1_1(x1d))

        raw_alpha = self.deconv1(x12d)
        pred_mattes = F.sigmoid(raw_alpha)

        # Stage2 refine conv1
        refine0 = torch.cat((x[:, :3, :, :], pred_mattes),  1)
        refine1 = F.relu(self.refine_conv1(refine0))
        refine2 = F.relu(self.refine_conv2(refine1))
        refine3 = F.relu(self.refine_conv3(refine2))
        # Should add sigmoid?
        # sigmoid lead to refine result all converge to 0... 
        #pred_refine = F.sigmoid(self.refine_pred(refine3))
        pred_refine = self.refine_pred(refine3)

        pred_alpha = F.sigmoid(raw_alpha + pred_refine)

        #print(pred_mattes.mean(), pred_alpha.mean(), pred_refine.sum())

        return pred_alpha

    def transform(self, x):
        x = data_transforms['valid'](x)
        x = x.unsqueeze(0)
        return x

    def migrate(self, state_dict):
        with torch.no_grad():
            for i, (name, p) in enumerate(self.state_dict().items()):
                if name in state_dict:
                    if p.data.shape == state_dict[name].shape:
                        print(i, name)
                        p.copy_(state_dict[name])