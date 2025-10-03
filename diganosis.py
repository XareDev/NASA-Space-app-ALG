import os
import xml.etree.ElementTree as ET
from PIL import Image

def diagnose_dzi(dzi_file):
    """Diagnose DZI file and check what was converted"""
    
    print("="*60)
    print("DZI DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check if DZI file exists
    if not os.path.exists(dzi_file):
        print(f"❌ DZI file not found: {dzi_file}")
        return
    
    print(f"\n✓ Found DZI file: {dzi_file}")
    
    # Parse DZI XML
    try:
        tree = ET.parse(dzi_file)
        root = tree.getroot()
        
        # Extract namespace
        ns = {'dzi': 'http://schemas.microsoft.com/deepzoom/2008'}
        
        # Get image dimensions from DZI
        size_elem = root.find('dzi:Size', ns)
        if size_elem is None:
            size_elem = root.find('Size')  # Try without namespace
        
        dzi_width = int(size_elem.get('Width'))
        dzi_height = int(size_elem.get('Height'))
        tile_size = int(root.get('TileSize'))
        overlap = int(root.get('Overlap'))
        format_type = root.get('Format')
        
        print(f"\n📊 DZI Information:")
        print(f"  Dimensions: {dzi_width} x {dzi_height}")
        print(f"  Tile Size: {tile_size}px")
        print(f"  Overlap: {overlap}px")
        print(f"  Format: {format_type}")
        
    except Exception as e:
        print(f"❌ Error parsing DZI: {e}")
        return
    
    # Check tiles folder
    tiles_folder = dzi_file.replace('.dzi', '_files')
    if not os.path.exists(tiles_folder):
        print(f"\n❌ Tiles folder not found: {tiles_folder}")
        return
    
    print(f"\n✓ Found tiles folder: {tiles_folder}")
    
    # Count levels and tiles
    levels = [d for d in os.listdir(tiles_folder) if os.path.isdir(os.path.join(tiles_folder, d))]
    levels.sort(key=int)
    
    print(f"\n📁 Pyramid Levels: {len(levels)}")
    
    total_tiles = 0
    for level in levels:
        level_path = os.path.join(tiles_folder, level)
        tiles = [f for f in os.listdir(level_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
        total_tiles += len(tiles)
        print(f"  Level {level}: {len(tiles)} tiles")
    
    print(f"\n  Total tiles: {total_tiles}")
    
    # Check a sample tile from highest level
    highest_level = levels[-1]
    highest_level_path = os.path.join(tiles_folder, highest_level)
    sample_tiles = os.listdir(highest_level_path)
    
    if sample_tiles:
        sample_tile = os.path.join(highest_level_path, sample_tiles[0])
        try:
            img = Image.open(sample_tile)
            print(f"\n🔍 Sample Tile (Level {highest_level}):")
            print(f"  Size: {img.size[0]} x {img.size[1]}")
            print(f"  Mode: {img.mode}")
        except Exception as e:
            print(f"\n❌ Error reading sample tile: {e}")
    
    print("\n" + "="*60)
    return dzi_width, dzi_height


def check_original_image(image_path):
    """Check the original image dimensions"""
    
    print("\n" + "="*60)
    print("ORIGINAL IMAGE CHECK")
    print("="*60)
    
    if not os.path.exists(image_path):
        print(f"❌ Original image not found: {image_path}")
        print("\nPlease provide the path to your original image:")
        return
    
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        print(f"\n📷 Original Image:")
        print(f"  Path: {image_path}")
        print(f"  Dimensions: {width} x {height}")
        print(f"  Mode: {img.mode}")
        print(f"  Format: {img.format}")
        
        # Calculate file size
        file_size = os.path.getsize(image_path)
        if file_size > 1024*1024*1024:
            size_str = f"{file_size/(1024**3):.2f} GB"
        elif file_size > 1024*1024:
            size_str = f"{file_size/(1024**2):.2f} MB"
        else:
            size_str = f"{file_size/1024:.2f} KB"
        
        print(f"  File Size: {size_str}")
        
        return width, height
        
    except Exception as e:
        print(f"❌ Error reading image: {e}")
        return None, None


def compare_dimensions(dzi_file, original_image):
    """Compare DZI and original image dimensions"""
    
    dzi_dims = diagnose_dzi(dzi_file)
    orig_dims = check_original_image(original_image)
    
    if dzi_dims and orig_dims:
        dzi_w, dzi_h = dzi_dims
        orig_w, orig_h = orig_dims
        
        print("\n" + "="*60)
        print("COMPARISON")
        print("="*60)
        
        if dzi_w == orig_w and dzi_h == orig_h:
            print("\n✅ DIMENSIONS MATCH!")
            print("   DZI contains the full image.")
        else:
            print("\n⚠️  DIMENSIONS MISMATCH!")
            print(f"   Original: {orig_w} x {orig_h}")
            print(f"   DZI:      {dzi_w} x {dzi_h}")
            print(f"\n   The DZI is showing only {(dzi_w*dzi_h)/(orig_w*orig_h)*100:.1f}% of the original image!")
            print("\n💡 SOLUTION: Re-run the DZI converter on the full image.")


# Main execution
if __name__ == "__main__":
    print("\nWelcome to the DZI Diagnostic Tool!\n")
    
    # Get file paths
    dzi_file = input("Enter path to your .dzi file (or press Enter for 'te.dzi'): ").strip().strip('"')
    if not dzi_file:
        dzi_file = "te.dzi"
    
    original_image = input("Enter path to your original image file: ").strip().strip('"')
    
    if original_image:
        compare_dimensions(dzi_file, original_image)
    else:
        diagnose_dzi(dzi_file)
    
    print("\n✓ Diagnostic complete!")