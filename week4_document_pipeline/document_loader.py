import os
from PIL import Image
from pdf2image import convert_from_path
import mimetypes


class DocumentLoader:
    def __init__(self, max_size_mb=10, min_resolution=(200, 200)):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.min_resolution = min_resolution
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.pdf'}
        
    def load(self, path: str) -> dict:
        """
        Load document and return metadata dict.
        """
        result = {
            'image': None,
            'path': path,
            'format': None,
            'size_bytes': 0,
            'dimensions': (0, 0),
            'mode': None,
            'pages': 0,
            'error': None
        }
        
        if not os.path.exists(path):
            result['error'] = f"File not found: {path}"
            return result
        
        result['size_bytes'] = os.path.getsize(path)
        ext = os.path.splitext(path)[1].lower()
        result['format'] = ext
        
        if ext not in self.supported_formats:
            result['error'] = f"Unsupported format: {ext}"
            return result
        
        if result['size_bytes'] > self.max_size_bytes:
            result['error'] = f"File too large: {result['size_bytes']} bytes"
            return result
        
        try:
            if ext == '.pdf':
                images = convert_from_path(path, first_page=1, last_page=1)
                if not images:
                    result['error'] = "Could not convert PDF"
                    return result
                img = images[0]
                result['pages'] = len(convert_from_path(path, fmt='ppm'))
            else:
                img = Image.open(path)
                result['pages'] = 1
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            result['image'] = img
            result['dimensions'] = img.size
            result['mode'] = img.mode
            
        except Exception as e:
            result['error'] = f"Load error: {str(e)}"
        
        return result
    
    def validate(self, doc_dict: dict) -> bool:
        """Validate loaded document"""
        if doc_dict.get('error'):
            return False
        
        if doc_dict['image'] is None:
            return False
        
        width, height = doc_dict['dimensions']
        min_w, min_h = self.min_resolution
        
        if width < min_w or height < min_h:
            return False
        
        if doc_dict['mode'] not in ['RGB', 'L']:
            return False
        
        return True
    
    def get_metadata_summary(self, doc_dict: dict) -> str:
        """Human-readable summary"""
        if doc_dict.get('error'):
            return f"ERROR: {doc_dict['error']}"
        
        return (f"Document: {os.path.basename(doc_dict['path'])}\n"
                f"  Format: {doc_dict['format']}\n"
                f"  Size: {doc_dict['size_bytes']:,} bytes\n"
                f"  Dimensions: {doc_dict['dimensions'][0]}x{doc_dict['dimensions'][1]}\n"
                f"  Mode: {doc_dict['mode']}\n"
                f"  Pages: {doc_dict['pages']}\n"
                f"  Valid: {self.validate(doc_dict)}")


if __name__ == "__main__":
    from synthetic_generator import SyntheticDocumentGenerator
    
    print("Generating test images...")
    gen = SyntheticDocumentGenerator("test_load")
    r_path = gen.generate_receipt(1)
    s_path = gen.generate_statement(2)
    i_path = gen.generate_invoice(3)
    
    print("\nTesting DocumentLoader...")
    loader = DocumentLoader()
    
    for path in [r_path, s_path, i_path, "nonexistent.png"]:
        print(f"\nLoading: {path}")
        doc = loader.load(path)
        print(loader.get_metadata_summary(doc))
        
        if doc['image']:
            print(f"  Image type: {type(doc['image'])}")
