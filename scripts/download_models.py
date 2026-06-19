import os
from transformers import AutoProcessor, AutoModel, AutoFeatureExtractor, ASTModel

def download_models():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "assets", "models")
    os.makedirs(models_dir, exist_ok=True)
    
    print("Downloading SigLIP...")
    siglip_path = os.path.join(models_dir, "siglip-base-patch16-224")
    AutoProcessor.from_pretrained("google/siglip-base-patch16-224").save_pretrained(siglip_path)
    AutoModel.from_pretrained("google/siglip-base-patch16-224").save_pretrained(siglip_path)
    
    print("Downloading AST...")
    ast_path = os.path.join(models_dir, "ast-finetuned-audioset")
    AutoFeatureExtractor.from_pretrained("MIT/ast-finetuned-audioset-10-10-0.4593").save_pretrained(ast_path)
    ASTModel.from_pretrained("MIT/ast-finetuned-audioset-10-10-0.4593").save_pretrained(ast_path)
    
    print("Models downloaded successfully to assets/models/")

if __name__ == "__main__":
    download_models()
