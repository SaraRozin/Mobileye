try:
    import os
    import json
    import glob
    import argparse
    import math
    import numpy as np
    from scipy import signal as sg
    from scipy.ndimage.filters import maximum_filter
    from skimage.feature import peak_local_max

    from PIL import Image

    import matplotlib.pyplot as plt
except ImportError:
    print("Need to fix the installation")
    raise

"""
:return the coordinates of the the suspicious lights.
"""


def find_tfl_lights(c_image, some_threshold):
    """
    Detect candidates for TFL lights. Use c_image, kwargs and you imagination to implement
    :param some_threshold: 
    :param c_image: The image itself as np.uint8, shape of (H, W, 3)
    :param kwargs: Whatever config you want to pass in here
    :return: 4-tuple of x_red, y_red, x_green, y_green
    """
    c_image = c_image.astype(float)

    x_red, y_red = find_lights3(c_image, 0)
    x_green, y_green = find_lights3(c_image, 1)

    # remove duplicates coordinates, between the red and green
    for i in range(len(x_red)):
        min_distance = 2000
        index = 0
        j = 0
        while j < len(x_green):
            distance = math.sqrt(((x_red[i] - x_green[j]) ** 2) + ((y_red[i] - y_green[j]) ** 2))
            if distance <= min_distance:
                min_distance = distance
                index = j
            j += 1
        if min_distance <= 10:
            x_green = x_green[:index] + x_green[index + 1:]
            y_green = y_green[:index] + y_green[index + 1:]

    return x_red, y_red, x_green, y_green


# Non-use function
# High-pass filter
def find_lights(c_image, color_num):
    c_image = c_image[:, :, color_num]
    kernel = [[-1 / 2025 for _ in range(45)] for _ in range(45)]
    kernel[22][22] = 2024 / 2025

    x_red, y_red = [], []
    convolved = sg.convolve(c_image, kernel, 'same')
    coordinates = peak_local_max(convolved, min_distance=10, num_peaks=10)
    for i in range(len(coordinates)):
        if convolved[coordinates[i][0]][coordinates[i][1]] > 150:
            x_red += [coordinates[i][1]]
            y_red += [coordinates[i][0]]
    return x_red, y_red


# Non-use function
# Make subtraction between two high-pass filters, one big and the second small.
def find_lights2(c_image, color_num):
    c_image = c_image[:, :, color_num]
    kernel = [[-1 / 2025 for _ in range(45)] for _ in range(45)]
    kernel[22][22] = 2024 / 2025
    convolved = sg.convolve(c_image, kernel, 'same')
    coordinates = peak_local_max(convolved, min_distance=10)
    big_light = []
    for i in range(len(coordinates)):
        if convolved[coordinates[i][0]][coordinates[i][1]] > 150:
            big_light.append((coordinates[i][1], coordinates[i][0]))

    kernel = [[-1 / 625 for _ in range(25)] for _ in range(25)]
    kernel[12][12] = 624 / 625
    convolved = sg.convolve(c_image, kernel, 'same')
    coordinates = peak_local_max(convolved, min_distance=10)
    small_light = []
    for i in range(len(coordinates)):
        if convolved[coordinates[i][0]][coordinates[i][1]] > 150:
            small_light.append((coordinates[i][1], coordinates[i][0]))

    for coordinate in small_light:
        min_distance = 2000
        index = 0
        for j in range(len(big_light)):
            if big_light[j] is not None:
                distance = math.sqrt(
                    ((coordinate[0] - big_light[j][0]) ** 2) + ((coordinate[1] - big_light[j][1]) ** 2))
                if distance <= min_distance:
                    min_distance = distance
                    index = j
        if min_distance <= 10:
            big_light[index] = None

    x_red, y_red = [], []
    for pair in big_light:
        if pair is not None:
            x_red.append(pair[0])
            y_red.append(pair[1])
    return x_red, y_red


