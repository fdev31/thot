from .algo_uncanny import compute as uncanny_compute
def compute(img, laser_nr):
    return uncanny_compute(img, laser_nr, use_ransac=True)
