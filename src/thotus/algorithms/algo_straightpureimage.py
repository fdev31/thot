from .algo_pureimage import compute as pure_compute

def compute(img, img_g, ref, ref_g, laser_nr, mask=None):
    return pure_compute(img, img_g, ref, ref_g, laser_nr=laser_nr, threshold=20, use_ransac=True, mask=mask)

