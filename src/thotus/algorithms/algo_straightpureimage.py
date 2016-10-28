from .algo_pureimage import compute as pure_compute

def compute(img, laser_nr):
    return pure_compute(img, laser_nr, 0, use_ransac=True)

