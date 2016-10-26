from thotus.ransac import ransac, sgf

import numpy as np
import cv2

def find_nearest(array,value):
    return (np.abs(array-value)).argmin()

def find_subsequence(seq, subseq):
    target = np.dot(subseq, subseq)
    candidates = np.where(np.correlate(seq,
                                       subseq, mode='valid') == target)[0]
    # some of the candidates entries may be false positives, double check
    check = candidates[:, np.newaxis] + np.arange(len(subseq))
    mask = np.all((np.take(seq, check) == subseq), axis=-1)
    return candidates[mask]

def compute_line_image(points, image):
    if points is not None:
        u, v = points
        image = np.zeros_like(image)
        try:
            image[v.astype(int), np.around(u).astype(int) - 1] = 255
            image[v.astype(int), np.around(u).astype(int)] = 255
            image[v.astype(int), np.around(u).astype(int) + 1] = 255
        except IndexError:
            pass
        return image

def auto_canny(image, sigma=0.3):
	# compute the median of the single channel pixel intensities
	v = np.median(image)

	# apply automatic Canny edge detection using the computed median
	lower = int(max(0, (1.0 - sigma) * v))
	upper = int(min(255, (1.0 + sigma) * v))
	edged = cv2.Canny(image, lower, upper)

	# return the edged image
	return edged


def find_lines(img):
    x = []
    y = []

    samples = range(10, img.shape[0], 30)

    vals = [np.max(img[n]) for n in samples]
    peak = np.max(vals)
    threshold = peak/5

    def keep_best(line, threshold):
        bands = np.where( line > threshold)
        if bands[0].size:
            avg = np.average(line[bands])
            for offset in range(255):
                v = np.where( line > avg + offset)
                if v[0].size == 0:
                    return avg
                else:
                    avg = np.average(v)-1

    def reguess(new_ref, margin):
        shift = max(0, new_ref-margin)
        second_guess = img[n][int(shift+0.5): int(new_ref+margin+0.5)]
        second_best_move = np.max(second_guess)
        best = keep_best(second_guess, second_best_move/2)
        if best:
            return shift + best

    for n in range(img.shape[0]):
        if not BBOX_MIN < n < BBOX_MAX: # y bounding box
            continue
        val = keep_best(img[n], threshold)
        if val:
            if y and y[-1] + 5 >= n: # continuation of a line
                old_x = x[-1] # old vertical position
                old_y = y[-1] # old horizontal position
                if not (old_x- 10 <= val <= old_x + 10):
                    try:
                        g = reguess(old_x, 20)
                    except ValueError:
                        g = None
                    if g:
                        val = g
            elif val < 50:
                g = reguess(img.shape[1]/2, 300)
                if g:
                    val = g
            y.append(n)
            x.append(min(val, img.shape[1]-1))

    y = np.array(y)
    if METHOD == 'ransac':
        x = ransac( np.array(x), y )
    elif METHOD == 'sgf':
        s = img.sum(axis=1)
        x = sgf( np.array(x), s )
    return (x, y)