# Find the lights using 2 drawn pictures in two sizes of traffic_lights as kernels.
def find_lights3(c_image, color_num):
    c_image = c_image[:, :, color_num]
    x_light, y_light = [], []
    x_light, y_light = get_coordinates(c_image, x_light, y_light, '../part1/traffic_lights.png')
    x_light, y_light = get_coordinates(c_image, x_light, y_light, '../part1/small_traffic_lights.png')

    return x_light, y_light


# Returns the coordinates of the suspicious lights
def get_coordinates(c_image, x_light, y_light, image):
    returned_x_light, returned_y_light = convolve_picture(c_image, image)
    x_light += returned_x_light
    y_light += returned_y_light
    return x_light, y_light


def convolve_picture(c_image, kernel):
    x_red, y_red = [], []
    im1 = Image.open(kernel).convert('L')
    kernel = np.stack((im1,) * 3, axis=-1)
    kernel = kernel[:, :, 0].astype(float)

    # Normalize kernel
    kernel = kernel - np.average(kernel)
    kernel = kernel / np.amax(kernel)

    # Make convolution on the image
    convolved = sg.convolve(c_image, kernel, 'same')

    # Get one point that is the maximum from each area
    coordinates = peak_local_max(convolved, min_distance=10, num_peaks=10)

    # Take only coordinates that meet a certain condition
    for i in range(len(coordinates)):
        if convolved[coordinates[i][0]][coordinates[i][1]] > np.amax(convolved) - 30000 and coordinates[i][0] > 20:
            x_red += [coordinates[i][1]]
            y_red += [coordinates[i][0]]
    return x_red, y_red


### GIVEN CODE TO TEST YOUR IMPLENTATION AND PLOT THE PICTURES
def show_image_and_gt(image, objs, fig_num=None):
    plt.figure(fig_num).clf()
    plt.imshow(image)
    labels = set()
    if objs is not None:
        for o in objs:
            poly = np.array(o['polygon'])[list(np.arange(len(o['polygon']))) + [0]]
            plt.plot(poly[:, 0], poly[:, 1], 'r', label=o['label'])
            labels.add(o['label'])
        if len(labels) > 1:
            plt.legend()


def test_find_tfl_lights(image_path, json_path=None, fig_num=None):
    """
    Run the attention code
    """
    image = np.array(Image.open(image_path))
    if json_path is None:
        objects = None
    else:
        gt_data = json.load(open(json_path))
        what = ['traffic light']
        objects = [o for o in gt_data['objects'] if o['label'] in what]
    show_image_and_gt(image, objects, fig_num)

    red_x, red_y, green_x, green_y = find_tfl_lights(image, some_threshold=42)
    plt.plot(red_x, red_y, 'ro', markersize=4)
    plt.plot(green_x, green_y, 'go', markersize=4)


def main(argv=None):
    """It's nice to have a standalone tester for the algorithm.
    Consider looping over some images from here, so you can manually exmine the results
    Keep this functionality even after you have all system running, because you sometime want to debug/improve a module
    :param argv: In case you want to programmatically run this"""

    parser = argparse.ArgumentParser("Test TFL attention mechanism")
    parser.add_argument('-i', '--image', type=str, help='Path to an image')
    parser.add_argument("-j", "--json", type=str, help="Path to json GT for comparison")
    parser.add_argument('-d', '--dir', type=str, help='Directory to scan images in')
    args = parser.parse_args(argv)
    # Path of the pictures directory
    default_base = './Data/test'

    if args.dir is None:
        args.dir = default_base
    flist = glob.glob(os.path.join(args.dir, '*_leftImg8bit.png'))

    for image in flist:
        json_fn = image.replace('_leftImg8bit.png', '_gtFine_polygons.json')

        if not os.path.exists(json_fn):
            json_fn = None
        test_find_tfl_lights(image, json_fn)

    if len(flist):
        print("You should now see some images, with the ground truth marked on them. Close all to quit.")
    else:
        print("Bad configuration?? Didn't find any picture to show")
    plt.show(block=True)


if __name__ == '__main__':
    main()
