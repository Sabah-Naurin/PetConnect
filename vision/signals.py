from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import SightingReport, LostReport, Notification
from vision.models import Embedding
from vision.services import get_image_fingerprint
import torch
import torch.nn.functional as F

THRESHOLD = 0.55

def get_or_create_embedding(base_report):
    embedding_obj = Embedding.objects.filter(pet=base_report).first()
    if embedding_obj:
        return torch.tensor(embedding_obj.feature_vector)
    
    if not base_report.image:
        return None
        
    try:
        feature_list = get_image_fingerprint(base_report.image.path)
        Embedding.objects.create(pet=base_report, feature_vector=feature_list)
        return torch.tensor(feature_list)
    except Exception as e:
        print(f"Error calculating embedding for base_report {base_report.id}: {e}")
        return None

def find_best_match(source_tensor, candidates):
    best_score = -1.0
    best_candidate = None
    
    source_tensor = source_tensor.unsqueeze(0)
    for candidate in candidates:
        candidate_tensor = get_or_create_embedding(candidate.base_report)
        if candidate_tensor is not None:
            score = F.cosine_similarity(source_tensor, candidate_tensor.unsqueeze(0)).item()
            if score > best_score:
                best_score = score
                best_candidate = candidate
                
    return best_candidate, best_score

@receiver(post_save, sender=SightingReport)
def sighting_match_lost(sender, instance, created, **kwargs):
    if created:
        if getattr(instance, 'parent_report_id', None) is not None:
            print(f"[ML-Vision] Sighting {instance.id} is an update to an existing lost post. Skipping ML check.")
            return

        print(f"[ML-Vision] Running match check for new SightingReport {instance.id} against existing LostReports...")
        source_tensor = get_or_create_embedding(instance.base_report)
        if source_tensor is None:
            print(f"[ML-Vision] Could not generate embedding. Aborting.")
            return
            
        location = instance.base_report.location
        candidates = LostReport.objects.filter(base_report__location=location, base_report__is_resolved=False)
        print(f"[ML-Vision] Found {candidates.count()} candidate LostReports in '{location}'.")
        
        best_match, best_score = find_best_match(source_tensor, candidates)
        if best_match:
            print(f"[ML-Vision] Best match score: {best_score*100:.1f}%")
        else:
            print(f"[ML-Vision] No valid matches found.")
        
        if best_score > THRESHOLD and best_match:
            Notification.objects.create(
                recipient=best_match.base_report.author,
                notif_type='NEW_SIGHTING',
                message=f"Possible match found for {best_match.pet_name}! Similarity: {best_score*100:.1f}%. Please review.",
                link=f"/report/{instance.base_report.id}/?ml_match={best_match.base_report.id}&score={best_score*100:.0f}"
            )

@receiver(post_save, sender=LostReport)
def lost_match_sighting(sender, instance, created, **kwargs):
    if created:
        print(f"[ML-Vision] Running match check for new LostReport {instance.id} against independent SightingReports...")
        source_tensor = get_or_create_embedding(instance.base_report)
        if source_tensor is None:
            print(f"[ML-Vision] Could not generate embedding. Aborting.")
            return
            
        location = instance.base_report.location
        # Do not compare against sighting updates
        candidates = SightingReport.objects.filter(
            base_report__location=location, 
            base_report__is_resolved=False,
            parent_report__isnull=True
        ).exclude(claims__approval_status='Approved')
        print(f"[ML-Vision] Found {candidates.count()} candidate SightingReports in '{location}'.")
        
        best_match, best_score = find_best_match(source_tensor, candidates)
        if best_match:
            print(f"[ML-Vision] Best match score: {best_score*100:.1f}%")
        else:
            print(f"[ML-Vision] No valid matches found.")
        
        if best_score > THRESHOLD and best_match:
            Notification.objects.create(
                recipient=instance.base_report.author,
                notif_type='NEW_SIGHTING',
                message=f"We found an existing sighting that resembles your pet ({best_score*100:.1f}% match)!",
                link=f"/report/{best_match.base_report.id}/?ml_match={instance.base_report.id}&score={best_score*100:.0f}"
            )
