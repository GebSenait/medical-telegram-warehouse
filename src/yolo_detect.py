"""
YOLO Object Detection for Medical Telegram Warehouse
Task-3: Data Enrichment with Object Detection

This module uses YOLOv8 to analyze images scraped in Task-1 and enrich
the analytical warehouse with image-derived features.

Business Questions:
- Which channels rely more on visuals?
- Do images with people drive more engagement?
- What are the limitations of generic CV models in medical commerce?
"""

import csv
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from ultralytics import YOLO
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATA_RAW_IMAGES = os.getenv('DATA_RAW_IMAGES', 'data/raw/images')
YOLO_MODEL = os.getenv('YOLO_MODEL', 'yolov8n.pt')  # nano for performance
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv('YOLO_CONFIDENCE_THRESHOLD', '0.25'))
OUTPUT_CSV = os.getenv('YOLO_OUTPUT_CSV', 'data/processed/yolo_detections.csv')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YOLODetector:
    """
    Production-grade YOLO object detector for medical Telegram images.

    Uses YOLOv8 nano model for performance on laptops while maintaining
    reasonable accuracy for common object detection tasks.
    """

    # COCO class names (YOLOv8 default)
    # Person = 0, Product-related classes: bottle=39, cup=41, etc.
    PERSON_CLASS = 0
    PRODUCT_CLASSES = {39, 41, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79}  # Common product classes

    def __init__(self, model_path: str = YOLO_MODEL):
        """
        Initialize YOLO detector.

        Args:
            model_path: Path to YOLO model file (default: yolov8n.pt)
        """
        logger.info(f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        self.model_path = model_path
        logger.info("YOLO model loaded successfully")

    def detect_objects(self, image_path: Path) -> List[Dict]:
        """
        Run object detection on a single image.

        Args:
            image_path: Path to image file

        Returns:
            List of detected objects with class, confidence, and bounding box
        """
        try:
            # Validate image exists
            if not image_path.exists():
                logger.warning(f"Image not found: {image_path}")
                return []

            # Run inference
            results = self.model(str(image_path), conf=YOLO_CONFIDENCE_THRESHOLD, verbose=False)

            detections = []
            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        class_name = self.model.names[class_id]

                        detections.append({
                            'class_id': class_id,
                            'class_name': class_name,
                            'confidence': confidence,
                            'bbox': box.xyxy[0].tolist() if hasattr(box.xyxy[0], 'tolist') else None
                        })

            return detections

        except Exception as e:
            logger.error(f"Error detecting objects in {image_path}: {str(e)}")
            return []

    def classify_image(self, detections: List[Dict]) -> Tuple[str, float]:
        """
        Classify image based on detected objects.

        Classification logic:
        - promotional: person + product
        - product_display: product only
        - lifestyle: person only
        - other: none detected

        Args:
            detections: List of detection dictionaries

        Returns:
            Tuple of (category, max_confidence)
        """
        if not detections:
            return ('other', 0.0)

        has_person = any(d['class_id'] == self.PERSON_CLASS for d in detections)
        has_product = any(d['class_id'] in self.PRODUCT_CLASSES for d in detections)

        max_confidence = max(d['confidence'] for d in detections) if detections else 0.0

        if has_person and has_product:
            return ('promotional', max_confidence)
        elif has_product:
            return ('product_display', max_confidence)
        elif has_person:
            return ('lifestyle', max_confidence)
        else:
            return ('other', max_confidence)

    def extract_message_info(self, image_path: Path) -> Optional[Dict]:
        """
        Extract message_id and channel_name from image path.

        Expected path format: data/raw/images/channel_name/message_id.jpg

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with channel_name and message_id, or None if parsing fails
        """
        try:
            # Normalize path
            path_str = str(image_path).replace('\\', '/')

            # Extract channel_name and message_id from path
            # Format: data/raw/images/channel_name/message_id.jpg
            parts = path_str.split('/')

            if 'images' in parts:
                idx = parts.index('images')
                if idx + 2 < len(parts):
                    channel_name = parts[idx + 1]
                    filename = parts[idx + 2]
                    # Remove extension
                    message_id = filename.rsplit('.', 1)[0]

                    return {
                        'channel_name': channel_name,
                        'message_id': message_id
                    }

            logger.warning(f"Could not parse message info from path: {image_path}")
            return None

        except Exception as e:
            logger.error(f"Error extracting message info from {image_path}: {str(e)}")
            return None


def scan_images_directory(images_dir: Path) -> List[Path]:
    """
    Scan directory for image files.

    Args:
        images_dir: Root directory containing images

    Returns:
        List of image file paths
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    image_files = []

    if not images_dir.exists():
        logger.warning(f"Images directory does not exist: {images_dir}")
        return image_files

    for root, dirs, files in os.walk(images_dir):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                image_files.append(Path(root) / file)

    logger.info(f"Found {len(image_files)} image files in {images_dir}")
    return image_files


def process_all_images(images_dir: str = DATA_RAW_IMAGES, output_csv: str = OUTPUT_CSV) -> str:
    """
    Process all images in the directory and generate detection results CSV.

    Args:
        images_dir: Directory containing images
        output_csv: Output CSV file path

    Returns:
        Path to output CSV file
    """
    images_path = Path(images_dir)
    output_path = Path(output_csv)

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    detector = YOLODetector()

    # Scan for images
    image_files = scan_images_directory(images_path)

    if not image_files:
        logger.warning("No images found. Creating empty CSV with headers.")
        # Create empty CSV with headers
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'message_id',
                'channel_name',
                'image_path',
                'detected_class',
                'confidence_score',
                'image_category',
                'num_detections'
            ])
        return str(output_path)

    # Process images
    results = []
    total = len(image_files)

    logger.info(f"Processing {total} images...")

    for idx, image_path in enumerate(image_files, 1):
        if idx % 10 == 0:
            logger.info(f"Processing image {idx}/{total}")

        # Extract message info
        message_info = detector.extract_message_info(image_path)
        if not message_info:
            continue

        # Run detection
        detections = detector.detect_objects(image_path)

        # Classify image
        category, max_confidence = detector.classify_image(detections)

        # Get primary detected class (highest confidence)
        primary_class = 'none'
        if detections:
            primary_detection = max(detections, key=lambda x: x['confidence'])
            primary_class = primary_detection['class_name']

        # Store result
        results.append({
            'message_id': message_info['message_id'],
            'channel_name': message_info['channel_name'],
            'image_path': str(image_path),
            'detected_class': primary_class,
            'confidence_score': max_confidence,
            'image_category': category,
            'num_detections': len(detections)
        })

    # Write to CSV
    logger.info(f"Writing {len(results)} detection results to {output_path}")
    df = pd.DataFrame(results)
    df.to_csv(output_path, index=False, encoding='utf-8')

    logger.info(f"YOLO detection complete. Results saved to {output_path}")
    return str(output_path)


def main():
    """Main entry point for YOLO detection script."""
    logger.info("=" * 60)
    logger.info("YOLO Object Detection - Task-3")
    logger.info("=" * 60)

    output_csv = process_all_images()

    logger.info("=" * 60)
    logger.info(f"Detection complete. Output: {output_csv}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
