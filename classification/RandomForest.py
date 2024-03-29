from sklearn.ensemble import RandomForestClassifier
import osgeo
from osgeo import gdal
from osgeo import osr
from osgeo import ogr
import numpy
import psutil
import os
import sys
import math
from .TrainByRandomForest import createClassifier
#import TrainByRandomForest as tbrf


filepath = "C:\\Users\\user\\Desktop\\MyProject\\1.tif"


def get_FileSize(filePath):
    fsize = os.path.getsize(filePath)
    fsize = fsize / float(1024 * 1024)

    return round(fsize, 2)


def memory_usage():
    mem_available = psutil.virtual_memory().available
    mem_process = psutil.Process(os.getpid()).memory_info().rss
    return round(mem_process / 1024 / 1024, 2), round(mem_available / 1024 / 1024, 2)


def checkMemory(size=500):
    p, a = memory_usage()
    if a < size:
        print("内存不足：", a)
        os._exit(-2)


def RandomForestClassification(ClassifyRaster, TrainRaster, TrainShp, outfile, blockSize=0, treenum=100, max_depth=10):
    gdal.AllRegister()
    rds = gdal.Open(ClassifyRaster)
    transform = (rds.GetGeoTransform())
    lX = transform[0]  # 左上角点
    lY = transform[3]
    rX = transform[1]  # 分辨率
    rY = transform[5]
    width = rds.RasterXSize
    height = rds.RasterYSize
    bX = lX + rX * width  # 右下角点
    bY = lY + rY * height
    BandsCount = rds.RasterCount
    # clf = tbrf.createClassifier(TrainRaster, TrainShp)
    clf = createClassifier(TrainRaster, TrainShp)
    Z = list()
    fixX = list()
    if blockSize == 0:
        p, a = memory_usage()
        pv = 0.6 / 10000
        checkMemory(2000)  # 内存小于2GB，不在计算
        bl = (a - 2000) / pv / height / BandsCount
        blockSize = math.ceil(height / bl)
        if blockSize < 1: blockSize = 1
        if blockSize > 1: blockSize += 5
    if blockSize != 1:
        blockHeight = 0
        modHeight = 0
        modHeight = height % blockSize

        if modHeight == 0:
            blockHeight = int(height / blockSize)

        else:
            blockHeight = int(height / blockSize)
        print(f"分块大小{width}*{blockHeight}")
        for bs in range(blockSize):
            print(f"计算块{bs + 1}/{blockSize}")
            checkMemory(500)
            arr = rds.ReadAsArray(0, bs * blockHeight, width, blockHeight)

            for i in range(blockHeight):
                print(f"分块：{bs + 1}/{blockSize}添加分类数据{round((i + 1) * 100 / blockHeight, 4)}%")
                for k in range(width):
                    tem = list()
                    for bc in range(BandsCount):
                        tem.append(int(arr[bc][i][k]))
                    fixX.append(tem)
            print(f"分块：{bs + 1}/{blockSize}计算分类结果……")
            checkMemory(800)
            z = clf.predict(fixX)
            Z.extend(z)
            fixX = list()
            arr = None
        print(f"计算余数：{width}*{modHeight}")
        checkMemory(500)
        arr = rds.ReadAsArray(0, blockSize * blockHeight, width, modHeight)
        if modHeight > 0:
            for i in range(modHeight):
                print(f"余块：添加分类数据{round((i + 1) * 100 / modHeight, 4)}%")
                for k in range(width):
                    tem = list()
                    for bc in range(BandsCount):
                        tem.append(int(arr[bc][i][k]))
                    fixX.append(tem)
            print("余块：计算分类结果……")
            checkMemory(500)
            z = clf.predict(fixX)
            Z.extend(z)
        Z = numpy.array(Z)
        # Z=Z.reshape(1,width*height)
        Z = Z.reshape(height, width)
        fixX = None
        arr = None


    else:
        checkMemory(1000)
        arr = rds.ReadAsArray(0, 0, width, height)

        for i in range(height):
            print(f"添加训练样本{round((i + 1) * 100 / height, 4)}%")
            for k in range(width):
                tem = list()
                for bc in range(BandsCount):
                    tem.append(int(arr[bc][i][k]))
                fixX.append(tem)
        arr = None
        print("计算分类结果……")
        Z = clf.predict(fixX)
        Z = numpy.array(Z)
        Z = Z.reshape(height, width)

    driver = gdal.GetDriverByName("GTiff")
    filepath, filename = os.path.split(outfile)
    short, ext = os.path.splitext(filename)
    try:
        print("如果输出文件已存在，将被覆盖")
        if os.path.exists(os.path.join(filepath, short + ".tif")): os.remove(os.path.join(filepath, short + ".tif"))
        if os.path.exists(os.path.join(filepath, short + ".tfw")): os.remove(os.path.join(filepath, short + ".tfw"))
        if os.path.exists(os.path.join(filepath, short + ".tif.aux.xml")): os.remove(
            os.path.join(filepath, short + ".tif.aux.xml"))
        if os.path.exists(os.path.join(filepath, short + ".tif.ovr")): os.remove(
            os.path.join(filepath, short + ".tif.ovr"))
    except Exception as e:
        print(e)
        os._exit(2)
    print("创建输出文件")
    out = driver.Create(outfile, width, height, 1, rds.GetRasterBand(1).DataType)
    out.SetGeoTransform(transform)
    out.SetProjection(rds.GetProjectionRef())
    print("写入数据……")
    out.GetRasterBand(1).WriteArray(Z)
    out.FlushCache()
    out = None
    print("计算完成")


def getPathRow(x, y, lX, lY, rX, rY):
    path = int((x - lX) / (rX))
    row = int(((y - lY) / rY))
    return path, row


def test():
    X = [[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4], [5, 5, 5]]
    Y = [1, 2, 3, 4, 2]

    clf = RandomForestClassifier(n_estimators=100)
    clf.fit(X, Y)

    Z = clf.predict([[5.25505156, 5.5652961, 5.17026121]])

    for z in Z:
        print(z)


def WriteOutputError(message, outpath="Record/Error.txt"):
    '''
记录错误消息
    '''
    path, file = os.path.split(outpath)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(outpath, "a+") as code:
        code.write(str(message))
        code.write("\n")
