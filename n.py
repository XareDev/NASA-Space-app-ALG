from PIL import Image
import os
import math
import xml.etree.ElementTree as ET 
import time

class DZIGenerator:
    """
    Pure Python DZI Generator using only Pillow
    Works on Windows without external dependencies
    """
    
    def __init__(self, image_path, output_name, tile_size=256, overlap=1, 
                 format='jpeg', quality=90):
        self.image_path = image_path
        self.output_name = output_name
        self.tile_size = tile_size
        self.overlap = overlap
        self.format = format.lower()
        self.quality = quality
        
        # Output paths
        self.dzi_file = f"{output_name}.dzi"
        self.tiles_dir = f"{output_name}_files"
        # max_level will be calculated after opening the image
        self.max_level = 0 
        
    def generate(self):
        """Main conversion function"""
        print("="*60)
        print("DZI GENERATOR - Pure Python (Windows Compatible)")
        print("="*60)
        
        start_time = time.time()
        
        # Open image
        print(f"\nOpening: {self.image_path}")
        try:
            img = Image.open(self.image_path)
        except Exception as e:
            print(f"Error opening image: {e}")
            return False
        
        width, height = img.size
        print(f"Image size: {width} x {height}")
        print(f"Mode: {img.mode}")
        
        # --- FIX 1: Image Mode Conversion ---
        # Ensure image is in a suitable mode for JPEG conversion (RGB or L)
        # Handle RGBA by compositing on a black background, suitable for astro images
        if img.mode not in ('RGB', 'RGBA', 'L'):
            print(f"Converting image from {img.mode} to RGB...")
            img = img.convert('RGB')
        elif img.mode == 'RGBA':
            print("Converting RGBA to RGB (compositing with black background)...")
            background = Image.new('RGB', img.size, (0, 0, 0)) # Use black for astro
            background.paste(img, mask=img.split()[3]) # Use alpha channel as mask
            img = background
        
        # --- FIX 2: Correct max_level calculation ---
        # Max level is the highest resolution level (original image)
        # Level 0 is the lowest resolution level (smallest image, typically 1x1)
        # This formula aligns with how OpenSeadragon and most DZI generators calculate levels.
        max_dimension = max(width, height)
        self.max_level = math.ceil(math.log2(max_dimension)) 
        
        print(f"Max zoom level (full resolution): {self.max_level}")
        print(f"Generating {self.max_level + 1} zoom levels (0 to {self.max_level})...")
        print(f"Tile size: {self.tile_size}x{self.tile_size}")
        print(f"Overlap: {self.overlap}px")
        
        # Create output directory
        os.makedirs(self.tiles_dir, exist_ok=True)
        
        # Generate all levels
        total_tiles = 0
        # Iterate from the lowest resolution (level 0) to the highest (self.max_level)
        for level in range(self.max_level + 1): 
            tiles_in_level = self._generate_level(img, level, width, height)
            total_tiles += tiles_in_level
        
        # Create DZI descriptor file
        self._create_dzi_descriptor(width, height)
        
        elapsed = time.time() - start_time
        print("\n" + "="*60)
        print(f"✓ CONVERSION COMPLETE!")
        print(f"  Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"  Total tiles: {total_tiles}")
        print(f"  DZI file: {self.dzi_file}")
        print(f"  Tiles directory: {self.tiles_dir}")
        print("="*60)
        
        return True
    
    def _generate_level(self, original_img, level, orig_width, orig_height):
        """Generate all tiles for a specific zoom level"""
        
        # Calculate dimensions for this level
        # Scale factor is 2^(MaxLevel - current_level)
        scale_factor = 2 ** (self.max_level - level)
        level_width = math.ceil(orig_width / scale_factor)
        level_height = math.ceil(orig_height / scale_factor)
        
        # Resize image for this level
        # If it's the highest level, use the original image directly
        # Otherwise, resize the original image for this level
        if level == self.max_level:
            level_img = original_img
        else:
            # Use LANCZOS for high-quality downsampling
            level_img = original_img.resize(
                (level_width, level_height),
                Image.Resampling.LANCZOS
            )
        
        # Calculate number of tiles required for this level's dimensions
        cols = math.ceil(level_width / self.tile_size)
        rows = math.ceil(level_height / self.tile_size)
        total_tiles_in_level = cols * rows
        
        print(f"\nLevel {level} ({level_width}x{level_height}): {cols}x{rows} tiles = {total_tiles_in_level} total")
        
        # Create level directory
        level_dir = os.path.join(self.tiles_dir, str(level))
        os.makedirs(level_dir, exist_ok=True)
        
        # Generate tiles with progress indicator
        processed_tiles = 0
        for row in range(rows):
            for col in range(cols):
                self._save_tile(level_img, level_dir, col, row, 
                                 level_width, level_height)
                processed_tiles += 1
                
                # Progress update every 50 tiles or on last tile
                if processed_tiles % 50 == 0 or processed_tiles == total_tiles_in_level:
                    percent = (processed_tiles / total_tiles_in_level) * 100
                    # Use carriage return for in-place update
                    print(f"  Progress: {processed_tiles}/{total_tiles_in_level} ({percent:.1f}%)", end='\r')
        
        # Print a final newline after the progress bar for this level if any tiles were processed
        if total_tiles_in_level > 0: 
            print() 
        return total_tiles_in_level
    
    def _save_tile(self, img, level_dir, col, row, level_width, level_height):
        """Extract and save a single tile, clamping coordinates to image bounds"""
        
        # Calculate crop coordinates for the tile, including overlap
        # x1, y1 are the top-left corner of the content area for the tile
        x1_content = col * self.tile_size
        y1_content = row * self.tile_size
        
        # Crop region starts 'overlap' pixels before the content area
        # and extends 'overlap' pixels beyond the content area.
        # So, the actual crop box includes overlap
        x1_crop = x1_content - self.overlap
        y1_crop = y1_content - self.overlap
        
        x2_crop = x1_content + self.tile_size + self.overlap
        y2_crop = y1_content + self.tile_size + self.overlap
        
        # Clamp crop coordinates to the actual image dimensions for this level
        # This handles tiles at the edges of the image where overlap might go outside
        x1_clamped = max(0, x1_crop)
        y1_clamped = max(0, y1_crop)
        x2_clamped = min(level_width, x2_crop)
        y2_clamped = min(level_height, y2_crop)
        
        # Crop the tile from the current level's image
        tile = img.crop((x1_clamped, y1_clamped, x2_clamped, y2_clamped))
        
        # Save tile
        tile_filename = f"{col}_{row}.{self.format}"
        tile_path = os.path.join(level_dir, tile_filename)
        
        if self.format == 'jpeg':
            # Ensure the image is in a format compatible with JPEG saving (RGB or L)
            if tile.mode not in ('RGB', 'L'):
                tile = tile.convert('RGB')
            tile.save(tile_path, 'JPEG', quality=self.quality, optimize=True)
        elif self.format == 'png':
            tile.save(tile_path, 'PNG', optimize=True)
        else:
            tile.save(tile_path)
    
    def _create_dzi_descriptor(self, width, height):
        """
        --- FIX 3: Include TileGroup Url in DZI descriptor XML ---
        Create the .dzi XML descriptor file, including the TileGroup Url
        """
        # The TileGroup Url should be the name of the directory containing the level folders
        tiles_dir_name = os.path.basename(self.tiles_dir)
        
        dzi_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008"
       Format="{self.format}"
       Overlap="{self.overlap}"
       TileSize="{self.tile_size}">
    <Size Height="{height}" Width="{width}"/>
    <Sources>
        <TileGroup Url="{tiles_dir_name}/" />
    </Sources>
</Image>'''
        
        with open(self.dzi_file, 'w') as f:
            f.write(dzi_content)
        
        print(f"✓ Created DZI descriptor: {self.dzi_file}")


def download_test_image():
    """Download a test astronomical image"""
    import urllib.request
    
    url = "https://cdn.spacetelescope.org/archives/images/large/heic0707a.jpg" # This image is 3253x3253
    filename = "test_carina.jpg"
    
    if os.path.exists(filename):
        print(f"Test image already exists: {filename}")
        return filename
    
    print(f"Downloading test image from Hubble (3253x3253)...")
    try:
        urllib.request.urlretrieve(url, filename)
        print(f"✓ Downloaded: {filename}")
        return filename
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return None


# Main execution
if __name__ == "__main__":
    print("\nWelcome to the DZI Generator!")
    print("This script works on Windows with no external dependencies.\n")
    
    # Option 1: Download test image
    print("[Option 1] Download and convert test Carina Nebula image")
    print("[Option 2] Convert your own image")
    choice = input("\nEnter 1 or 2: ").strip()
    
    if choice == "1":
        # Download test image
        test_file = download_test_image()
        if test_file:
            generator = DZIGenerator(
                image_path=test_file,
                output_name="test", # Changed output_name to "test" to match your original HTML setup "test.dzi"
                tile_size=256,
                overlap=1,
                format='jpeg',
                quality=90
            )
            generator.generate()
    else:
        # Use custom image
        image_path = input("Enter path to your image file: ").strip().strip('"')
        if os.path.exists(image_path):
            output_name = input("Enter output name (without extension): ").strip() or "output"
            
            generator = DZIGenerator(
                image_path=image_path,
                output_name=output_name,
                tile_size=512,  # Larger tiles for astro images, as suggested by original code
                overlap=2,
                format='jpeg',
                quality=92
            )
            generator.generate()
        else:
            print(f"Error: File not found: {image_path}")
    
    print("\n✓ Done! You can now use the .dzi file with OpenSeadragon.")