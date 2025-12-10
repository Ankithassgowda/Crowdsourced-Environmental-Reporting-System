import os
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import uuid
from werkzeug.utils import secure_filename

# Model definition (same as your original model)
class EnvironmentalClassifier(nn.Module):
    def __init__(self, num_classes=3, pretrained=True):
        super(EnvironmentalClassifier, self).__init__()
        self.backbone = models.efficientnet_b0(pretrained=pretrained)
        num_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        return self.backbone(x)

# Load the trained model
def load_model():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = EnvironmentalClassifier(num_classes=3, pretrained=False)
    
    try:
        checkpoint = torch.load('./training/best_environmental_model.pth', map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        return model, device
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, device

# Image preprocessing
def get_transform():
    return transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

# Predict image class
def predict_image(image_path, model, device):
    class_names = ['cutting_trees', 'garbage', 'polluted_water']
    transform = get_transform()
    
    try:
        image = Image.open(image_path).convert('RGB')
        image_tensor = transform(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            outputs = model(image_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
            _, predicted = torch.max(outputs, 1)
        
        predicted_class = class_names[predicted.item()]
        confidence = probabilities[predicted.item()].item()
        
        return {
            'predicted_class': predicted_class,
            'confidence': confidence,
            'all_probabilities': {
                class_names[i]: float(probabilities[i].item()) 
                for i in range(len(class_names))
            }
        }
    except Exception as e:
        print(f"Error predicting image: {e}")
        return None

# File upload utilities
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, upload_folder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + '_' + filename
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        return unique_filename
    return None