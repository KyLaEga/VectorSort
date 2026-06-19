import numpy as np
from PIL import Image

class ImageHash:
    """
    Custom ImageHash implementation that is 100% compatible with the imagehash library's
    serialization, deserialization, and Hamming distance calculation.
    """
    def __init__(self, binary_array):
        self.hash = binary_array

    def __str__(self):
        arr = self.hash.flatten()
        bit_string = ''.join(str(b) for b in 1 * arr)
        width = int(np.ceil(len(bit_string) / 4))
        return '{:0>{width}x}'.format(int(bit_string, 2), width=width)

    def __repr__(self):
        return repr(self.hash)

    def __sub__(self, other):
        if other is None:
            raise TypeError('Other hash must not be None.')
        if self.hash.size != other.hash.size:
            raise TypeError('ImageHashes must be of the same shape.', self.hash.shape, other.hash.shape)
        return int(np.count_nonzero(self.hash.flatten() != other.hash.flatten()))

    def __eq__(self, other):
        if other is None:
            return False
        return np.array_equal(self.hash.flatten(), other.hash.flatten())

    def __ne__(self, other):
        if other is None:
            return False
        return not np.array_equal(self.hash.flatten(), other.hash.flatten())

    def __hash__(self):
        return sum([2**(i % 8) for i, v in enumerate(self.hash.flatten()) if v])

    def __len__(self):
        return self.hash.size


def hex_to_hash(hexstr):
    """
    Convert hex string back to ImageHash object.
    """
    hash_size = int(np.sqrt(len(hexstr) * 4))
    binary_array = '{:0>{width}b}'.format(int(hexstr, 16), width=hash_size * hash_size)
    bit_rows = [binary_array[i:i + hash_size] for i in range(0, len(binary_array), hash_size)]
    hash_array = np.array([[bool(int(d)) for d in row] for row in bit_rows])
    return ImageHash(hash_array)


def phash(image, hash_size=8, highfreq_factor=4):
    """
    Pure numpy implementation of 2D DCT-II perceptual hash (phash),
    matching imagehash.phash output exactly.
    """
    img_size = hash_size * highfreq_factor
    image = image.convert('L').resize((img_size, img_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(image, dtype=np.float64)
    
    # 2D DCT using precomputed matrix multiplication:
    # C_{k, n} = 2 * cos(pi * (2n+1) * k / (2N))
    N = img_size
    k = np.arange(N).reshape(N, 1)
    n = np.arange(N).reshape(1, N)
    C = 2 * np.cos(np.pi * (2 * n + 1) * k / (2 * N))
    
    # DCT along columns, then along rows
    dct_0 = C @ pixels
    dct = (C @ dct_0.T).T
    
    dctlowfreq = dct[:hash_size, :hash_size]
    med = np.median(dctlowfreq)
    diff = dctlowfreq > med
    return ImageHash(diff)
