
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


