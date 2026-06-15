import numpy as np
import cv2

class FFTProcessor:
    """
    Mathematical Lattice Suppression Engine.
    Uses Fast Fourier Transforms (FFT) to convert atomic-resolution HR-STEM 
    images into the frequency domain, mathematically masks out high-frequency 
    periodic atomic lattice planes, and returns the suppressed spatial image.
    """
    def __init__(self, low_pass_radius=50):
        # Radius of the central low-frequency region to preserve.
        # Everything outside this radius (high frequencies like lattice fringes) will be deleted.
        self.low_pass_radius = low_pass_radius

    def suppress_lattice(self, image: np.ndarray) -> np.ndarray:
        """
        Applies a 2D FFT, masks out high frequencies, and returns 
        the spatial image with the atomic lattice suppressed.
        """
        # Ensure grayscale for FFT
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. Forward FFT: Transform to frequency domain
        # Use float32 to prevent precision loss
        f_transform = np.fft.fft2(np.float32(gray))
        
        # 2. Shift the zero-frequency component to the center of the spectrum
        f_shift = np.fft.fftshift(f_transform)

        # 3. Create the mathematical low-pass mask
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2
        
        # Create a mask initialized to zero (blocks all frequencies)
        mask = np.zeros((rows, cols), np.uint8)
        
        # Draw a solid white circle at the center (preserves low frequencies)
        cv2.circle(mask, (ccol, crow), self.low_pass_radius, 1, thickness=-1)

        # 4. Apply the mask to the frequency spectrum
        # Multiplying the complex array by the 0/1 mask mathematically deletes the lattice frequencies
        f_shift_filtered = f_shift * mask

        # 5. Inverse FFT: Transform back to spatial domain
        f_ishift = np.fft.ifftshift(f_shift_filtered)
        img_back = np.fft.ifft2(f_ishift)
        
        # Take the absolute value to get the real pixel intensities
        img_back = np.abs(img_back)

        # 6. Normalize back to standard 8-bit image for OpenCV processing
        img_normalized = cv2.normalize(img_back, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        return img_normalized

if __name__ == "__main__":
    print("FFTProcessor module loaded. Ready to suppress atomic lattice fringes.")
