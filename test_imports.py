import numpy as np
import pandas as pd
import spacy
import fastapi
import uvicorn
import transformers
import torch
import sentence_transformers
import pytesseract
from PIL import Image
import rapidfuzz
import openai

print("✅ All imports successful!")
print(f"NumPy: {np.__version__}")
print(f"Pandas: {pd.__version__}")
print(f"SpaCy: {spacy.__version__}")
print(f"PyTorch: {torch.__version__}")