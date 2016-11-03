from .algo_uncanny import compute as uncanny_compute
def compute(img, img_g, ref, ref_g, laser_nr, mask=None):
    return uncanny_compute(img,img_g, ref, ref_g, laser_nr=laser_nr, straight_lines=True, mask=mask)
