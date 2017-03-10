from PIL import Image, ImageFont, ImageDraw
from tesserocr import PyTessBaseAPI, RIL, PSM, Orientation
import time
import numpy as np
import cv2
import math
import scipy.ndimage
import threading
from multiprocessing import Process, Queue
import sys


THRESHOLD_WHITE = 200
WEIGHT = 5


def measure_timing(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print('time: ', time.time() - start)
        return result
    return wrapper


def rotate_to_upright(image):
    with PyTessBaseAPI(psm=PSM.OSD_ONLY) as api:
        api.SetImage(image)

        os = api.DetectOS()
        if os:
            if os['orientation'] == Orientation.PAGE_RIGHT:
                image = image.rotate(90, expand=True)

            if os['orientation'] == Orientation.PAGE_LEFT:
                image = image.rotate(270, expand=True)

            if os['orientation'] == Orientation.PAGE_DOWN:
                image = image.rotate(180, expand=True)

    return image


def unit_vector(vector):
    if np.linalg.norm(vector) == 0:
        return None
    return vector / np.linalg.norm(vector)


def calc_angle(line):
    x1, y1, x2, y2 = line
    y1 = -y1
    y2 = -y2
    v1 = unit_vector(np.array([x2 - x1, y2 - y1]))
    v2 = np.array([0, 1])
    if v1 is None:
        return 0
    return np.arccos(np.clip(np.dot(v1, v2), -1.0, 1.0)) / np.pi * 180


def find_best_angle(image):
    best_angle = 0
    max_variance = 0

    for angle in np.linspace(-2.0, 2.0, num=32):
        rotated = scipy.ndimage.rotate(image, angle)
        variance = np.var(np.sum(rotated, axis=1))

        if variance > max_variance:
            best_angle = angle
            max_variance = variance

    return best_angle


def find_best_angle_threaded(image):
    variances = []
    threads = []

    for angle in np.linspace(-2.0, 2.0, num=32):
        thread = threading.Thread(
            target=cal_img_variance,
            args=(image, angle, variances)
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    best_angle = 0
    max_variance = 0
    for angle, variance in variances:
        if variance > max_variance:
            max_variance = variance
            best_angle = angle

    return best_angle


def cal_img_variance(image, angle, variances):
    rotated = scipy.ndimage.rotate(image, angle)
    variances.append((angle, np.var(np.sum(rotated, axis=1))))


def deskew_image(text_area):
    image, x, y = text_area

    if image.size == 0:
        return image

    height, width = image.shape
    cropped_height = width // 5

    angles_up = []
    angles_down = []
    start = 0
    while start < height:
        end = start + cropped_height
        if end > height:
            end = height
        img_segment = image[start:end]
        lines = cv2.HoughLinesP(
            img_segment,
            1,
            np.pi / 180,
            100,
            minLineLength=width // 3,
            maxLineGap=100
        )

        start = end

        if lines is None:
            continue

        for line in lines:
            angle = calc_angle(line[0])
            if angle > 180 / 4 and angle < 90:
                angles_up.append(angle)
            if angle >= 90 and angle < 180 * (3 / 4):
                angles_down.append(angle)

    rotate_angle = 0
    if len(angles_up) > 0.8 * len(angles_down):
        rotate_angle = np.mean(angles_up)
    elif len(angles_down) > 0.8 * len(angles_up):
        rotate_angle = np.mean(angles_down)
    elif len(angles_up) == 0 and len(angles_down) == 0:
        rotate_angle = 90
    else:
        rotate_angle = np.mean(
            np.append(
                np.array(angles_up),
                np.array(angles_down)
            )
        )

    rotated = 0
    rotate_angle = rotate_angle - 90
    if math.fabs(rotate_angle) > 2:
        image = scipy.ndimage.rotate(image, rotate_angle)
        rotated += rotate_angle

        ih, iw = image.shape
        x = x - (iw - width) / 2
        y = y - (ih - height) / 2
        height = ih
        width = iw

    best_angle = find_best_angle_threaded(image)

    image = scipy.ndimage.rotate(image, best_angle)
    rotated += best_angle

    ih, iw = image.shape
    x = x - (iw - width) / 2
    y = y - (ih - height) / 2
    height = ih
    width = iw

    return (image, np.int0(x), np.int0(y), rotated)


def rotate_point(p, rotation, origin=(0, 0)):
    px, py = p
    ox, oy = origin
    rotation_in_rad = np.deg2rad(rotation)
    rotated_x = np.cos(rotation_in_rad) * (px - ox) -   \
        np.sin(rotation_in_rad) * (py - oy) + ox
    rotated_y = np.sin(rotation_in_rad) * (px - ox) +   \
        np.cos(rotation_in_rad) * (py - oy) + oy

    return np.array([np.int0(np.round(rotated_x)),
                     np.int0(np.round(rotated_y))])


def is_within(mask1, mask2):
    """returns True if mask1 is completely within mask2
    """
    result = cv2.bitwise_and(mask1, mask2)
    return np.array_equal(result, mask1)


def create_mask(shape, contour):
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.drawContours(mask, [contour], 0, 255, -1)
    return mask


def extract_text_areas(image, original):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 3))
    dilation = cv2.dilate(image, kernel, iterations=8)

    img, cnts, __ = cv2.findContours(
        dilation,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE
    )

    cnt_areas = [(cnt, create_mask(image.shape, cnt))
                 for cnt in cnts]
    cnt_areas.sort(key=lambda x: cv2.contourArea(x[0]), reverse=True)

    superset_areas = [cnt_areas[0]]
    for i in range(1, len(cnt_areas)):
        cnt_area = cnt_areas[i]
        area1_is_within = False
        for __, superset_mask in superset_areas:
            if is_within(cnt_area[1], superset_mask):
                area1_is_within = True
                break
        if not area1_is_within:
            superset_areas.append(cnt_area)

    text_areas = []
    for cnt, mask in superset_areas:
        x, y, w, h = cv2.boundingRect(cnt)

        if w < 50 or h < 50:
            continue

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        crop = binarise_image_otsu(original[y: y + h, x: x + w])
        masked_image = cv2.bitwise_and(crop, mask[y: y + h, x: x + w])
        text_areas.append((masked_image, x, y))

    return text_areas


