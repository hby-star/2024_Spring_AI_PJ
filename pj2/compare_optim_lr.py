# Importing Libraries
import os
import random
import sys

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torchsummary import summary
from torchvision import datasets
from torchvision import transforms
from tqdm import tqdm


# Define the model, here we take resnet-18 as an example

class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock, self).__init__()

        DROPOUT = 0.1

        self.conv1 = nn.Conv2d(
            in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.dropout = nn.Dropout(DROPOUT)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.dropout = nn.Dropout(DROPOUT)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion * planes,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion * planes),
                nn.Dropout(DROPOUT)
            )

    def forward(self, x):
        out = F.relu(self.dropout(self.bn1(self.conv1(x))))
        out = self.dropout(self.bn2(self.conv2(out)))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(ResNet, self).__init__()
        self.in_planes = 64

        self.conv1 = nn.Conv2d(3, 64, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        self.linear = nn.Linear(512 * block.expansion, num_classes)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return F.log_softmax(out, dim=-1)


def design_model():
    return ResNet(BasicBlock, [2, 2, 2, 2])


# 训练代码

def model_training(model, device, train_dataloader, optimizer, train_acc, train_losses):
    model.train()
    pbar = tqdm(train_dataloader)
    correct = 0
    processed = 0
    running_loss = 0.0

    for batch_idx, (data, target) in enumerate(pbar):
        data, target = data.to(device), target.to(device)

        # TODO
        # 补全内容:optimizer的操作，获取模型输出，loss设计与计算，反向传播
        optimizer.zero_grad()
        y_pred = model(data)
        # 由于已经计算了log_softmax，所以这里使用nll_loss
        loss = F.nll_loss(y_pred, target)
        loss.backward()
        optimizer.step()

        train_losses.append(loss.item())
        pred = y_pred.argmax(dim=1, keepdim=True)
        correct += pred.eq(target.view_as(pred)).sum().item()
        processed += len(data)
        # print statistics
        running_loss += loss.item()
        pbar.set_description(desc=f'Loss={loss.item()} Batch_id={batch_idx} Accuracy={100 * correct / processed:0.2f}')
        train_acc.append(100 * correct / processed)


# 验证代码

def model_testing(model, device, test_dataloader, test_acc, test_losses, misclassified=[]):
    model.eval()
    test_loss = 0
    correct = 0

    with torch.no_grad():
        for index, (data, target) in enumerate(test_dataloader):
            data, target = data.to(device), target.to(device)

            # TODO
            # 补全内容:获取模型输出，loss计算
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction='sum').item()

            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()
    test_loss /= len(test_dataloader.dataset)
    test_losses.append(test_loss)

    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.2f}%)\n'.format(
        test_loss, correct, len(test_dataloader.dataset),
        100. * correct / len(test_dataloader.dataset)))

    test_acc.append(100. * correct / len(test_dataloader.dataset))


def main(optimAlg, optimLr):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(device)

    # prepare datasets and transforms
    train_transforms = transforms.Compose([

        # TODO,设计针对训练数据集的图像增强
        # https://pytorch.org/vision/0.9/transforms.html
        # 50%的概率对图像进行水平翻转
        torchvision.transforms.RandomHorizontalFlip(),
        # 随机旋转角度范围为-10到10度
        transforms.RandomRotation(10),
        # 随机裁剪图像，裁剪后的图像大小为原图像的0.9到1之间
        transforms.RandomResizedCrop(32, scale=(0.9, 1.0), ratio=(0.9, 1.1)),

        transforms.ToTensor(),  # comvert the image to tensor so that it can work with torch
        transforms.Normalize((0.491, 0.482, 0.446), (0.247, 0.243, 0.261))  # Normalize all the images
    ])
    test_transforms = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.491, 0.482, 0.446), (0.247, 0.243, 0.261))
    ])

    data_dir = './data'
    trainset = datasets.CIFAR10(data_dir, train=True, download=True, transform=train_transforms)
    testset = datasets.CIFAR10(data_dir, train=False, download=True, transform=test_transforms)

    trainloader = torch.utils.data.DataLoader(trainset, batch_size=512,
                                              shuffle=True, num_workers=4)
    testloader = torch.utils.data.DataLoader(testset, batch_size=512,
                                             shuffle=False, num_workers=4)

    # Importing Model and printing Summary,默认是ResNet-18
    # TODO,分析讨论其他的CNN网络设计

    model = design_model().to(device)
    summary(model, input_size=(3, 32, 32))

    # Training the model

    optimizer = None

    if optimAlg == 'SGD':
        optimizer = optim.SGD(model.parameters(), lr=optimLr, momentum=0.9)
    elif optimAlg == 'Adam':
        optimizer = optim.Adam(model.parameters(), lr=optimLr)
    elif optimAlg == 'RMSprop':
        optimizer = optim.RMSprop(model.parameters(), lr=optimLr)
    else:
        print("Error: Invalid optimizer algorithm")
        exit(1)


    scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.05, patience=2, threshold=0.0001,
                                  threshold_mode='rel', cooldown=0, min_lr=0, eps=1e-08, verbose=True)

    train_acc = []
    train_losses = []
    test_acc = []
    test_losses = []
    model_path = './checkpoints'
    os.makedirs(model_path, exist_ok=True)

    print(f'Running with Optimizer: {optimAlg}, Learning Rate: {optimLr}')

    EPOCHS = 40

    for i in range(EPOCHS):
        print(f'EPOCHS : {i}')
        model_training(model, device, trainloader, optimizer, train_acc, train_losses)
        scheduler.step(train_losses[-1])
        model_testing(model, device, testloader, test_acc, test_losses)

        # 保存模型权重
        torch.save(model.state_dict(), os.path.join(model_path, optimAlg+'_'+str(optimLr)+'_'+'model.pth'))

    return max(test_acc)


if __name__ == '__main__':
    optimAlg = ['SGD', 'Adam', 'RMSprop']
    optimLr = [0.005, 0.01, 0.05]
    log_file = open("result_all.log", "w")
    original_stdout = sys.stdout
    sys.stdout = log_file

    test_acc = {}

    for alg in optimAlg:
        for lr in optimLr:
            temp = main(alg, lr)
            print(f'Optimizer: {alg}, Learning Rate: {lr}, Test Accuracy: {temp:.2f}')
            test_acc[(alg, lr)] = temp

    # 使用三维柱状图展示不同优化器和学习率的测试精度
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Adjust x and y values to increase gap between bars
    x = np.array([0, 2, 4, 0, 2, 4, 0, 2, 4])
    y = np.array([0, 0, 0, 2, 2, 2, 4, 4, 4])

    z = np.zeros(9)
    dx = np.ones(9)
    dy = np.ones(9)
    dz = []
    for lr in optimLr:
        for alg in optimAlg:
            dz.append(test_acc[(alg, lr)])

    ax.bar3d(x, y, z, dx, dy, dz, color='lightskyblue')

    # Add text on top of each bar
    for xi, yi, zi in zip(x, y, dz):
        ax.text(xi, yi, zi, f"{zi:.2f}", color='darkred')

    ax.set_xticks([1, 3, 5])
    ax.set_xticklabels(optimAlg)
    ax.set_yticks([1, 3, 5])
    ax.set_yticklabels(optimLr)
    ax.set_xlabel('Optimizer')
    ax.set_ylabel('Learning Rate')
    ax.set_zlabel('Test Accuracy')

    plt.show()
    plt.savefig('result_all.png')

    sys.stdout = original_stdout
    log_file.close()
