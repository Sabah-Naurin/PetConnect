import os
import django
import argparse
import torch
import torch.nn.functional as F

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petconnect.settings')
django.setup()

from vision.services import get_image_fingerprint

def compare_images(image1_path, image2_path):
    print(f"Extracting fingerprint for {os.path.basename(image1_path)}...")
    fp1 = get_image_fingerprint(image1_path)
    
    print(f"Extracting fingerprint for {os.path.basename(image2_path)}...")
    fp2 = get_image_fingerprint(image2_path)
    
    # Convert lists back to PyTorch tensors for cosine similarity calculation
    tensor1 = torch.tensor(fp1)
    tensor2 = torch.tensor(fp2)
    
    # Since our get_image_fingerprint already L2-normalizes the vectors, 
    # we can just use PyTorch's built-in cosine_similarity function
    similarity = F.cosine_similarity(tensor1.unsqueeze(0), tensor2.unsqueeze(0))
    
    return similarity.item()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Compare two images using DINOv2 cosine similarity.")
    parser.add_argument('--img1', type=str, default='media/pet_images/phi_2.jpg', help='Path to first image')
    parser.add_argument('--img2', type=str, default='media/pet_images/phi_1.jpg', help='Path to second image')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.img1):
        print(f"Error: Image 1 not found at {args.img1}")
    elif not os.path.exists(args.img2):
        print(f"Error: Image 2 not found at {args.img2}")
    else:
        score = compare_images(args.img1, args.img2)
        print(f"\n=========================================")
        print(f"Cosine Similarity Score: {score:.4f}")
        print(f"=========================================")
        if score > 0.60:
            print("Status: HIGH CONFIDENCE MATCH (Likely the same pet)")
        else:
            print("Status: LOW MATCH (Likely different pets)")
        print(f"=========================================")
