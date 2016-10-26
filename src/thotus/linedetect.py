from __future__ import print_function

BBOX_MIN = 300
BBOX_MAX = 2000

import math

import cv2
import numpy as np
import scipy.ndimage

from thotus.ransac import ransac, sgf

METHOD = 'sgf' # refinement method: sgf, ransac or None

# thanks stackoverflow for those two functions !

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

class LineMaker:
    points = None
    def from_lineimage2(self, img, laser_nr=0):
        # Do Canny then
        # find "couples", average the values
        # do an average of all "y" values, call it avg
        # loop again:
        #  for each line, take the option nearest from "avg"
        # OR?
        #  for each line, take the option nearest from previous, take avg for the first
        return

    def from_simpleline(self, img, laser_nr=0):
        idx = 0 if laser_nr == 0 else -1
        u = []
        v = []
#        img = auto_canny(img)
#        img = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,11,2)
#        img = cv2.blur(img, (5, 5))
        img = cv2.Sobel(img, cv2.CV_16S, 1, 0, ksize=3)
#        kernel = np.ones((5, 3),np.uint8)
#        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
#        img = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,11,2)

#        line_map = auto_canny(img)
#        cv2.imshow('plop', img)
        maximums = np.amax(img, axis=1)
        for n in range(img.shape[0]):
#            if n < img.shape[0]*0.6:
#                continue
            r = np.where(img[n] == maximums[n])[0]
            if r.size == 1:
                v.append(n)
                u.append(r[0])
            else:
                v.append(n)
                if laser_nr == 0:
                    u.append(r[0])
                else:
                    u.append(r[-1])
                    '''
                # detect islands
                prev = -1
                cur_c = []
                thres = 5
                all_chunks = []
                for cc in r:
                    if cc > prev + thres:
                        if cur_c:
                            all_chunks.append(cur_c.copy())
                            cur_c.clear()
                    cur_c.append(cc)
                    prev = cc
                if cur_c:
                    all_chunks.append(cur_c)
                for chunk in all_chunks:
                    v.append(n)
                    u.append( np.average(chunk) )
                    '''
        if u:
            self.points = (np.array(u),np.array(v))

            # TODO: do this for laser detection
#            self.points = (ransac( self.points[0], self.points[1]), self.points[1])

#            if METHOD == 'ransac':
#                x = ransac( self.points[0], self.points[1])
#            elif METHOD == 'sgf':
#                s = img.sum(axis=1)
#                x = sgf( self.points[0], s )

            return compute_line_image(self.points, img)
        return img

    def from_straightpureimage(self, img, laser_nr):
        return self.from_pureimage(img, laser_nr, 30, use_ransac=True, prune_top=int(img.shape[0]/2.8))

    def from_pureimage(self, img, laser_nr, threshold=40, use_ransac=False, prune_top=0):
        x = []
        y = []
        img = cv2.blur(img, (5, 5))

#        vals = [np.max(img[n]) for n in samples]
#        peak = np.max(vals)
#        threshold = peak/5

        bound = 0 if laser_nr == 0 else -1
        cur_chunk = []
        for n in range(prune_top, img.shape[0]):
            max_val = np.max(img[n])
            if max_val < threshold:
                continue
#            scipy.signal.find_peaks_cwt(img[n],
            peaks = np.where(img[n] == max_val)[0]
            y.append(n)
            x.append(peaks[bound])
            '''
            oldidx = -10
            if peaks.size:
                for idx in peaks:
#                    if idx > 900: # skip some lines
#                        continue
                    if oldidx + 5 >= idx:
                        cur_chunk.append(idx)
                    else:
                        if cur_chunk:
                            y.append(n)
                            x.append(np.max(img[n][cur_chunk]))
                        cur_chunk.clear()
                    oldidx = idx

                if len(cur_chunk) > 2:
                    y.append(n)
                    x.append(int(0.5 + np.average(cur_chunk)))
#            y.extend(n for _ in range(len(peaks)))
#            x.extend(peaks)
            '''

        y = np.array(y)
        x = np.array(x)

        if use_ransac:  # line calibration
#            s = img.sum(axis=1)
#            x = (self.calibration_data.weight_matrix * img).sum(axis=1)[y]/s[y]
            x = ransac( x, y )

#        if METHOD == 'ransac':
#            x = ransac( x, y )
#        elif METHOD == 'sgf':
#            s = img.sum(axis=1)
#            x = sgf( x, s )
        self.points = (x, y)
        if self.points:
            return compute_line_image(self.points, img)
        else:
            return img

    def from_lineimage(self, img, laser_nr=0):
        idx = 0 if laser_nr == 0 else -1
        u = []
        v = []
        line_map = cv2.Canny(img,50,200)
        for n in range(line_map.shape[0]):
            r = np.where(line_map[n] == 255)[0]
            if r.size > 0:
                #TODO: if they are too far from previous, discard them
#                if r.size > 1:
                    # TODO
                    # re-compute points, merging couples and trying to follow the "top" line
                    # if the sequence is not a "couple" (255, ...., 255)
                    # then try to match the top move
#                    pass

#                v.append(n)
#                u.append(r[idx])
                for p in r:
                    v.append(n)
                    u.append(p)
        if u:
            self.points = (np.array(u),np.array(v))

            if METHOD == 'ransac':
                x = ransac( self.points[0], self.points[1])
            elif METHOD == 'sgf':
                s = img.sum(axis=1)
                x = sgf( self.points[0], s )

            return compute_line_image(self.points, img)
        return img

    def from_image(self, img, laser_nr):
        point2d = find_lines(img)

        self.points = point2d
        if point2d:
            return compute_line_image(point2d, img)

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

