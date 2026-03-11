"""Fix image sizing in the deck - preserve aspect ratios"""
from pptx.util import Inches
from PIL import Image
import os

IMG = os.path.join(os.path.dirname(__file__), '..', 'ip-filing', 'deck', 'images')

def get_fitted_dims(img_path, max_w_inches, max_h_inches):
    """Calculate dimensions that fit within max bounds while preserving aspect ratio"""
    im = Image.open(img_path)
    w, h = im.size
    ratio = w / h
    
    # Try fitting by width first
    fit_w = max_w_inches
    fit_h = fit_w / ratio
    
    if fit_h > max_h_inches:
        # Too tall, fit by height instead
        fit_h = max_h_inches
        fit_w = fit_h * ratio
    
    return fit_w, fit_h

# Test
for f in ['actualized-beings-library.jpg', 'genesis-forge-builder-new.jpg', 'ipad-colosseum-battles.jpg', 'ui-voice-orb.png']:
    path = os.path.join(IMG, f)
    if os.path.exists(path):
        w, h = get_fitted_dims(path, 8.4, 4.5)
        print(f'{f}: {w:.1f}" x {h:.1f}"')
