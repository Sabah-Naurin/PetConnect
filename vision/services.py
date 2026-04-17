import torch
import torch.nn.functional as F
from PIL import Image
from django.apps import apps

def get_image_fingerprint(image_path):
    """
    Extracts a fine-grained image fingerprint using the preloaded DINOv2 model.
    """
    vision_config = apps.get_app_config('vision')
    processor = vision_config.processor
    model = vision_config.model

    if processor is None or model is None:
        raise RuntimeError("DINOv2 model or processor is not loaded.")

    try:
        image = Image.open(image_path).convert('RGB')
    except Exception as e:
        raise ValueError(f"Could not open image at {image_path}: {str(e)}")

    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)
        # Extract the [CLS] token
        cls_token = outputs.last_hidden_state[:, 0, :]
        
        # Apply L2 normalization
        normalized_embedding = F.normalize(cls_token, p=2, dim=1)
        
        # Squeeze and convert to Python list
        embedding_list = normalized_embedding.squeeze().tolist()
        
    return embedding_list
