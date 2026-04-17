from django.apps import AppConfig


class VisionConfig(AppConfig):
    name = 'vision'

    processor = None
    model = None

    def ready(self):
        import os
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

        from transformers import AutoImageProcessor, Dinov2Model

        if VisionConfig.processor is None:
            VisionConfig.processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
        if VisionConfig.model is None:
            VisionConfig.model = Dinov2Model.from_pretrained('facebook/dinov2-base')
            VisionConfig.model.eval()

        # Connect signals
        import vision.signals
