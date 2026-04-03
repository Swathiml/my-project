import os
import json
import uuid
from datetime import datetime
from typing import Dict, List

from week4_document_pipeline.synthetic_generator import SyntheticDocumentGenerator
from week4_document_pipeline.document_loader import DocumentLoader
from week4_document_pipeline.quality_scorer import QualityScorer
from week4_document_pipeline.geometric_corrector import GeometricCorrector
from week4_document_pipeline.type_classifier import TypeClassifier
from week4_document_pipeline.ocr_engine import OCREngine


class Week4Pipeline:
    def __init__(self):
        self.loader = DocumentLoader()
        self.scorer = QualityScorer()
        self.corrector = GeometricCorrector()
        self.classifier = TypeClassifier()
        self.ocr = OCREngine()
        
        # Thresholds
        self.min_quality_score = 0.3
        self.min_classification_confidence = 0.3
    
    def process_document(self, image_path: str) -> Dict:
        """
        Full pipeline: Load → Quality → Correct → Classify → OCR → Output
        """
        document_id = str(uuid.uuid4())
        preprocessing_steps = []
        
        # Step 1: Load
        doc = self.loader.load(image_path)
        if doc['error']:
            return self._error_result(document_id, image_path, f"Load failed: {doc['error']}")
        
        if not self.loader.validate(doc):
            return self._error_result(document_id, image_path, "Validation failed")
        
        image = doc['image']
        
        # Step 2: Quality Check
        quality = self.scorer.compute_quality(image)
        
        if quality['overall'] < self.min_quality_score:
            return self._error_result(
                document_id, image_path, 
                f"Quality too low: {quality['overall']}",
                quality=quality
            )
        
        route = self.scorer.route_by_quality(quality)
        if route == 'reject_or_manual':
            return self._error_result(
                document_id, image_path,
                "Quality below threshold for auto-processing",
                quality=quality
            )
        
        preprocessing_steps.extend(self.scorer.get_recommendations(quality))
        
        # Step 3: Geometric Correction
        geo_result = self.corrector.correct_geometry(image)
        image = geo_result['image']
        preprocessing_steps.extend(geo_result['preprocessing_applied'])
        
        # Step 4: Initial OCR (for classification)
        initial_ocr = self.ocr.extract(image, doc_type='default')
        
        # Step 5: Document Classification
        classification = self.classifier.classify(image, initial_ocr['raw_text'])
        
        if classification['confidence'] < self.min_classification_confidence:
            doc_type = 'unknown'
        else:
            doc_type = classification['type']
        
        # Step 6: Optimized OCR with document-type config
        final_ocr = self.ocr.extract(image, doc_type=doc_type)
        
        # Step 7: Structure Analysis
        structure = self.ocr.extract_structure(final_ocr)
        
        # Build final output
        result = {
            "document_id": document_id,
            "source_path": image_path,
            "timestamp": datetime.now().isoformat(),
            
            "type": doc_type,
            "classification_confidence": classification['confidence'],
            "classification_status": classification['status'],
            
            "quality_score": quality['overall'],
            "quality_breakdown": {
                "sharpness": quality['sharpness'],
                "noise": quality['noise'],
                "contrast": quality['contrast'],
                "resolution": quality['resolution']
            },
            
            "preprocessing_applied": list(set(preprocessing_steps)),
            
            "geometric_correction": {
                "orientation_angle": geo_result['orientation_angle'],
                "orientation_method": geo_result['orientation_method'],
                "skew_angle": geo_result['skew_angle'],
                "original_size": geo_result['original_size'],
                "final_size": geo_result['final_size']
            },
            
            "ocr": {
                "raw_text": final_ocr['raw_text'][:1000],  # Truncate for JSON
                "word_count": final_ocr['word_count'],
                "confidence": final_ocr['confidence'],
                "config_used": final_ocr['config_used']
            },
            
            "extracted_structure": structure,
            
            "routing_decision": self.classifier.get_routing_decision(classification),
            
            "status": "success"
        }
        
        return result
    
    def _error_result(self, document_id: str, path: str, error_msg: str, quality=None) -> Dict:
        """Build error result."""
        return {
            "document_id": document_id,
            "source_path": path,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": error_msg,
            "quality_score": quality['overall'] if quality else None,
            "quality_breakdown": quality if quality else None
        }
    
    def process_batch(self, input_dir: str, output_file: str = "week4_output.json"):
        """
        Process all images in directory.
        """
        results = []
        
        # Find all images
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.pdf']:
            image_files.extend(
                [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(ext.replace('*', ''))]
            )
        
        print(f"Found {len(image_files)} documents to process")
        
        for i, img_path in enumerate(image_files, 1):
            print(f"\nProcessing {i}/{len(image_files)}: {os.path.basename(img_path)}")
            
            result = self.process_document(img_path)
            results.append(result)
            
            status = result.get('status', 'unknown')
            doc_type = result.get('type', 'unknown')
            print(f"  Status: {status}, Type: {doc_type}")
        
        # Save results
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*50}")
        print(f"Batch complete: {len(results)} documents")
        print(f"Output saved: {output_file}")
        
        # Summary
        successful = [r for r in results if r.get('status') == 'success']
        by_type = {}
        for r in successful:
            t = r.get('type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
        
        print(f"Successful: {len(successful)}/{len(results)}")
        print("By type:", by_type)
        
        return results


if __name__ == "__main__":
    # Generate test documents
    print("Generating test documents...")
    gen = SyntheticDocumentGenerator("test_pipeline")
    
    test_docs = [
        gen.generate_receipt(1, None),
        gen.generate_statement(2, {'blur': 1}),  # Slightly degraded
        gen.generate_invoice(3, None),
    ]
    
    # Run pipeline
    print("\n" + "="*50)
    print("Running Week 4 Pipeline")
    print("="*50)
    
    pipeline = Week4Pipeline()
    
    for doc_path in test_docs:
        print(f"\n{'-'*40}")
        result = pipeline.process_document(doc_path)
        
        print(f"Document: {result['document_id'][:8]}...")
        print(f"Type: {result['type']} (confidence: {result['classification_confidence']})")
        print(f"Quality: {result['quality_score']}")
        print(f"Preprocessing: {result['preprocessing_applied']}")
        print(f"OCR words: {result['ocr']['word_count']}, confidence: {result['ocr']['confidence']}")
        print(f"Routing: {result['routing_decision']}")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"\nExtracted text:")
            print(result['ocr']['raw_text'])
    
 