def binarise_image(image):
    image = gray_and_blur(image)
    image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 13, 2)
    image = cv2.bitwise_not(image)
    kernel = np.ones((5, 5), np.uint8)
    image = cv2.erode(image, kernel, iterations=1)
    image = cv2.dilate(image, kernel, iterations=1)

    return image


def binarise_image_otsu(image):
    image = gray_and_blur(image)
    __, img = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return cv2.bitwise_not(img)


def gray_and_blur(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.GaussianBlur(image, (5, 5), 0)

    return image


def evaluate_text_area(text_area, results):
    if text_area[0].size == 0:
        return

    text, tx, ty, angle = deskew_image(text_area)
    image = cv2.bitwise_not(text)

    image = Image.fromarray(image)

    with PyTessBaseAPI(psm=PSM.SINGLE_BLOCK, lang='eng') as api:
        api.SetImage(image)
        boxes = api.GetComponentImages(RIL.TEXTLINE, True)
        for im, box, __, __ in boxes:
            x = box['x']
            y = box['y']
            w = box['w']
            h = box['h']

            api.SetRectangle(x, y, w, h)
            ocrResult = api.GetUTF8Text()

            iw, ih = image.size
            origin = (iw / 2, ih / 2)

            detected_area = np.array([
                rotate_point((x, y), angle, origin=origin),
                rotate_point((x, y + h), angle, origin=origin),
                rotate_point((x + w, y + h), angle, origin=origin),
                rotate_point((x + w, y), angle, origin=origin),
            ])

            detected_area = np.add(detected_area, np.array([tx, ty]))
            result = (ocrResult, detected_area)
            results.put(result)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Incorrect number of arguments '{}' given.".format(len(sys.argv) - 1))
        print("Usage: python main.py <file_path>")
        sys.exit()

    img_path = sys.argv[1]
    image = Image.open(img_path)
    image = rotate_to_upright(image)

    with PyTessBaseAPI(psm=PSM.SINGLE_BLOCK, lang='eng') as api:
        api.SetImage(image)
        original = np.array(image)

        binarised = binarise_image(original)

        text_areas = extract_text_areas(binarised, original)

        results = Queue()
        processes = []
        for text_area in text_areas:
            process = Process(
                target=evaluate_text_area,
                args=(text_area, results)
            )
            process.start()
            processes.append(process)

        for process in processes:
            process.join()

        while not results.empty():
            text, box = results.get()
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype('DejaVuSans-Bold.ttf', 32)
            points = list(map(tuple, box))
            points.append(tuple(box[0]))
            draw.line(points, width=5, fill=(0, 255, 0))
            draw.text(points[0], text, (255, 0, 0), font=font)

        image.save('result.jpg')
